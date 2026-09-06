import time

from core.decision_core import Action
from identity.goal_manager import GoalManager


class _FakeSelfState:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class _FakePlanner:
    def __init__(self, active_plans=None):
        self.active_plans = active_plans or {}

    def get_plan(self, value):
        return self.active_plans.get(value)

    def next_task(self, value):
        plan = self.active_plans.get(value)
        if not plan:
            return None
        return _FakeTask(plan[0])


class _FakeTask:
    def __init__(self, title):
        self.title = title


def _manager(active_values, candidate_values):
    mgr = GoalManager(
        _FakeSelfState(),
        planner=_FakePlanner(),
    )

    for value in active_values:
        mgr.add_candidate(
            value,
            motivation=0.9,
            priority=0.9,
            confidence=0.9,
            source="self",
        )
        mgr.activate(value)

    for value in candidate_values:
        mgr.add_candidate(
            value,
            motivation=0.7,
            priority=0.6,
            confidence=0.7,
            source="curiosity",
        )

    return mgr


def _core(manager):
    from core.decision_core import DecisionCore

    core = DecisionCore.__new__(DecisionCore)
    core.goal_manager = manager
    core.memory = None
    core.server = None
    core.llm = None
    return core


def _state(**overrides):
    state = {
        "incoming_call": None,
        "emotions": {"frustration": 0.1},
        "inbox_unread": 0,
        "idle_seconds": 0,
    }
    state.update(overrides)
    return state


def test_curiosity_candidate_activated_when_slot_free():
    manager = _manager(
        active_values=["разобраться с кодом"],
        candidate_values=[
            "Исследовать тему: чёрные дыры",
        ],
    )

    action = _core(manager)._local_rules(_state())

    assert action is not None
    assert action.kind == "ACTIVATE_GOAL"
    assert action.payload["value"].startswith(
        "Исследовать тему:"
    )


def test_active_goal_proceeds_when_slots_full():
    manager = _manager(
        active_values=[
            "разобраться с кодом",
            "починить баг",
            "написать тесты",
        ],
        candidate_values=[
            "Исследовать тему: чёрные дыры",
        ],
    )
    manager.planner.active_plans = {
        "разобраться с кодом": ["понять стек"],
    }

    action = _core(manager)._local_rules(_state())

    assert action is not None
    assert action.kind == "EXECUTE"
    assert action.payload["goal"] == (
        "разобраться с кодом"
    )


def test_curiosity_gives_way_under_high_frustration():
    manager = _manager(
        active_values=["разобраться с кодом"],
        candidate_values=[
            "Исследовать тему: чёрные дыры",
        ],
    )

    action = _core(manager)._local_rules(
        _state(
            emotions={
                "frustration": 0.85,
            }
        )
    )

    assert action is not None
    assert action.kind != "ACTIVATE_GOAL"


def test_periodic_curiosity_cooldown_is_shorter():
    from core.curiosity import CuriosityDirector

    director = CuriosityDirector(
        _FakeSelfState(),
        GoalManager(
            _FakeSelfState(),
            planner=_FakePlanner(),
        ),
    )

    assert (
        director.min_interval_seconds
        <= 600
    )


def test_screen_comment_sent_on_new_description():
    runtime = _runtime()
    server = _FakeServer()
    runtime.eddie_server = server

    runtime._maybe_comment_screen(
        {"description": "На экране открыт редактор кода с окном терминала."}
    )

    assert server.sent == [
        "Смотрю на экран: На экране открыт редактор кода с окном терминала."
    ]


def test_screen_comment_repeats_same_only_after_cooldown():
    runtime = _runtime()
    server = _FakeServer()
    runtime.eddie_server = server

    runtime._maybe_comment_screen(
        {"description": "На экране открыт браузер."}
    )
    runtime._maybe_comment_screen(
        {"description": "На экране открыт браузер."}
    )

    assert len(server.sent) == 1


def test_screen_comment_ignores_empty_description():
    runtime = _runtime()
    server = _FakeServer()
    runtime.eddie_server = server

    runtime._maybe_comment_screen(
        {"description": ""}
    )

    assert server.sent == []


def test_screen_comment_respects_cooldown_window():
    runtime = _runtime()
    server = _FakeServer()
    runtime.eddie_server = server
    runtime._last_screen_comment_at = (
        time.time() - 100
    )
    runtime._last_comment_description = (
        "old"
    )

    runtime._maybe_comment_screen(
        {"description": "На экране терминал."}
    )
    runtime._maybe_comment_screen(
        {"description": "На экране чат."}
    )

    assert server.sent == []


class _FakeServer:
    def __init__(self):
        self.sent = []

    def send_initiative(self, text, speak=True):
        self.sent.append(text)


def _runtime():
    import core.autonomous_runtime as ar

    r = ar.AutonomousRuntime.__new__(
        ar.AutonomousRuntime
    )
    r._last_screen_comment_at = 0.0
    r._last_comment_description = None
    return r