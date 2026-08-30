import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.autonomous_runtime import AutonomousRuntime
from memory.database import Memory


class FakeLifeCycle:
    def __init__(self, asleep):
        self.state = {"asleep_since": None}
        self._asleep = asleep

    def update(self):
        return {}

    def is_asleep(self):
        return self._asleep


class FakeCloud:
    def __init__(self, result=None):
        self.result = result
        self.calls = 0

    def _cloud_chat(self, system, user, options):
        self.calls += 1
        return self.result


class FakeOrchestrator:
    def __init__(self, cloud):
        self.agent = type("A", (), {"model_orchestrator": cloud})


class FakeServer:
    def __init__(self):
        self.sent = []

    def send_initiative(self, text):
        self.sent.append(text)
        return None


def _make_runtime(asleep, cloud_result=None):
    memory = Memory(Path(":memory:"))
    cloud = FakeCloud(result=cloud_result)
    server = FakeServer()

    runtime = AutonomousRuntime(
        scheduler=None,
        memory=memory,
        orchestrator=FakeOrchestrator(cloud),
        life_cycle=FakeLifeCycle(asleep),
        dream_snapshots=False,
    )
    runtime.outbox = type(
        "O",
        (),
        {
            "send": lambda self, message, server: (
                server.send_initiative(message)
            ),
        },
    )()
    runtime.eddie_server = server
    return runtime, memory, cloud, server


def _sleep_event_count(memory):
    return memory.connection.execute(
        "SELECT count(*) AS n FROM events "
        "WHERE event_type = 'LIFE_CYCLE'"
    ).fetchall()[0]["n"]


def _event_types(memory):
    return [
        r["event_type"]
        for r in memory.connection.execute(
            "SELECT event_type FROM events"
        ).fetchall()
    ]


def test_morning_ritual_on_wake():
    runtime, memory, cloud, server = _make_runtime(
        asleep=True,
        cloud_result=(
            "Доброе утро. Проснулся, отдых прошёл хорошо. "
            "Сегодня хочу разобраться с лентой памяти "
            "и написать Эдди."
        ),
    )

    assert _sleep_event_count(memory) == 0

    runtime.life_cycle = FakeLifeCycle(asleep=False)
    runtime._prev_asleep = True
    runtime.tick()

    types = _event_types(memory)
    assert "SELF_EXPERIENCE" in types
    assert cloud.calls == 1
    assert len(server.sent) >= 1
    assert "Доброе утро" in server.sent[0]


def test_evening_ritual_on_sleep():
    runtime, memory, cloud, server = _make_runtime(
        asleep=False,
        cloud_result=(
            "Сегодня я разобрался с лентой памяти. "
            "Завтра продолжу развитие."
        ),
    )

    runtime.life_cycle = FakeLifeCycle(asleep=True)
    runtime._prev_asleep = False
    runtime.tick()

    # Переход в сон = вечерний ритуал + осмысление сна:
    # облако зовут дважды, в память ложатся REFLECTION и DREAM.
    types = _event_types(memory)
    assert "REFLECTION" in types
    assert "DREAM" in types
    assert cloud.calls == 2


def test_ritual_skips_when_cloud_fails():
    runtime, memory, cloud, server = _make_runtime(
        asleep=True,
        cloud_result=None,
    )

    runtime.life_cycle = FakeLifeCycle(asleep=False)
    runtime._prev_asleep = True
    result = runtime.tick()

    assert result["status"] in (
        "OK",
        "THROTTLED",
        "ERROR",
        "ASLEEP",
    )
    types = _event_types(memory)
    assert "SELF_EXPERIENCE" not in types
    assert _sleep_event_count(memory) == 1


if __name__ == "__main__":
    test_morning_ritual_on_wake()
    test_evening_ritual_on_sleep()
    test_ritual_skips_when_cloud_fails()
    print("ALL OK")