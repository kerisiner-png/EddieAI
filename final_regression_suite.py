from pathlib import Path
import shutil
import sys
import traceback


ROOT = Path("data") / "final_regression_suite"

if ROOT.exists():
    shutil.rmtree(
        ROOT,
        ignore_errors=True,
    )

ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

passed = 0
failed = 0


def run_test(name, fn):
    global passed, failed

    print()
    print("=" * 70)
    print(name)
    print("=" * 70)

    try:
        fn()
        print("PASS")
        passed += 1
    except Exception:
        print("FAIL")
        traceback.print_exc()
        failed += 1


# ============================================================
# 1. EVIDENCE ENGINE
# ============================================================

def test_evidence_independence():
    from memory.database import Memory
    from memory.evidence import EvidenceEngine

    db = ROOT / "evidence.db"
    memory = Memory(db)

    try:
        evidence = EvidenceEngine(memory)

        for i, source in enumerate(
            ["source-a", "source-b", "source-c"],
            start=1,
        ):
            evidence.add(
                category="belief",
                value="test-belief",
                source="SELF_INTERPRETATION",
                event_id=i,
                independence_key=source,
            )

        record = evidence.get(
            "belief",
            "test-belief",
        )

        assert record.count == 3
        assert record.weighted_score == 3.0
        assert record.confidence == 0.742
        assert (
            record.source_types
            == ["SELF_INTERPRETATION"]
        )

        rows = memory.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM evidence_events
            WHERE category = ?
              AND value = ?
            """,
            (
                "belief",
                "test-belief",
            ),
        ).fetchone()

        assert rows["count"] == 3

    finally:
        memory.close()


# ============================================================
# 2. LIFECYCLE
# ============================================================

def test_lifecycle():
    from memory.database import Memory

    from identity.self_state import SelfState
    from identity.personality_history import (
        PersonalityHistory,
    )
    from identity.personality_lifecycle import (
        PersonalityLifecycle,
    )

    db = ROOT / "lifecycle.db"
    memory = Memory(db)

    try:
        state = SelfState(
            ROOT / "lifecycle_state.json"
        )

        lifecycle = PersonalityLifecycle(
            state,
            PersonalityHistory(memory),
        )

        field = "preference"
        value = "test:lifecycle"

        trait = lifecycle.promote(
            field=field,
            value=value,
            strength=0.20,
            confidence=0.20,
            evidence_count=2,
        )

        print(
            "INITIAL LIFECYCLE TRAIT:",
            trait,
        )

        assert trait.strength == 0.20
        assert trait.confidence == 0.20
        assert (
            getattr(
                trait.status,
                "value",
                trait.status,
            )
            == "DORMANT"
        )

        trait = lifecycle.reinforce(
            field=field,
            value=value,
            amount=0.20,
        )

        assert (
            getattr(
                trait.status,
                "value",
                trait.status,
            )
            == "WEAKENING"
        )

        trait = lifecycle.reinforce(
            field=field,
            value=value,
            amount=0.20,
        )

        assert (
            getattr(
                trait.status,
                "value",
                trait.status,
            )
            == "EMERGING"
        )

        trait = lifecycle.reinforce(
            field=field,
            value=value,
            amount=0.20,
        )

        assert (
            getattr(
                trait.status,
                "value",
                trait.status,
            )
            == "ACTIVE"
        )

        trait = lifecycle.contradict(
            field=field,
            value=value,
            amount=0.90,
        )

        assert (
            getattr(
                trait.status,
                "value",
                trait.status,
            )
            == "DORMANT"
        )
        assert trait.contradictions == 1

    finally:
        memory.close()


# ============================================================
# 3. HABIT DETECTOR + IDEMPOTENCY
# ============================================================

def test_habit_pipeline():
    from memory.database import Memory
    from memory.events import Event
    from memory.evidence import EvidenceEngine

    from identity.habit_pattern_detector import (
        HabitPatternDetector,
    )

    db = ROOT / "habit.db"
    memory = Memory(db)

    try:
        evidence = EvidenceEngine(memory)

        detector = HabitPatternDetector(
            memory,
            evidence,
        )

        targets = [
            "\u043a\u043e\u0441\u043c\u043e\u0441",
            "\u0433\u0430\u043b\u0430\u043a\u0442\u0438\u043a\u0438",
            "\u0447\u0435\u0440\u043d\u044b\u0435 \u0434\u044b\u0440\u044b",
            "\u044d\u043a\u0437\u043e\u043f\u043b\u0430\u043d\u0435\u0442\u044b",
            "\u0437\u0432\u0435\u0437\u0434\u044b",
            "\u0433\u0440\u0430\u0432\u0438\u0442\u0430\u0446\u0438\u044f",
            "\u043d\u0435\u0439\u0442\u0440\u043e\u043d\u043d\u044b\u0435 \u0437\u0432\u0435\u0437\u0434\u044b",
            "\u043a\u043e\u0441\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043c\u0438\u0441\u0441\u0438\u0438",
            "\u043a\u043e\u0441\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0444\u043e\u043d",
            "\u0432\u0441\u0435\u043b\u0435\u043d\u043d\u0430\u044f",
        ]

        for target in targets:
            memory.remember(
                Event.create(
                    content=(
                        "\u042f "
                        "\u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u043e "
                        "\u0432\u044b\u043f\u043e\u043b\u043d\u0438\u043b "
                        "\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 "
                        f"'\u041f\u0440\u043e\u0432\u0435\u0441\u0442\u0438 "
                        f"\u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435: "
                        f"{target}' "
                        "\u0447\u0435\u0440\u0435\u0437 "
                        "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442 "
                        "research. "
                        "\u0421\u0442\u0430\u0442\u0443\u0441: OK."
                    ),
                    event_type="SELF_EXPERIENCE",
                    source_type="TOOL",
                    source="research",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

        first = detector.detect()

        assert first
        assert first[0]["observations"] == 10
        assert first[0]["distinct_targets"] == 10
        assert first[0]["created_evidence"] == 10

        record_1 = evidence.get(
            "habit",
            "repeated_action:research",
        )

        assert record_1.count == 10
        assert record_1.confidence == 0.775

        second = detector.detect()

        assert second
        assert second[0]["created_evidence"] == 0

        record_2 = evidence.get(
            "habit",
            "repeated_action:research",
        )

        assert record_2.count == 10
        assert record_2.weighted_score == 10.0

    finally:
        memory.close()


# ============================================================
# 4. BELIEF DETECTOR + IDEMPOTENCY
# ============================================================

def test_belief_pipeline():
    from memory.database import Memory
    from memory.evidence import EvidenceEngine
    from memory.knowledge import Knowledge

    from identity.belief_pattern_detector import (
        BeliefPatternDetector,
    )

    db = ROOT / "belief.db"
    memory = Memory(db)

    try:
        evidence = EvidenceEngine(memory)

        detector = BeliefPatternDetector(
            memory,
            evidence,
        )

        content = (
            "\u041c\u043e\u0439 "
            "\u0432\u044b\u0432\u043e\u0434 "
            "\u043f\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0443 "
            "'\u043d\u0430\u0443\u0447\u043d\u044b\u0439 \u043c\u0435\u0442\u043e\u0434': "
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c\u044b\u0435 "
            "\u043d\u0430\u0431\u043b\u044e\u0434\u0435\u043d\u0438\u044f "
            "\u043d\u0430\u0434\u0451\u0436\u043d\u0435\u0435 "
            "\u043d\u0435\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043d\u044b\u0445 "
            "\u0443\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0439."
        )

        sources = (
            "https://source-a.example,"
            "https://source-b.example,"
            "https://source-c.example"
        )

        for _ in range(3):
            memory.remember_knowledge(
                Knowledge(
                    content=content,
                    owner="SELF",
                    source_type="SELF_INTERPRETATION",
                    source=sources,
                    confidence=0.9,
                    verified=False,
                    personal_experience=False,
                )
            )

        first = detector.detect()

        assert first
        assert first[0]["observations"] == 3
        assert first[0]["distinct_sources"] == 3
        assert first[0]["created_evidence"] == 9

        value = first[0]["value"]

        record_1 = evidence.get(
            "belief",
            value,
        )

        assert record_1.count == 9
        assert record_1.confidence == 0.965

        second = detector.detect()

        assert second
        assert second[0]["created_evidence"] == 0

        record_2 = evidence.get(
            "belief",
            value,
        )

        assert record_2.count == 9
        assert record_2.confidence == record_1.confidence

    finally:
        memory.close()


# ============================================================
# 5. IDENTITY MANAGER + DEDUPLICATION
# ============================================================

def test_identity_manager():
    from memory.database import Memory

    from identity.identity_manager import (
        IdentityManager,
    )
    from identity.personality_lifecycle import (
        PersonalityLifecycle,
    )
    from identity.personality_history import (
        PersonalityHistory,
    )
    from identity.proposal import Proposal
    from identity.self_state import SelfState

    db = ROOT / "identity.db"
    memory = Memory(db)

    try:
        state = SelfState(
            ROOT / "identity_state.json"
        )

        lifecycle = PersonalityLifecycle(
            state,
            PersonalityHistory(memory),
        )

        manager = IdentityManager(
            state,
            memory,
            lifecycle,
        )

        proposal = Proposal(
            proposal_type="preference",
            value="test:identity",
            reason="regression",
            confidence=0.9,
            evidence=[],
            evidence_count=5,
        )

        first = manager.evaluate(
            proposal
        )

        assert first == "accepted"

        second = manager.evaluate(
            proposal
        )

        assert second == "already_present"

        preferences = state.get(
            "preferences",
            [],
        )

        assert preferences.count(
            "test:identity"
        ) == 1

    finally:
        memory.close()


# ============================================================
# 6. UNIFIED AGENT LOOP
# ============================================================

def test_unified_agent_loop():
    from core.agent_loop import AgentLoop

    from memory.database import Memory
    from memory.events import Event
    from memory.evidence import EvidenceEngine
    from memory.knowledge import Knowledge

    from identity.habit_pattern_detector import (
        HabitPatternDetector,
    )
    from identity.belief_pattern_detector import (
        BeliefPatternDetector,
    )
    from identity.self_state import SelfState
    from identity.identity_manager import (
        IdentityManager,
    )
    from identity.personality_lifecycle import (
        PersonalityLifecycle,
    )
    from identity.personality_history import (
        PersonalityHistory,
    )

    db = ROOT / "unified.db"
    memory = Memory(db)

    try:
        state = SelfState(
            ROOT / "unified_state.json"
        )

        evidence = EvidenceEngine(
            memory
        )

        lifecycle = PersonalityLifecycle(
            state,
            PersonalityHistory(memory),
        )

        identity_manager = IdentityManager(
            state,
            memory,
            lifecycle,
        )

        habit_detector = (
            HabitPatternDetector(
                memory,
                evidence,
            )
        )

        belief_detector = (
            BeliefPatternDetector(
                memory,
                evidence,
            )
        )

        targets = [
            "\u043a\u043e\u0441\u043c\u043e\u0441",
            "\u0433\u0430\u043b\u0430\u043a\u0442\u0438\u043a\u0438",
            "\u0447\u0435\u0440\u043d\u044b\u0435 \u0434\u044b\u0440\u044b",
            "\u0437\u0432\u0435\u0437\u0434\u044b",
            "\u044d\u043a\u0437\u043e\u043f\u043b\u0430\u043d\u0435\u0442\u044b",
            "\u0433\u0440\u0430\u0432\u0438\u0442\u0430\u0446\u0438\u044f",
            "\u0432\u0441\u0435\u043b\u0435\u043d\u043d\u0430\u044f",
            "\u043d\u0435\u0439\u0442\u0440\u043e\u043d\u043d\u044b\u0435 \u0437\u0432\u0435\u0437\u0434\u044b",
            "\u043a\u043e\u0441\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043c\u0438\u0441\u0441\u0438\u0438",
            "\u043a\u043e\u0441\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0444\u043e\u043d",
        ]

        for target in targets:
            memory.remember(
                Event.create(
                    content=(
                        "\u042f "
                        "\u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u043e "
                        "\u0432\u044b\u043f\u043e\u043b\u043d\u0438\u043b "
                        "\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 "
                        f"'\u041f\u0440\u043e\u0432\u0435\u0441\u0442\u0438 "
                        f"\u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435: "
                        f"{target}' "
                        "\u0447\u0435\u0440\u0435\u0437 "
                        "\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442 "
                        "research. "
                        "\u0421\u0442\u0430\u0442\u0443\u0441: OK."
                    ),
                    event_type="SELF_EXPERIENCE",
                    source_type="TOOL",
                    source="research",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

        belief_content = (
            "\u041c\u043e\u0439 "
            "\u0432\u044b\u0432\u043e\u0434 "
            "\u043f\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0443 "
            "'\u043d\u0430\u0443\u0447\u043d\u044b\u0439 "
            "\u043c\u0435\u0442\u043e\u0434': "
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c\u044b\u0435 "
            "\u043d\u0430\u0431\u043b\u044e\u0434\u0435\u043d\u0438\u044f "
            "\u043d\u0430\u0434\u0451\u0436\u043d\u0435\u0435 "
            "\u043d\u0435\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043d\u044b\u0445 "
            "\u0443\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0439."
        )

        sources = (
            "https://source-a.example,"
            "https://source-b.example,"
            "https://source-c.example"
        )

        for _ in range(3):
            memory.remember_knowledge(
                Knowledge(
                    content=belief_content,
                    owner="SELF",
                    source_type="SELF_INTERPRETATION",
                    source=sources,
                    confidence=0.9,
                    verified=False,
                    personal_experience=False,
                )
            )

        loop = AgentLoop.__new__(
            AgentLoop
        )

        loop.action_preference_detector = None
        loop.habit_pattern_detector = (
            habit_detector
        )
        loop.belief_pattern_detector = (
            belief_detector
        )
        loop.evidence = evidence
        loop.identity_manager = (
            identity_manager
        )

        first = (
            loop._process_identity_detectors()
        )

        assert any(
            item["category"] == "habit"
            and item["result"] == "accepted"
            for item in first
        )

        assert any(
            item["category"] == "belief"
            and item["result"] == "accepted"
            for item in first
        )

        second = (
            loop._process_identity_detectors()
        )

        assert any(
            item["category"] == "habit"
            and item["result"] == "already_present"
            for item in second
        )

        assert any(
            item["category"] == "belief"
            and item["result"] == "already_present"
            for item in second
        )

        assert (
            state.get(
                "habits",
                [],
            ).count(
                "repeated_action:research"
            )
            == 1
        )

        belief_value = (
            belief_detector.detect()[0]["value"]
        )

        assert (
            state.get(
                "beliefs",
                [],
            ).count(
                belief_value
            )
            == 1
        )

    finally:
        memory.close()


# ============================================================
# 7. PRODUCTION RUNTIME REGRESSION
# ============================================================

def test_production_runtime():
    import os
    import subprocess

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "test_production_runtime.py",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    print(
        result.stdout[-5000:]
    )

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(
            "test_production_runtime.py failed"
        )

    # The production runtime test itself is authoritative:
    # successful process termination means the runtime
    # completed without an uncaught exception.
    assert result.returncode == 0


# ============================================================
# RUN
# ============================================================

run_test(
    "1. Evidence independence",
    test_evidence_independence,
)

run_test(
    "2. Personality lifecycle",
    test_lifecycle,
)

run_test(
    "3. Habit pipeline + idempotency",
    test_habit_pipeline,
)

run_test(
    "4. Belief pipeline + idempotency",
    test_belief_pipeline,
)

run_test(
    "5. IdentityManager deduplication",
    test_identity_manager,
)

run_test(
    "6. Unified AgentLoop",
    test_unified_agent_loop,
)

run_test(
    "7. Production runtime",
    test_production_runtime,
)


print()
print("=" * 70)
print(
    f"RESULT: {passed} passed, {failed} failed"
)
print("=" * 70)

if failed:
    sys.exit(1)

print("FINAL REGRESSION: PASS")
