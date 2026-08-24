from pathlib import Path
from tempfile import TemporaryDirectory

from identity.action_executor import ActionExecutor
from identity.llm_executor import LLMExecutor
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner
from identity.web_executor import WebExecutor

from memory.database import Memory
from memory.external_knowledge import (
    ExternalKnowledgeRecorder,
)
from memory.self_interpretation import (
    SelfInterpretation,
)


with TemporaryDirectory() as temp:
    memory = Memory(
        Path(temp) / "memory.db"
    )

    registry = ToolRegistry()

    registry.register(
        name="llm",
        executor=LLMExecutor(),
        description="Local LLM.",
        enabled=True,
    )

    registry.register(
        name="web",
        executor=WebExecutor(),
        description="Web search.",
        enabled=True,
    )

    runner = ToolRunner(
        registry,
        filesystem_root=r"C:\EddieAI",
        external_recorder=(
            ExternalKnowledgeRecorder(
                memory
            )
        ),
        self_interpreter=(
            SelfInterpretation(
                memory
            )
        ),
    )

    action = ActionExecutor().create(
        action_type="RESEARCH",
        target="исследовать космические миссии NASA",
        parameters={
            "query": (
                "NASA space missions"
            ),
            "limit": 3,
        },
        reason="Проверка research pipeline.",
        dry_run=False,
    )

    result = runner.run(action)

    print("STATUS:")
    print(result["status"])

    print()
    print("RESULT:")
    print(result["result"])

    print()
    print("KNOWLEDGE:")

    rows = memory.connection.execute("""
        SELECT
            owner,
            source_type,
            source,
            confidence,
            verified,
            personal_experience,
            content
        FROM knowledge
        ORDER BY id ASC
    """).fetchall()

    for row in rows:
        print(dict(row))

    memory.close()
