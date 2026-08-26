from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import DecisionCore
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


STATE = {
    "goal": "Изучить тему: космос",
    "task_type": "research",
    "inbox_unread": 0,
    "affect": {"valence": 0.6},
    "period": "day",
    "freshness": 5,
    "idle_seconds": 0,
}


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    state.set("interests", [])

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
    )

    # 1. Короткое безделье, ничего нет -> IDLE (отдых)
    decision = core.decide(STATE)

    assert decision.kind == "IDLE", decision

    # 2. Долгое безделье, нет интересов ->
    #    скука -> рефлексия
    decision = core.decide(
        dict(STATE, idle_seconds=900)
    )

    assert decision.kind == "REFLECT", decision

    # 3. Долгое безделье + интерес ->
    #    скука -> исследовать (ACTIVATE_GOAL)
    state.set("interests", ["космос"])

    decision = core.decide(
        dict(STATE, idle_seconds=900)
    )

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert decision.payload == {
        "value": "изучить тему: космос"
    }, decision

    state.set("interests", [])

    # 4. Локальное правило: активная цель + план -> EXECUTE
    goal_manager.add_candidate(
        value="Изучить тему: космос",
        motivation=0.9,
        priority=0.9,
        confidence=0.9,
    )
    goal_manager.activate("Изучить тему: космос")
    goal_manager.ensure_plan(
        "Изучить тему: космос",
        ["Провести исследование: космос"],
    )

    decision = core.decide(STATE)

    assert decision.kind == "EXECUTE", decision

    # 5. Активная цель без плана -> GENERATE_PLAN
    goal_manager.complete("Изучить тему: космос")

    goal_manager.add_candidate(
        value="Изучить тему: океан",
        motivation=0.8,
        priority=0.8,
        confidence=0.8,
    )
    goal_manager.activate("Изучить тему: океан")

    decision = core.decide(
        dict(STATE, goal="Изучить тему: океан")
    )

    assert decision.kind == "GENERATE_PLAN", decision

    # 6. Нет активных целей, но есть кандидат -> ACTIVATE_GOAL
    goal_manager.abandon("Изучить тему: океан")

    goal_manager.add_candidate(
        value="Изучить тему: звёзды",
        motivation=0.7,
        priority=0.7,
        confidence=0.7,
    )

    decision = core.decide(STATE)

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert decision.payload == {
        "value": "Изучить тему: звёзды"
    }

    print("ALL PASS")

    db.close()
