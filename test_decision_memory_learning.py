from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import (
    DecisionCore,
    NEEDS_NEW_PATTERN,
)
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


class FakeOrchestrator:
    def _cloud_chat(self, system, user, options, task):
        raise AssertionError(
            "LLM не должен вызываться при "
            "обучении из памяти"
        )


STATE = {
    "goal": None,
    "task_type": None,
    "inbox_unread": 0,
    "affect": None,
    "freshness": 0,
}


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    # Накопленный опыт: интерес в self_state
    state.set("interests", ["космос"])

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
        model_orchestrator=FakeOrchestrator(),
    )

    # Первый decide: локальных правил нет, паттерна нет,
    # но обучение из памяти создаёт паттерн (БЕЗ LLM)
    decision = core.decide(STATE)

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert decision.payload == {
        "value": "изучить тему: космос"
    }, decision
    assert core.llm_calls == 0, (
        "обучение из памяти не должно звать LLM"
    )

    # Повторный decide: паттерн уже накоплен -> без LLM
    decision = core.decide(STATE)

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert core.llm_calls == 0

    # learn_from_memory на консолидации: идемпотентно
    created = core.learn_from_memory()

    assert created == 0, (
        "паттерн уже есть, повторное обучение "
        "не должно создавать новый"
    )

    # Число NEEDS_NEW_PATTERN упало до нуля
    needs_count = 0

    for _ in range(5):
        if core.decide(STATE) == NEEDS_NEW_PATTERN:
            needs_count += 1

    assert needs_count == 0, (
        "после обучения NEEDS_NEW_PATTERN "
        "не должен возвращаться"
    )

    stats = db.pattern_stats()

    print("STATS:", stats)
    print("LLM calls:", core.llm_calls)
    print("ALL PASS")

    db.close()
