from pathlib import Path
from tempfile import TemporaryDirectory

from identity.action_executor import ActionExecutor
from identity.action_planner import ActionPlanner
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
        "llm",
        LLMExecutor(),
        "Local LLM.",
        enabled=True,
    )

    registry.register(
        "web",
        WebExecutor(),
        "Web search.",
        enabled=True,
    )

    runner = ToolRunner(
        registry,
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

    planner = ActionPlanner()

    task = type(
        "Task",
        (),
        {
            "title": (
                "Провести исследование: "
                "космические миссии NASA"
            )
        },
    )()

    action_plan = planner.plan(
        task
    )

    print("ACTION PLAN:")
    print(action_plan)

    action = ActionExecutor().create(
        action_type=action_plan.action_type,
        target=action_plan.target,
        parameters=action_plan.parameters,
        reason=action_plan.reason,
        dry_run=False,
    )

    result = runner.run(
        action
    )

    print()
    print("RESULT STATUS:")
    print(result["status"])

    print()
    print("RESULT:")
    print(result.get("result"))

    print()
    print("KNOWLEDGE OWNERS:")

    rows = memory.connection.execute("""
        SELECT
            owner,
            source_type,
            COUNT(*) AS count
        FROM knowledge
        GROUP BY owner, source_type
        ORDER BY owner, source_type
    """).fetchall()

    for row in rows:
        print(dict(row))

    memory.close()
