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
    #    собственная воля -> CALL (без «часового» порога)
    decision = core.decide(
        dict(STATE, idle_seconds=900)
    )

    assert decision.kind == "CALL", decision

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

    # 7. Правило воли напрямую: долгое безделье -> CALL
    state7 = SelfState(
        Path(temp) / "state7.json"
    )
    state7.set("interests", [])

    gm7 = GoalManager(
        state7,
        GoalPlanner(state7),
    )

    core7 = DecisionCore(
        memory=db,
        goal_manager=gm7,
    )

    decision = core7._local_rules(
        dict(STATE, idle_seconds=900)
    )

    assert decision.kind == "CALL", decision

    # 8. Если уже есть необработанная инициатива —
    #    CALL не дублируется
    state8 = SelfState(
        Path(temp) / "state8.json"
    )
    state8.set("interests", [])

    server8 = type(
        "S8",
        (),
        {"pending_initiative": {"text": "x"}},
    )()

    core8 = DecisionCore(
        memory=db,
        goal_manager=GoalManager(
            state8,
            GoalPlanner(state8),
        ),
        server=server8,
    )

    decision = core8._local_rules(
        dict(STATE, idle_seconds=900)
    )

    assert decision is None, decision

    print("ALL PASS")

    db.close()

with TemporaryDirectory() as temp9:
    state9 = SelfState(
        Path(temp9) / "state9.json"
    )
    state9.set("interests", [])

    core9 = DecisionCore(
        memory=object(),
        goal_manager=GoalManager(
            state9,
            GoalPlanner(state9),
        ),
    )

    # 13. Фрустрация 1.0 не блокирует чтение
    #     сообщений Эдди (READ_INBOX)
    decision = core9._local_rules(
        dict(
            STATE,
            inbox_unread=2,
            emotions={"frustration": 1.0},
        )
    )

    assert decision.kind == "READ_INBOX", (
        decision
    )

