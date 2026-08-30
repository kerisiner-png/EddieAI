import unittest
from unittest.mock import MagicMock


class FakeCuriosity:
    def __init__(self):
        self.calls = []

    def track_action(self, kind):
        self.calls.append(kind)


class TestUsageHooks(unittest.TestCase):
    def test_tool_runner_increments_web(self):
        from identity.tool_runner import ToolRunner

        curiosity = FakeCuriosity()
        registry = MagicMock()
        tool = MagicMock()
        tool.executor.search.return_value = {"status": "OK", "results": []}
        registry.require.return_value = tool
        runner = ToolRunner(registry=registry, filesystem_root=r"C:\EddieAI")
        runner.curiosity = curiosity
        result = runner._execute_web_search(query="test", limit=3)
        self.assertEqual(result["status"], "OK")
        self.assertIn("web", curiosity.calls)

    def test_llm_chat_increments_llm(self):
        from identity.llm_access import CloudFirstLlm

        curiosity = FakeCuriosity()
        orchestrator = MagicMock()
        orchestrator._cloud_chat.return_value = "ответ"
        llm = CloudFirstLlm(model_orchestrator=orchestrator)
        llm.curiosity = curiosity
        result = llm.chat(system="s", user="u", options={})
        self.assertEqual(result, "ответ")
        self.assertIn("llm", curiosity.calls)

    def test_direct_web_action_increments_web(self):
        from identity.tool_runner import ToolRunner

        curiosity = FakeCuriosity()
        registry = MagicMock()
        tool = MagicMock()
        tool.executor.search.return_value = {"status": "OK", "results": []}
        registry.require.return_value = tool
        runner = ToolRunner(
            registry=registry,
            filesystem_root=r"C:\EddieAI",
        )
        runner.curiosity = curiosity

        class Action:
            action_type = "WEB_SEARCH"
            parameters = {"query": "test", "limit": 2}

        result = runner._execute_web(
            tool,
            Action(),
        )
        self.assertEqual(result["status"], "OK")
        self.assertIn("web", curiosity.calls)

    def test_direct_web_action_without_curiosity(self):
        from identity.tool_runner import ToolRunner

        registry = MagicMock()
        tool = MagicMock()
        tool.executor.search.return_value = {"status": "OK", "results": []}
        registry.require.return_value = tool
        runner = ToolRunner(
            registry=registry,
            filesystem_root=r"C:\EddieAI",
        )
        result = runner._execute_web(
            tool,
            type(
                "Action",
                (),
                {
                    "action_type": "WEB_SEARCH",
                    "parameters": {"query": "test"},
                },
            )(),
        )
        self.assertEqual(result["status"], "OK")


if __name__ == "__main__":
    unittest.main()