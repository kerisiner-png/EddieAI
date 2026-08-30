import unittest


class TestWorldDescription(unittest.TestCase):
    def test_build_returns_text(self):
        from core.world_description import build_world_description

        text = build_world_description()
        self.assertIsInstance(text, str)
        self.assertGreaterEqual(len(text), 10)
        self.assertLessEqual(len(text), 500)

    def test_world_block_has_marker(self):
        from core.world_description import world_block

        block = world_block("вымышленная сводка")
        self.assertIn("ГДЕ ТЫ ЖИВЁШЬ", block)
        self.assertIn("вымышленная сводка", block)

    def test_ensure_fills_empty_self_state(self):
        from core.world_description import (
            ensure_world_description,
        )

        class FakeSelfState:
            def __init__(self):
                self._data = {}

            def get(self, key, default=None):
                return self._data.get(key, default)

            def set(self, key, value):
                self._data[key] = value

        state = FakeSelfState()
        text = ensure_world_description(state)
        self.assertIsInstance(text, str)
        self.assertEqual(
            state.get("world_description"),
            text,
        )

    def test_ensure_keeps_existing(self):
        from core.world_description import (
            ensure_world_description,
        )

        class FakeSelfState:
            def __init__(self):
                self._data = {
                    "world_description": (
                        "личная версия мира"
                    )
                }

            def get(self, key, default=None):
                return self._data.get(key, default)

            def set(self, key, value):
                self._data[key] = value

        state = FakeSelfState()
        text = ensure_world_description(state)
        self.assertEqual(
            text,
            "личная версия мира",
        )


if __name__ == "__main__":
    unittest.main()