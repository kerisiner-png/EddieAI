from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import DecisionCore
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


class FakeOrchestrator:
    def _cloud_chat(self, system, user, options, task):
        raise AssertionError("LLM не должен вызываться")


BASE_STATE = {
    "goal": None,
    "task_type": None,
    "inbox_unread": 0,
    "affect": 0.0,
    "emotions": {},
    "freshness": 0,
}


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))
    goal_manager.add_candidate(
        value="изучить тему: космос",
        motivation=0.7,
        priority=0.7,
        confidence=0.7,
    )

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
        model_orchestrator=FakeOrchestrator(),
    )

    # Высокая фрустрация + есть кандидат
    # -> ядро НЕ начинает новое (IDLE)
    decision = core.decide(
        dict(BASE_STATE, emotions={"frustration": 0.9})
    )

    assert decision.kind == "IDLE", decision

    # Без фрустрации кандидат активируется
    decision = core.decide(
        dict(BASE_STATE, emotions={"frustration": 0.0})
    )

    assert decision.kind == "ACTIVATE_GOAL", decision

    # Активная цель + фрустрация -> текущая работа
    # НЕ прерывается (EXECUTE)
    goal_manager.activate("изучить тему: космос")
    goal_manager.ensure_plan(
        "изучить тему: космос",
        ["Провести исследование: космос"],
    )

    decision = core.decide(
        dict(
            BASE_STATE,
            emotions={"frustration": 0.9},
        )
    )

    assert decision.kind == "EXECUTE", decision

    print("ALL PASS")

    db.close()
