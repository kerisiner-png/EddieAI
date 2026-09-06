import core.autonomous_runtime as ar


class _FakeAffect:
    def __init__(self):
        self.decayed = 0

    def decay(self):
        self.decayed += 1


class _BrokenAffect:
    def decay(self):
        raise RuntimeError("x")


class _FakeAgent:
    def __init__(self, affect=None):
        self.affective_state = affect


class _FakeOrchestrator:
    def __init__(self, agent=None):
        self.agent = agent


class _FakeRuntime:
    def __new__(cls):
        r = ar.AutonomousRuntime.__new__(
            ar.AutonomousRuntime
        )
        return r


def _runtime(agent):
    r = ar.AutonomousRuntime.__new__(
        ar.AutonomousRuntime
    )
    r.orchestrator = _FakeOrchestrator(agent)
    return r


def test_decay_affect_calls_decay():
    affect = _FakeAffect()
    r = _runtime(_FakeAgent(affect))
    r._decay_affect()
    assert affect.decayed == 1


def test_decay_affect_tolerates_missing_orchestrator():
    r = ar.AutonomousRuntime.__new__(
        ar.AutonomousRuntime
    )
    r._decay_affect()


def test_decay_affect_tolerates_missing_agent():
    r = _runtime(None)
    r._decay_affect()


def test_decay_affect_tolerates_missing_state():
    r = _runtime(_FakeAgent(None))
    r._decay_affect()


def test_decay_affect_tolerates_broken_affect():
    r = _runtime(_FakeAgent(_BrokenAffect()))
    r._decay_affect()


if __name__ == "__main__":
    test_decay_affect_calls_decay()
    test_decay_affect_tolerates_missing_orchestrator()
    test_decay_affect_tolerates_missing_agent()
    test_decay_affect_tolerates_missing_state()
    test_decay_affect_tolerates_broken_affect()
    print("ALL OK")
