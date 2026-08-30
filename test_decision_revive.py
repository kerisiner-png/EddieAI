from datetime import datetime, timedelta, timezone
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
            ["Провести исследование: тема"],
        )
        return self.goal_manager.planner.get_plan(goal)


def _dead_interest_goal(goal_manager):
    goal_manager.add_candidate(
        value="изучить тему: понимание устройства мира",
        motivation=0.7,
        priority=0.7,
        confidence=0.7,
    )
    goal_manager.ensure_plan(
        "изучить тему: понимание устройства мира",
        ["Собрать материал"],
    )
    goal_manager.planner.complete_task(
        "изучить тему: понимание устройства мира",
        "Собрать материал",
    )
    goal_manager.complete(
        "изучить тему: понимание устройства мира"
    )


with TemporaryDirectory() as temp:
    # ---- A. Свежий оркестратор: счётчик безделья не
    #      заморожен на None с момента создания.
    state = SelfState(Path(temp) / "self_state.json")
    state.set(
        "interests",
        ["понимание устройства мира"],
    )

    db = Memory(Path(temp) / "memory.db")
    goal_manager = GoalManager(state, GoalPlanner(state))

    _dead_interest_goal(goal_manager)

    fake_loop = FakeLoop()
    fake_plan = FakePlan(goal_manager)
    fake_server = FakeServer()

    decision_core = DecisionCore(
        memory=db,
        goal_manager=goal_manager,
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

    # 1. После создания процесса время последнего
    #    действия не пустое.
    assert orchestrator._last_action_at is not None, (
        "_last_action_at должен стартовать от создания процесса"
    )

    # 2. COMPLETED-интерес возвращает НОВУЮ followup-цель,
    #    а не мёртвую и не None.
    target = decision_core._next_interest_target()

    assert target is not None, (
        "интерес должен давать цель-углубление"
    )
    assert target != "изучить тему: понимание устройства мира", (
        "нельзя оживлять завершённую цель повторно"
    )
    assert goal_manager.get(target) is None, (
        "followup-цель должна быть новой"
    )

    # 3. Долгое безделье в свежем процессе -> деятельность
    #    (GOAL_ACTIVATED), а не NO_MOTIVATION и не CALL.
    orchestrator._last_action_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1500)
    )

    result = orchestrator.tick()

    assert result.status == "GOAL_ACTIVATED", (
        f"ожидали GOAL_ACTIVATED, получено {result.status}"
    )

    active = goal_manager.active()

    assert len(active) == 1, active
    assert active[0].value.startswith(
        "Найти новые аспекты темы:"
    ), active[0].value

    # 4. Следующий тик: активная цель без плана ->
    #    GENERATE_PLAN (локально, без LLM).
    result = orchestrator.tick()

    assert result.status == "PLAN_CREATED", result.status
    assert decision_core.llm_calls == 0, (
        "мотивация локальна, LLM не зовётся"
    )

    # 5. План есть -> EXECUTE.
    result = orchestrator.tick()

    assert result.status == "EXECUTED", result.status
    assert fake_loop.calls == 1
    assert decision_core.llm_calls == 0

    db.close()

print("ALL PASS")