from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from core.agent import Agent
from identity.proposal import Proposal


ROOT = Path(__file__).resolve().parent
QUEUE_PATH = ROOT / "data" / "cognitive_queue.json"
QUEUE_BACKUP = ROOT / "data" / "cognitive_queue.regression_backup.json"
RESULT_PATH = ROOT / "data" / "core_regression_test.json"

TEST_PREFIX = "REGRESSION_TEST_"


class RegressionTest:

    def __init__(self):
        self.agent = None
        self.results = []
        self.started = time.perf_counter()

    def check(
        self,
        name,
        passed,
        details="",
        seconds=0.0,
    ):
        status = "PASS" if passed else "FAIL"

        self.results.append({
            "name": name,
            "status": status,
            "seconds": round(
                seconds,
                4,
            ),
            "details": details,
        })

        print(
            f"[{status}] "
            f"{name:<45} "
            f"{seconds:.4f}s"
        )

        if details:
            print(
                f"       {details}"
            )

    def run(self):
        print("=" * 72)
        print("EDDIEAI CORE REGRESSION TEST")
        print("=" * 72)
        print()

        try:
            self.prepare()
            self.agent = Agent()

            self.test_direct_knowledge()
            self.test_unknown_not_direct()
            self.test_self_change_intents()
            self.test_semantic_clustering()
            self.test_evidence_threshold()
            self.test_personality_candidate()
            self.test_promotion_decision()
            self.test_reflection_snapshot()
            self.test_reflection_worker()
            self.test_reflection_apply()
            self.test_dialogue_context()

        except Exception as exc:
            self.check(
                "runner_unhandled_exception",
                False,
                repr(exc),
            )

        finally:
            self.cleanup()

        self.save()
        self.report()

    # =========================================================
    # SETUP
    # =========================================================

    def prepare(self):
        QUEUE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if QUEUE_PATH.exists():
            shutil.copy2(
                QUEUE_PATH,
                QUEUE_BACKUP,
            )

    # =========================================================
    # CLEANUP
    # =========================================================

    def cleanup(self):
        if self.agent is None:
            return

        try:
            self.agent.cognition_worker.stop()
        except Exception:
            pass

        try:
            self.agent.memory.connection.execute(
                """
                DELETE FROM evidence_events
                WHERE independence_key LIKE ?
                """,
                (
                    TEST_PREFIX + "%",
                ),
            )

            self.agent.memory.connection.commit()

        except Exception:
            pass

        try:
            self.agent.close()
        except Exception:
            pass

        if QUEUE_BACKUP.exists():
            try:
                shutil.copy2(
                    QUEUE_BACKUP,
                    QUEUE_PATH,
                )

                QUEUE_BACKUP.unlink()

            except Exception:
                pass

    # =========================================================
    # 1. DIRECT KNOWLEDGE
    # =========================================================

    def test_direct_knowledge(self):
        prompt = (
            "Какая у тебя основная миссия?"
        )

        calls = []
        original = (
            self.agent.model_orchestrator.execute
        )

        def wrapped(
            *args,
            **kwargs,
        ):
            calls.append(1)

            return original(
                *args,
                **kwargs,
            )

        self.agent.model_orchestrator.execute = wrapped

        started = time.perf_counter()

        try:
            answer = self.agent.respond(
                prompt
            )
        finally:
            self.agent.model_orchestrator.execute = (
                original
            )

        elapsed = (
            time.perf_counter()
            - started
        )

        passed = (
            bool(answer.strip())
            and len(calls) == 0
            and elapsed < 0.5
        )

        self.check(
            "direct_knowledge_no_llm",
            passed,
            (
                f"llm_calls={len(calls)}, "
                f"answer={answer}"
            ),
            elapsed,
        )

    # =========================================================
    # 2. UNKNOWN NOT DIRECT
    # =========================================================

    def test_unknown_not_direct(self):
        result = (
            self.agent.knowledge_resolver.resolve(
                "Почему тебе нравится астрофизика?"
            )
        )

        self.check(
            "unknown_requires_reasoning",
            not result.found,
            str(result),
        )

    # =========================================================
    # 3. SELF CHANGE INTENTS
    # =========================================================

    def test_self_change_intents(self):
        prompts = [
            "Можешь ли ты изменить своё отношение "
            "к собственным чувствам?",

            "Может ли новое знание заставить тебя "
            "пересмотреть собственную позицию?",

            "Что могло бы убедить тебя изменить "
            "собственное убеждение?",
        ]

        all_correct = True
        details = []

        for prompt in prompts:
            result = (
                self.agent.cognitive_reasoner.reason(
                    user_message=prompt,
                    route="SELF_QUERY",
                )
            )

            ok = (
                result.response_intent
                == "SELF_CHANGE"
            )

            all_correct = (
                all_correct
                and ok
            )

            details.append(
                f"{result.response_intent}"
            )

        self.check(
            "self_change_intent_detection",
            all_correct,
            "intents=" + str(details),
        )

    # =========================================================
    # 4. SEMANTIC CLUSTERING
    # =========================================================

    def test_semantic_clustering(self):
        prompts = [
            "Можешь ли ты изменить своё отношение "
            "к собственным чувствам?",

            "Может ли новое знание заставить тебя "
            "пересмотреть собственную позицию?",

            "Что могло бы убедить тебя изменить "
            "собственное убеждение?",
        ]

        values = []

        for prompt in prompts:
            result = (
                self.agent.cognitive_reasoner.reason(
                    user_message=prompt,
                    route="SELF_QUERY",
                )
            )

            observations = (
                self.agent.self_observation_bridge.observe(
                    result=result,
                    user_message=prompt,
                )
            )

            values.extend(
                observation.value
                for observation in observations
            )

        passed = (
            len(values) == 3
            and len(set(values)) == 1
            and values[0]
            == "self_model_is_revisable"
        )

        self.check(
            "semantic_self_observation_clustering",
            passed,
            str(values),
        )

    # =========================================================
    # 5. EVIDENCE
    # =========================================================

    def test_evidence_threshold(self):
        value = (
            TEST_PREFIX
            + "belief_evidence"
        )

        for index in range(3):
            self.agent.evidence.add(
                category="belief",
                value=value,
                source="SELF_INTERPRETATION",
                independence_key=(
                    f"{TEST_PREFIX}independent_{index}"
                ),
            )

        record = self.agent.evidence.get(
            "belief",
            value,
        )

        passed = (
            record.count == 3
            and record.weighted_score >= 3.0
            and record.confidence >= 0.70
        )

        self.check(
            "evidence_accumulates",
            passed,
            str(record),
        )

    # =========================================================
    # 6. PERSONALITY CANDIDATE
    # =========================================================

    def test_personality_candidate(self):
        value = (
            TEST_PREFIX
            + "belief_candidate"
        )

        for index in range(4):
            self.agent.evidence.add(
                category="belief",
                value=value,
                source="SELF_INTERPRETATION",
                independence_key=(
                    f"{TEST_PREFIX}candidate_{index}"
                ),
            )

        candidates = [
            candidate
            for candidate
            in self.agent.personality.candidates(
                self_state=self.agent.self_state
            )
            if candidate.value == value
        ]

        self.check(
            "evidence_becomes_personality_candidate",
            bool(candidates),
            str(candidates),
        )

    # =========================================================
    # 7. PROMOTION
    # =========================================================

    def test_promotion_decision(self):
        value = (
            TEST_PREFIX
            + "belief_promotion"
        )

        for index in range(4):
            source = [
                "SELF_INTERPRETATION",
                "SELF_OBSERVATION",
                "SELF_EXPERIENCE",
                "ACTION_CHOICE",
            ][index]

            self.agent.evidence.add(
                category="belief",
                value=value,
                source=source,
                independence_key=(
                    f"{TEST_PREFIX}promotion_{index}"
                ),
            )

        candidates = [
            candidate
            for candidate
            in self.agent.personality.candidates(
                self_state=self.agent.self_state
            )
            if candidate.value == value
        ]

        if not candidates:
            self.check(
                "promotion_engine_accepts_strong_candidate",
                False,
                "Candidate was not produced.",
            )
            return

        decision = (
            self.agent.promotion.evaluate(
                candidates[0]
            )
        )

        self.check(
            "promotion_engine_accepts_strong_candidate",
            decision.action == "PROMOTE",
            str(decision),
        )

    # =========================================================
    # 8. REFLECTION SNAPSHOT
    # =========================================================

    def test_reflection_snapshot(self):
        candidates = (
            self.agent.personality.candidates(
                self_state=self.agent.self_state
            )
        )

        snapshot = {
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

        serialized = json.dumps(
            snapshot,
            ensure_ascii=False,
        )

        self.check(
            "reflection_snapshot_serializable",
            isinstance(
                json.loads(serialized),
                dict,
            ),
            f"candidate_count={len(candidates)}",
        )

    # =========================================================
    # 9. BACKGROUND REFLECTION
    # =========================================================

    def test_reflection_worker(self):
        # Чистим очередь только внутри теста.
        self.agent.cognitive_queue.items = []
        self.agent.cognitive_queue._save()

        snapshot = {
            "self_state": (
                self.agent.self_state.snapshot()
            ),
            "candidates": [],
        }

        item = (
            self.agent.cognitive_queue.enqueue(
                content=json.dumps(
                    snapshot,
                    ensure_ascii=False,
                ),
                route="REFLECTION",
                reason=(
                    TEST_PREFIX
                    + "reflection_worker"
                ),
            )
        )

        started = time.perf_counter()

        self.agent.cognition_worker.start()
        self.agent.cognition_worker.wake()

        current = None

        for _ in range(40):
            time.sleep(0.25)

            current = (
                self.agent.cognitive_queue.get(
                    item.id
                )
            )

            if (
                current is not None
                and current.status
                in {
                    "ANALYZED",
                    "FAILED",
                }
            ):
                break

        elapsed = (
            time.perf_counter()
            - started
        )

        passed = (
            current is not None
            and current.status == "ANALYZED"
            and self.agent.cognition_worker.last_error
            is None
        )

        self.agent.cognition_worker.stop()

        self.check(
            "background_reflection_worker",
            passed,
            (
                f"status={getattr(current, 'status', None)}, "
                f"worker_error="
                f"{self.agent.cognition_worker.last_error}"
            ),
            elapsed,
        )

    # =========================================================
    # 10. MAIN THREAD APPLY
    # =========================================================

    def test_reflection_apply(self):
        self.agent.cognitive_queue.items = []
        self.agent.cognitive_queue._save()

        snapshot = {
            "self_state": (
                self.agent.self_state.snapshot()
            ),
            "candidates": [],
        }

        item = (
            self.agent.cognitive_queue.enqueue(
                content=json.dumps(
                    snapshot,
                    ensure_ascii=False,
                ),
                route="REFLECTION",
                reason=(
                    TEST_PREFIX
                    + "reflection_apply"
                ),
            )
        )

        self.agent.cognition_worker.start()
        self.agent.cognition_worker.wake()

        current = None

        for _ in range(40):
            time.sleep(0.25)

            current = (
                self.agent.cognitive_queue.get(
                    item.id
                )
            )

            if (
                current is not None
                and current.status
                in {
                    "ANALYZED",
                    "DONE",
                }
            ):
                break

        if (
            current is not None
            and current.status == "ANALYZED"
        ):
            apply_result = (
                self.agent.cognitive_processor
                .apply_analyzed(
                    item.id
                )
            )

            current = (
                self.agent.cognitive_queue.get(
                    item.id
                )

            )

            passed = (
                apply_result.get("status")
                == "REFLECTION_APPLIED"
                and current is not None
                and current.status == "DONE"
            )

            details = (
                f"apply={apply_result.get('status')}, "
                f"final={getattr(current, 'status', None)}"
            )

        else:
            # Worker уже мог завершить main-thread apply
            # в другой части системы. DONE здесь также
            # является допустимым end-state.
            passed = (
                current is not None
                and current.status == "DONE"
            )

            details = (
                f"already_applied="
                f"{getattr(current, 'status', None)}"
            )

        self.agent.cognition_worker.stop()

        self.check(
            "reflection_main_thread_application",
            passed,
            details,
        )

    # =========================================================
    # 11. DIALOGUE
    # =========================================================

    def test_dialogue_context(self):
        first = self.agent.respond(
            "Что тебе сейчас нравится?"
        )

        second = self.agent.respond(
            "Почему?"
        )

        context = (
            self.agent.dialogue_state
            .followup_context(
                "Почему?"
            )
        )

        linked = (
            "Что тебе сейчас нравится?"
            in context
        )

        nonempty = bool(
            second.strip()
        )

        self.check(
            "dialogue_followup_context",
            linked and nonempty,
            (
                f"context={context[:300]!r}, "
                f"answer={second[:300]!r}"
            ),
        )

    # =========================================================
    # SAVE
    # =========================================================

    def save(self):
        payload = {
            "test": "EDDIEAI CORE REGRESSION TEST",
            "duration": round(
                time.perf_counter()
                - self.started,
                3,
            ),
            "summary": {
                "total": len(
                    self.results
                ),
                "passed": sum(
                    item["status"] == "PASS"
                    for item in self.results
                ),
                "failed": sum(
                    item["status"] == "FAIL"
                    for item in self.results
                ),
            },
            "results": self.results,
        }

        RESULT_PATH.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def report(self):
        passed = sum(
            item["status"] == "PASS"
            for item in self.results
        )

        failed = sum(
            item["status"] == "FAIL"
            for item in self.results
        )

        total = len(
            self.results
        )

        print()
        print("=" * 72)
        print("CORE REGRESSION RESULT")
        print("=" * 72)
        print(
            f"PASS: {passed}"
        )
        print(
            f"FAIL: {failed}"
        )
        print(
            f"TOTAL: {total}"
        )

        if total:
            print(
                f"SCORE: {passed / total * 100:.1f}%"
            )

        print()
        print(
            f"JSON: {RESULT_PATH}"
        )


if __name__ == "__main__":
    RegressionTest().run()
