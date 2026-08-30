import unittest
from unittest.mock import MagicMock


class TestWorldTrigger(unittest.TestCase):
    def test_trigger_on_critical_ram(self):
        from core.autonomous_runtime import AutonomousRuntime
        from core.world_probe import WorldProbe

        probe = WorldProbe(probe_interval_seconds=0)
        runtime = AutonomousRuntime(scheduler=MagicMock(), memory=MagicMock())
        runtime.world_probe = probe
        runtime._probe_world_on_pressure(force=True)
        calls = [
            c
            for c in runtime.memory.remember.mock_calls
        ]
        self.assertTrue(calls)  # событие записано

    def test_trigger_on_sleep_transition(self):
        from core.autonomous_runtime import AutonomousRuntime
        from core.world_probe import WorldProbe

        probe = WorldProbe(probe_interval_seconds=0)
        runtime = AutonomousRuntime(scheduler=MagicMock(), memory=MagicMock())
        runtime.world_probe = probe
        runtime._record_sleep_event(was_asleep=True)
        calls = [
            c
            for c in runtime.memory.remember.mock_calls
        ]
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()
