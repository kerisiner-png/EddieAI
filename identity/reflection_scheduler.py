import json
import time


class ReflectionScheduler:
    """
    Планировщик фоновой рефлексии личности.

    Главный поток:
        - собирает snapshot;
        - ставит snapshot в CognitiveQueue.

    Worker:
        - получает только JSON snapshot;
        - выполняет ReflectionCycle без SQLite.

    Main thread:
        - применяет готовый результат.
    """

    def __init__(
        self,
        agent,
        event_threshold: int = 8,
    ):
        self.agent = agent
        self.event_threshold = event_threshold
        self.events_since_reflection = 0

    def event_happened(
        self,
        significant: bool = True,
    ):
        if not significant:
            return False

        self.events_since_reflection += 1

        if (
            self.events_since_reflection
            < self.event_threshold
        ):
            return False

        return self.enqueue_reflection()

    def enqueue_reflection(self):
        candidates = (
            self.agent.personality.candidates(
                self_state=self.agent.self_state
            )
        )

        snapshot = {
            "created_at": time.time(),
            "self_state": (
                self.agent.self_state.snapshot()
            ),
            "candidates": [
                {
                    "field": candidate.field,
                    "value": candidate.value,
                    "category": candidate.category,
                    "strength": candidate.strength,
                    "weighted_score": (
                        candidate.weighted_score
                    ),
                    "evidence_count": (
                        candidate.evidence_count
                    ),
                    "source_types": (
                        candidate.source_types
                    ),
                    "reason": candidate.reason,
                }
                for candidate in candidates
            ],
        }

        item = (
            self.agent.cognitive_queue.enqueue(
                content=json.dumps(
                    snapshot,
                    ensure_ascii=False,
                ),
                route="REFLECTION",
                reason=(
                    "Достигнут порог значимых событий. "
                    "Сформирован snapshot для фоновой "
                    "рефлексии личности."
                ),
            )
        )

        self.events_since_reflection = 0

        self.agent.cognition_worker.start()
        self.agent.cognition_worker.wake()

        return {
            "queued": True,
            "item_id": item.id,
            "status": item.status,
            "candidate_count": len(
                candidates
            ),
        }

    def _reinforce_confirmed_traits(self):
        results = []

        traits = (
            self.agent
            .personality_lifecycle
            .all_traits()
        )

        for trait in traits:
            if trait.status == "REJECTED":
                continue

            try:
                evidence = (
                    self.agent.evidence.get(
                        trait.field,
                        trait.value,
                    )
                )
            except ValueError:
                continue

            if evidence.confidence <= 0:
                continue

            updated = (
                self.agent
                .personality_lifecycle
                .reinforce(
                    field=trait.field,
                    value=trait.value,
                    amount=0.02,
                )
            )

            if updated is not None:
                results.append(updated)

        return results

    def apply_completed_reflection(
        self,
        cycle_result: dict,
    ):
        application_result = (
            self.agent.apply_reflection_cycle(
                cycle_result
            )
        )

        reinforced = (
            self._reinforce_confirmed_traits()
        )

        self.agent.personality_lifecycle.decay(
            amount=0.02
        )

        return {
            "applied": application_result,
            "reinforced": reinforced,
        }

    def session_end(self):
        if self.events_since_reflection <= 0:
            return None

        return self.enqueue_reflection()

    def sleep_cycle(self):
        return self.enqueue_reflection()
