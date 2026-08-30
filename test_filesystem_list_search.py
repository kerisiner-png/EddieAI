import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from identity.filesystem_executor import (
    FilesystemExecutor,
)


class TestFilesystemListSearch(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "alpha").mkdir()
        (self.root / "alpha" / "beta").mkdir()
        (self.root / "readme.txt").write_text(
            "hello",
            encoding="utf-8",
        )
        (self.root / "alpha" / "beta" / "notes.md").write_text(
            "note body",
            encoding="utf-8",
        )
        self.executor = FilesystemExecutor(
            root=str(self.root)
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_returns_directory_entries(self):
        result = self.executor.list(str(self.root))
        self.assertEqual(result["status"], "OK")
        names = [e["name"] for e in result["entries"]]
        self.assertIn("alpha", names)
        self.assertIn("readme.txt", names)

    def test_list_rejects_outside_sandbox(self):
        result = self.executor.list(
            str(Path(self._tmp.name).parent)
        )
        self.assertEqual(result["status"], "DENIED")

    def test_list_missing_path(self):
        result = self.executor.list(
            str(self.root / "nope")
        )
        self.assertEqual(result["status"], "NOT_FOUND")

    def test_search_finds_by_name(self):
        result = self.executor.search("notes")
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["results"][0]["name"],
            "notes.md",
        )

    def test_search_respects_limit(self):
        result = self.executor.search("a", limit=1)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["results"]), 1)

    def test_search_empty_query(self):
        result = self.executor.search("   ")
        self.assertEqual(result["status"], "EMPTY_QUERY")


if __name__ == "__main__":
    unittest.main()
