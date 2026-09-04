import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from identity.terminal_executor import TerminalExecutor


class TestTerminalExecutor:
    def setup_method(self):
        self.executor = TerminalExecutor()

    def test_execute_echo(self):
        result = self.executor.execute("echo hello")
        assert result["status"] == "OK"
        assert "hello" in result["stdout"]
        assert result["exit_code"] == 0

    def test_execute_timeout(self):
        result = self.executor.execute(
            "python -c \"import time; time.sleep(60)\"",
            timeout=2,
        )
        assert result["status"] == "TIMEOUT"

    def test_execute_stderr(self):
        result = self.executor.execute(
            "python -c \"import sys; sys.stderr.write('err')\""
        )
        assert result["status"] == "OK"
        assert "err" in result["stderr"]

    def test_execute_empty_command(self):
        result = self.executor.execute("")
        assert result["status"] == "ERROR"
        assert result["exit_code"] is None

    def test_execute_whitespace_command(self):
        result = self.executor.execute("   ")
        assert result["status"] == "ERROR"
        assert result["exit_code"] is None

    def test_execute_exit_code(self):
        result = self.executor.execute(
            "python -c \"exit(42)\""
        )
        assert result["status"] == "OK"
        assert result["exit_code"] == 42

    def test_execute_output_truncation(self):
        cmd = (
            "python -c \"print('x' * 100000)\""
        )
        executor = TerminalExecutor(
            max_output_bytes=1000
        )
        result = executor.execute(cmd)
        assert result["status"] == "OK"
        assert len(result["stdout"]) <= 1000

    def test_execute_cwd(self):
        temp_dir = os.environ.get(
            "TEMP", "C:\\Windows\\Temp"
        )
        result = self.executor.execute(
            "echo %CD%",
            cwd=temp_dir,
        )
        assert result["status"] == "OK"

    def test_execute_invalid_command(self):
        result = self.executor.execute(
            "nonexistent_command_xyz"
        )
        assert result["status"] == "OK"
        assert result["exit_code"] != 0

    def test_execute_command_preserved(self):
        cmd = "echo test123"
        result = self.executor.execute(cmd)
        assert result["command"] == cmd

    def test_execute_default_timeout(self):
        assert self.executor._timeout == 30

    def test_execute_custom_timeout(self):
        executor = TerminalExecutor(timeout=5)
        assert executor._timeout == 5

    def test_execute_stderr_truncation(self):
        cmd = (
            "python -c \""
            "import sys; "
            "[sys.stderr.write('e' * 100) "
            "for _ in range(1000)]\""
        )
        executor = TerminalExecutor(
            max_output_bytes=500
        )
        result = executor.execute(cmd)
        assert result["status"] == "OK"
        assert len(result["stderr"]) <= 500


if __name__ == "__main__":
    import pytest

    sys.exit(
        pytest.main(
            [__file__, "-v"]
        )
    )
