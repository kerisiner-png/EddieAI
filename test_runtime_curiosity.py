import unittest
from unittest.mock import MagicMock


class TestRuntimeCuriosity(unittest.TestCase):
    def test_runtime_has_director_and_probe(self):
        from core.autonomous_runtime import (
            AutonomousRuntime,
        )
        from core.world_probe import WorldProbe

        runtime = AutonomousRuntime(
            scheduler=MagicMock(),
        )
        self.assertIsInstance(
            runtime.world_probe, WorldProbe
        )
        self.assertTrue(
            hasattr(runtime, "curiosity")
        )

        runtime = AutonomousRuntime(
            scheduler=MagicMock(),
            curiosity=MagicMock(),
        )
        self.assertIsNotNone(runtime.curiosity)

    def test_cycle_creates_goal_when_curious(self):
        from core.curiosity import CuriosityDirector

        ss = MagicMock()
        ss.get.side_effect = (
            lambda k, d=None: {
                "interests": ["устройство мира"],
                "usage_today": {},
                "world_description": None,
            }.get(k, d)
        )
        gm = MagicMock()
        d = CuriosityDirector(
            ss,
            gm,
            min_interval_seconds=0,
        )
        res = d.evaluate(asleep=False)
        self.assertTrue(res["should_act"])


if __name__ == "__main__":
    unittest.main()