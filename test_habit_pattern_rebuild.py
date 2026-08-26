from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import DecisionCore
from core.situation import encode_situation
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


class FakeOrchestrator:
    def _cloud_chat(self, system, user, options, task):
        raise AssertionError("LLM не должен вызываться")


STATE = {
    "goal": None,
    "task_type": None,
    "inbox_unread": 0,
    "affect": 0.0,
    "emotions": {},
    "period": "day",
    "freshness": 0,
}

KEY = encode_situation(STATE)


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    # Устойчивая привычка: в этой ситуации EddieAI
    # обычно выполняет шаг (EXECUTE)
    state.set(
        "personality_traits",
        {
            "habit:key": {
                "field": "habit",
                "value": f"situation_action:{KEY}:::EXECUTE",
                "status": "ACTIVE",
            }
        },
    )

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
        model_orchestrator=FakeOrchestrator(),
    )

    state.set("interests", [])

    # Паттерн потерян, но привычка сохранилась ->
    # ядро восстанавливает действие БЕЗ LLM
    decision = core.decide(STATE)

    assert decision.kind == "EXECUTE", decision
    assert core.llm_calls == 0, (
        "восстановление из привычки не должно звать LLM"
    )

    # Паттерн теперь записан -> переиспользуется
    decision = core.decide(STATE)

    assert decision.kind == "EXECUTE", decision
    assert core.llm_calls == 0

    print("ALL PASS")

    db.close()
