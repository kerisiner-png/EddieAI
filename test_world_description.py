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


if __name__ == "__main__":
    unittest.main()