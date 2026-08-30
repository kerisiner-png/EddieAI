import unittest
from unittest.mock import patch


class TestWorldProbeExtras(unittest.TestCase):
    def test_probe_includes_cpu_key(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("cpu", snap)

    def test_probe_includes_top_processes_key(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("top_processes", snap)

    @patch("core.world_probe._cpu_percent", return_value=None)
    def test_cpu_graceful_failure(self, _c):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsNone(snap["cpu"])

    @patch("core.world_probe._top_processes", return_value=[])
    def test_top_processes_graceful_empty(self, _t):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertEqual(snap["top_processes"], [])

    def test_snapshot_text_mentions_cpu_when_present(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = {
            "status": "OK",
            "ram": {"load": 42, "avail_mb": 800},
            "disk": {"status": "OK"},
            "cpu": {"percent": 23.0},
            "top_processes": [
                {"name": "python.exe", "memory_mb": 320}
            ],
        }
        text = wp.snapshot_text(snap)
        self.assertIn("CPU", text)
        self.assertIn("python.exe", text)


if __name__ == "__main__":
    unittest.main()
