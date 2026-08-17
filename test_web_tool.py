from identity.action_executor import ActionExecutor
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner
from identity.web_executor import WebExecutor


registry = ToolRegistry()

registry.register(
    name="web",
    executor=WebExecutor(),
    description="External web search.",
    enabled=True,
)

runner = ToolRunner(
    registry,
    filesystem_root=r"C:\EddieAI",
)

action = ActionExecutor().create(
    action_type="WEB_SEARCH",
    target="Найти базовую информацию о космосе",
    parameters={
        "query": "NASA space exploration",
        "limit": 3,
    },
    reason="Получение внешнего знания.",
    dry_run=False,
)

result = runner.run(action)

print("STATUS:")
print(result["status"])

print("TOOL:")
print(result.get("tool"))

print("RESULT:")
print(result.get("result"))
