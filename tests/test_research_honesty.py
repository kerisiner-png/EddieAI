from pathlib import Path
from tempfile import TemporaryDirectory

from identity.action_executor import ActionExecutor
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner
from memory.database import Memory
from memory.external_knowledge import (
    ExternalKnowledgeRecorder,
)
from memory.source_evaluator import SourceEvaluator
from memory.self_interpretation import (
    SelfInterpretation,
)


class _StubResearchExecutor:
    def execute(self, action):
        return {"status": "OK"}


class _StubWebExecutor:
    def __init__(self, results):
        self._results = results

    def search(self, query, limit=5):
        return {
            "status": "OK",
            "results": self._results[:limit],
        }

    def read_page(self, url):
        return {
            "status": "OK",
            "url": url,
            "text": (
                "NASA space missions research "
                "content long enough for the "
                "runner to accept the page and "
                "pass it into interpretation."
            ),
        }


def _runner(results, threshold=0.45):
    temp = TemporaryDirectory()
    memory = Memory(
        Path(temp.name) / "memory.db"
    )
    registry = ToolRegistry()
    registry.register(
        name="web",
        executor=_StubWebExecutor(results),
        description="Web search stub.",
        enabled=True,
    )
    registry.register(
        name="research",
        executor=_StubResearchExecutor(),
        description="Research stub.",
        enabled=True,
    )
    runner = ToolRunner(
        registry,
        filesystem_root=temp.name,
        external_recorder=(
            ExternalKnowledgeRecorder(memory)
        ),
        self_interpreter=SelfInterpretation(
            memory
        ),
        source_evaluator=SourceEvaluator(
            acceptance_threshold=threshold
        ),
    )
    return temp, memory, runner


def _research_action(query):
    return ActionExecutor().create(
        action_type="RESEARCH",
        target=f"исследовать: {query}",
        parameters={"query": query, "limit": 5},
        reason="тест честного исследования",
        dry_run=False,
    )


def test_no_accepted_sources_is_honest_ok():
    results = [
        {
            "title": "случайный блог без сути",
            "url": "https://random-blog123.example.com/post",
        },
    ]
    temp, memory, runner = _runner(
        results, threshold=0.99
    )

    result = runner.run(
        _research_action("редкая тема без источников")
    )

    memory.close()
    temp.cleanup()

    assert result["status"] == "OK"

    inner = result.get("result", {})

    assert (
        inner.get("no_accepted_sources")
        is True
    )
    assert inner["external_records"] == []
    assert inner["interpretation"] is None
    assert "не нашлось" in (
        inner.get("honest_note", "")
    )


