import re
from collections import defaultdict


class HabitPatternDetector:
    """
    Detects repeated self-action patterns.

    Habit is inferred from:
    - repeated successful self-experience;
    - same action/tool;
    - multiple distinct targets;
    - no requirement for alternative choices.

    Does not modify self_state directly.
    Produces habit evidence only.
    """

    MIN_OBSERVATIONS = 4
    MIN_DISTINCT_TARGETS = 3
    MIN_CONFIDENCE = 0.80

    def __init__(
        self,
        memory,
        evidence,
    ):
        self.memory = memory
        self.evidence = evidence

    def detect(self):
        groups = self._load_experiences()

        results = []

        for action_type, observations in groups.items():
            result = self._analyze(
                action_type,
                observations,
            )

            if result is None:
                continue

            results.append(result)

        return results

    def _load_experiences(self):
        rows = self.memory.connection.execute(
            """
            SELECT
                id,
                content,
                source,
                confidence,
                verified
            FROM events
            WHERE event_type = 'SELF_EXPERIENCE'
              AND personal_experience = 1
            ORDER BY id ASC
            """
        ).fetchall()

        groups = defaultdict(list)

        for row in rows:
            source = str(
                row["source"] or ""
            ).strip().lower()

            if not source:
                continue

            confidence = float(
                row["confidence"] or 0.0
            )

            verified = bool(
                row["verified"]
            )

            if confidence < self.MIN_CONFIDENCE:
                continue

            if not verified:
                continue

            target = self._extract_target(
                row["content"]
            )

            if not target:
                continue

            groups[source].append({
                "event_id": row["id"],
                "source": source,
                "target": target,
                "confidence": confidence,
            })

        return groups

    def _analyze(
        self,
        action_type,
        observations,
    ):
        if len(observations) < (
            self.MIN_OBSERVATIONS
        ):
            return None

        distinct_targets = {
            self._normalize_target(
                observation["target"]
            )
            for observation in observations
        }

        distinct_targets.discard("")

        if len(distinct_targets) < (
            self.MIN_DISTINCT_TARGETS
        ):
            return None

        average_confidence = (
            sum(
                observation["confidence"]
                for observation in observations
            )
            / len(observations)
        )

        if (
            average_confidence
            < self.MIN_CONFIDENCE
        ):
            return None

        target = (
            f"repeated_action:{action_type}"
        )

        existing = None

        try:
            existing = self.evidence.get(
                "habit",
                target,
            )
        except ValueError:
            pass

        existing_count = (
            existing.count
            if existing is not None
            else 0
        )

        # One evidence per newly observed
        # self-experience event.
        created = 0

        for observation in observations:
            if (
                created + existing_count
                >= len(observations)
            ):
                break

            # The evidence engine currently does not
            # carry event_id, so the aggregate count
            # is used to keep detector idempotent.
            self.evidence.add(
                category="habit",
                value=target,
                source="SELF_EXPERIENCE",
            )

            created += 1

        return {
            "status": (
                "PROMOTABLE"
                if created > 0
                else "OBSERVED"
            ),
            "category": "habit",
            "value": target,
            "action_type": action_type,
            "observations": len(
                observations
            ),
            "distinct_targets": len(
                distinct_targets
            ),
            "average_confidence": round(
                average_confidence,
                3,
            ),
            "created_evidence": created,
        }

    def _extract_target(
        self,
        content,
    ):
        if not content:
            return None

        text = str(content)

        marker = (
            "Я самостоятельно выполнил "
            "действие '"
        )

        start = text.find(marker)

        if start < 0:
            return None

        start += len(marker)

        end = text.find(
            "' через инструмент",
            start,
        )

        if end < 0:
            end = text.find(
                "'. Статус:",
                start,
            )

        if end < 0:
            return None

        target = text[
            start:end
        ].strip()

        return target or None

    def _normalize_target(
        self,
        target,
    ):
        return " ".join(
            re.findall(
                r"[\u0430-\u044f\u0451a-z0-9]+",
                str(target).lower(),
            )
        )
