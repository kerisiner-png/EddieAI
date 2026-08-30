import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.autonomous_runtime import AutonomousRuntime


class FakeStateScheduler:
    def __init__(self):
        self.calls = 0
        self.state = "IDLE"
        self.inbox_unread = None
        self.idle_seconds = None

    def tick(self):
        self.calls += 1
        return {"decision": "noop"}


def test_executor_initialized_on_construction():
    runtime = AutonomousRuntime(scheduler=None)
    assert hasattr(runtime, "_executor"), (
        "_executor должен существовать сразу после __init__, "
        "до любой смены сна/бодрствования"
    )
    assert runtime._executor is not None


def test_background_tick_runs_without_sleep_transition():
    scheduler = FakeStateScheduler()
    runtime = AutonomousRuntime(
        scheduler=scheduler,
        memory=None,
        orchestrator=None,
    )
    result = runtime.tick_background()
    assert result["status"] in (
        "STARTED",
        "ALREADY_RUNNING",
    ), f"вместо старта фонового тика: {result}"
    future = runtime._background_future
    assert future is not None


if __name__ == "__main__":
    test_executor_initialized_on_construction()
    test_background_tick_runs_without_sleep_transition()
    print("ALL OK")
