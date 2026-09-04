from identity.command_policy import CommandPolicy
from identity.terminal_executor import TerminalExecutor


class TestCommandAudit:
    def setup_method(self):
        self.executor = TerminalExecutor()
        self.policy = CommandPolicy()

    def test_command_produces_result_dict(self):
        result = self.executor.execute(
            "echo test"
        )
        assert "status" in result
        assert "stdout" in result
        assert "command" in result

    def test_command_result_has_all_fields(self):
        result = self.executor.execute(
            "echo audit"
        )
        assert result["command"] == "echo audit"
        assert result["exit_code"] == 0
        assert isinstance(result["stdout"], str)

    def test_command_policy_blocks_dangerous(self):
        assert (
            self.policy.is_safe("Format-Volume")
            is False
        )
        assert (
            self.policy.deny_reason("Format-Volume")
            is not None
        )
