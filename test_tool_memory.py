from identity.action_executor import ActionExecutor
from identity.filesystem_executor import FilesystemExecutor
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner

from memory.database import Memory
from memory.tool_experience import ToolExperienceRecorder


memory = Memory()

registry = ToolRegistry()

registry.register(
    name="filesystem",
    executor=FilesystemExecutor(
        r"C:\EddieAI"
    ),
    description="EddieAI filesystem sandbox.",
    enabled=True,
)

runner = ToolRunner(
    registry,
    filesystem_root=r"C:\EddieAI",
)

recorder = ToolExperienceRecorder(
    memory
)

action = ActionExecutor().create(
    action_type="READ_FILE",
    target="Прочитать собственный код",
    parameters={
        "path": r"core\agent.py",
    },
    reason="Изучение собственного проекта.",
    dry_run=False,
)

result = runner.run(action)

print("TOOL RESULT:")
print(result["status"])

recorded = recorder.record(
    action,
    result,
    owner="SELF",
    personal_experience=True,
)

print()
print("MEMORY EVENT:")
print(
    recorded["event"]
)

print()
print("KNOWLEDGE:")
print(
    recorded["knowledge"].to_dict()
)

memory.close()
