from pathlib import Path
from tempfile import TemporaryDirectory

from core.autonomy_orchestrator import (
    AutonomyOrchestrator,
)
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


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


class FakeAgent:
    def __getattr__(self, name):
        return None


class FakeGoalGenerator:
    def __init__(self):
        self.calls = 0

    def generate(self):
        self.calls += 1
        return []


with TemporaryDirectory() as temp:
    state = SelfState(Path(temp) / "self_state.json")
    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    state.set("interests", [])

    fake_loop = FakeLoop()
    fake_plan = FakePlan(goal_manager)
    fake_server = FakeServer()
    fake_agent = FakeAgent()
    fake_generator = FakeGoalGenerator()

    orchestrator = AutonomyOrchestrator(
        goal_manager=goal_manager,
        goal_generator=fake_generator,
        goal_plan_generator=fake_plan,
        agent_loop=fake_loop,
        agent=fake_agent,
        outbox=None,
        server=fake_server,
        decision_core=None,
    )

    # Кандидат любопытства (как создаёт CuriosityDirector.topic_goal)
    goal_manager.add_candidate(
        value="Исследовать тему: устройство мира",
        motivation=0.6,
        priority=0.4,
        confidence=0.7,
        source="curiosity",
    )

    # Тик без decision_core должен активировать и исполнить
    # curiosity-кандидата (ранее застревал как CANDIDATE -> NO_MOTIVATION).
    # Первый тик: активация + создание плана. Второй: исполнение.
    for _ in range(3):
        result = orchestrator.tick()

    assert fake_plan.calls >= 1, (
        "для curiosity-цели должен быть создан план "
        f"(получено {result.status})"
    )
    assert fake_loop.calls >= 1, (
        "curiosity-цель должна исполниться через agent_loop "
        f"(получено {result.status})"
    )

    active = goal_manager.active()
    assert any(
        g.value == "Исследовать тему: устройство мира"
        for g in active
    ), "curiosity-цель должна стать ACTIVE без decision_core"

    print("plan calls:", fake_plan.calls)
    print("exec loop calls:", fake_loop.calls)
    print("active goals:", [g.value for g in active])
    print("ALL PASS")

    db.close()
