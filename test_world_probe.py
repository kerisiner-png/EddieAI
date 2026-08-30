import unittest
from unittest.mock import patch


class TestWorldProbe(unittest.TestCase):
    def test_probe_returns_snapshot_dict(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("timestamp", snap)
        self.assertIn("ram", snap)

    @patch("core.world_probe._meminfo", return_value=None)
    def test_partial_failure_keeps_snapshot(self, _m):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("ram", snap)
        self.assertIsNone(snap["ram"])

    def test_throttle_blocks_rapid_probes(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=3600)
        wp.probe(force=True)
        self.assertFalse(wp.allow())


if __name__ == "__main__":
    unittest.main()
