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


class FakeScheduler:
    def __init__(self):
        self.calls = 0

    def event_happened(self, significant=True):
        self.calls += 1
        return False


class FakeCogProcessor:
    def __init__(self):
        self.calls = 0

    def process_next(self):
        self.calls += 1
        return {"status": "EMPTY"}


class FakeAgent:
    def __init__(self, scheduler, cog):
        self.reflection_scheduler = scheduler
        self.cognitive_processor = cog

    def __getattr__(self, name):
        return None


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

    scheduler = FakeScheduler()
    cog = FakeCogProcessor()
    fake_agent = FakeAgent(scheduler, cog)

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
        agent=fake_agent,
        outbox=None,
        server=fake_server,
        decision_core=decision_core,
    )

    # 1. Пусто + короткое безделье -> IDLE, хук когниции ещё не зовётся мёртво
    result = orchestrator.tick()
    assert result.status == "NO_MOTIVATION", result.status
    assert decision_core.llm_calls == 0

    # 2. Кандидат -> GOAL_ACTIVATED (локально)
    goal_manager.add_candidate(
        value="Изучить тему: космос",
        motivation=0.9,
        priority=0.9,
        confidence=0.9,
    )
    result = orchestrator.tick()
    assert result.status == "GOAL_ACTIVATED", result.status

    # 3. Активная цель без плана -> PLAN_CREATED
    result = orchestrator.tick()
    assert result.status == "PLAN_CREATED", result.status
    assert fake_plan.calls == 1

    # 4. Есть план -> EXECUTE
    result = orchestrator.tick()
    assert result.status == "EXECUTED", result.status

    # 5. После исполненного действия cognition должна продвигаться:
    #    рефлексия получает событие, процессор будится.
    assert scheduler.calls >= 1, (
        "reflection_scheduler.event_happened должен вызываться "
        "после автономного действия"
    )
    assert cog.calls >= 1, (
        "cognitive_processor.process_next должен вызываться "
        "после автономного действия"
    )

    print("scheduler events:", scheduler.calls)
    print("cognition process calls:", cog.calls)
    print("exec loop calls:", fake_loop.calls)
    print("ALL PASS")

    db.close()
