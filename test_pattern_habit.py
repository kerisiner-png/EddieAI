from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import DecisionCore
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory
from memory.evidence import EvidenceEngine


KEY = "g=изучить тему: космос|t=research|i=n|a=positive|p=day|f=0"


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    evidence = EvidenceEngine(db)
    goal_manager = GoalManager(state, GoalPlanner(state))

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
        evidence=evidence,
    )

    # Паттерн без достаточного переиспользования
    # НЕ становится привычкой
    db.pattern_record(
        KEY,
        '{"kind": "EXECUTE", "payload": null}',
        confidence=0.8,
    )

    created = core.consolidate_habits(min_uses=3)

    assert created == 0, (
        "мало переиспользований не должно "
        "создавать привычку"
    )

    # Накопление использования до порога
    for _ in range(3):
        db.pattern_bump(KEY)

    created = core.consolidate_habits(min_uses=3)

    assert created == 1, created

    record = evidence.get(
        "habit",
        f"situation_action:{KEY}",
    )

    assert record.count == 1
    assert "DECISION_PATTERN" in record.source_types

    # Идемпотентность: повторная консолидация не дублирует
    created = core.consolidate_habits(min_uses=3)

    assert created == 0, created

    record = evidence.get(
        "habit",
        f"situation_action:{KEY}",
    )

    assert record.count == 1, (
        "повторная консолидация не должна "
        "плодить свидетельства"
    )

    print("SOURCE_TYPES:", record.source_types)
    print("CONFIDENCE:", record.confidence)
    print("ALL PASS")

    db.close()
