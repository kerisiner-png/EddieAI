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
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def _cloud_chat(self, system, user, options, task):
        self.calls += 1
        return self.reply


STATE = {
    "goal": "Изучить тему: космос",
    "task_type": "research",
    "inbox_unread": 0,
    "affect": {"valence": 0.6},
    "period": "day",
    "freshness": 5,
}


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    # Чистый путь новизны: без интересов из памяти,
    # чтобы проверка дошла до LLM-гейта
    state.set("interests", [])

    core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
    )

    # 1. Нет активных целей, нет кандидатов,
    #    паттернов нет -> NEEDS_NEW_PATTERN
    decision = core.decide(STATE)

    assert decision == NEEDS_NEW_PATTERN, (
        "новая ситуация без паттерна должна "
        "вернуть NEEDS_NEW_PATTERN"
    )

    assert core.llm_calls == 0, (
        "decide не должен звать LLM"
    )

    # 2. learn: один вызов LLM -> паттерн сохранён
    fake = FakeOrchestrator(
        '{"kind": "REFLECT", "payload": null}'
    )

    core.llm = core.llm.__class__(fake)

    action = core.learn(core.key(STATE), "нет целей")

    assert action.kind == "REFLECT", action
    assert fake.calls == 1, "learn должен звать LLM один раз"

    # 3. Повторный decide на той же ситуации ->
    #    паттерн найден, LLM НЕ зовётся
    decision = core.decide(STATE)

    assert decision == action, decision

    assert fake.calls == 1, (
        "повторный decide не должен звать LLM"
    )

    # 4. Локальное правило: активная цель + план ->
    #    EXECUTE (без LLM)
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
    assert fake.calls == 1, (
        "локальный decide не должен звать LLM"
    )

    # 5. Локальное правило: активная цель без плана ->
    #    GENERATE_PLAN
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

    # 6. Локальное правило: нет активных целей,
    #    но есть кандидат -> ACTIVATE_GOAL
    goal_manager.abandon("Изучить тему: океан")

    goal_manager.add_candidate(
        value="Изучить тему: звёзды",
        motivation=0.7,
        priority=0.7,
        confidence=0.7,
    )

    decision = core.decide(STATE)

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert decision.payload == {"value": "Изучить тему: звёзды"}

    print("LLM CALLS:", fake.calls)
    print("ALL PASS")

    db.close()
