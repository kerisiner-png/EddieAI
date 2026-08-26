from pathlib import Path
from tempfile import TemporaryDirectory

from core.autonomy_orchestrator import (
    AutonomyOrchestrator,
)
from core.decision_core import DecisionCore
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


class FakeOrchestrator:
    def _cloud_chat(self, system, user, options, task):
        return '{"kind": "IDLE", "payload": null}'


class FakeHistory:
    def chat_unread_meta(self):
        return {"count": 0}

    def chat_unread(self):
        return 0

    def chat_recent(self, limit):
        return []


class FakeServer:
    def __init__(self):
        self.history = FakeHistory()


class FakeLoop:
    def __init__(self):
        self.calls = 0

    def run_once(self):
        self.calls += 1
        return {"status": "OK", "steps": 1}


class FakePlan:
    def __init__(self, goal_manager):
        self.goal_manager = goal_manager
        self.calls = 0

    def generate(self, goal, context):
        self.calls += 1
        self.goal_manager.ensure_plan(
            goal,
            ["Провести исследование: космос"],
        )
        return self.goal_manager.planner.get_plan(goal)


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    state.set("interests", [])

    fake_loop = FakeLoop()
    fake_plan = FakePlan(goal_manager)
    fake_server = FakeServer()

    decision_core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
        model_orchestrator=FakeOrchestrator(),
        agent_loop=fake_loop,
    )

    orchestrator = AutonomyOrchestrator(
        goal_manager=goal_manager,
        goal_generator=None,
        goal_plan_generator=fake_plan,
        agent_loop=fake_loop,
        agent=None,
        outbox=None,
        server=fake_server,
        decision_core=decision_core,
    )

    # 1. Пусто + короткое безделье -> IDLE (NO_MOTIVATION),
    #    LLM не вызывается
    result = orchestrator.tick()

    assert result.status == "NO_MOTIVATION", result.status
    assert decision_core.llm_calls == 0, (
        "рутина не должна звать LLM"
    )

    # 2. Появляется кандидат -> ACTIVATE_GOAL (локально)
    goal_manager.add_candidate(
        value="Изучить тему: космос",
        motivation=0.9,
        priority=0.9,
        confidence=0.9,
    )

    result = orchestrator.tick()

    assert result.status == "GOAL_ACTIVATED", result.status
    assert decision_core.llm_calls == 0, (
        "активация цели локальна"
    )

    # 3. Активная цель без плана -> GENERATE_PLAN (локально)
    result = orchestrator.tick()

    assert result.status == "PLAN_CREATED", result.status
    assert fake_plan.calls == 1
    assert decision_core.llm_calls == 0

    # 4. Есть план -> EXECUTE (локально)
    result = orchestrator.tick()

    assert result.status == "EXECUTED", result.status
    assert fake_loop.calls == 1
    assert decision_core.llm_calls == 0

    # 5. Снова EXECUTE, план-генератор НЕ перевызывается
    result = orchestrator.tick()

    assert result.status == "EXECUTED", result.status
    assert fake_plan.calls == 1, (
        "план не должен генерироваться повторно"
    )
    assert decision_core.llm_calls == 0

    print("LLM calls (decision core):", decision_core.llm_calls)
    print("plan calls:", fake_plan.calls)
    print("exec loop calls:", fake_loop.calls)
    print("ALL PASS")

    db.close()
