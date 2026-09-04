from identity.action_executor import ActionExecutor
from identity.terminal_executor import TerminalExecutor
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner


def _make_runner():
    registry = ToolRegistry()
    registry.register(
        name="powershell",
        executor=TerminalExecutor(),
        description="test",
        enabled=True,
    )
    runner = ToolRunner(registry)
    runner.policy.allow_powershell = True
    return runner


def _make_action(command, target="run-command"):
    return ActionExecutor().create(
        action_type="RUN_COMMAND",
        target=target,
        parameters={
            "command": command,
        },
        reason="Тест терминала.",
        dry_run=False,
    )


def test_run_command_echo():
    runner = _make_runner()
    result = runner.run(
        _make_action(
            "echo hello"
        )
    )
    assert result["status"] == "OK"
    assert "hello" in result["result"]["output"]


def test_run_command_deny():
    runner = _make_runner()
    result = runner.run(
        _make_action(
            "Format-Volume -DriveLetter D"
        )
    )
    assert result["status"] == "REJECTED"
    assert result["stage"] == "policy"


def test_run_command_timeout():
    runner = _make_runner()
    action = ActionExecutor().create(
        action_type="RUN_COMMAND",
        target="sleep",
        parameters={
            "command": (
                "python -c \"import time; "
                "time.sleep(60)\""
            ),
        },
        reason="Тест таймаута.",
        dry_run=False,
    )
    result = runner.run(action)
    assert result["status"] in (
        "TIMEOUT",
        "ERROR",
        "DENIED",
    )


def test_run_command_exit_code():
    runner = _make_runner()
    result = runner.run(
        _make_action(
            "python -c \"exit(42)\""
        )
    )
    assert result["result"]["exit_code"] == 42


def test_run_command_empty():
    runner = _make_runner()
    result = runner.run(
        _make_action("")
    )
    assert result["status"] in (
        "ERROR",
        "REJECTED",
    )
