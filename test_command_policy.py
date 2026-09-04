from identity.command_policy import CommandPolicy


class TestCommandPolicy:
    def setup_method(self):
        self.policy = CommandPolicy()

    def test_safe_git_status(self):
        assert self.policy.is_safe("git status") is True

    def test_safe_get_process(self):
        assert self.policy.is_safe("Get-Process") is True

    def test_deny_format_volume(self):
        assert self.policy.is_safe(
            "Format-Volume -DriveLetter D"
        ) is False

    def test_allow_pip_install(self):
        # Решение Эдди 04.09: «всё можно что захочет»,
        # установка ПО не блокируется (не разрушительно).
        assert self.policy.is_safe(
            "pip install numpy"
        ) is True

    def test_empty_command(self):
        assert self.policy.is_safe("") is False
        assert self.policy.is_safe("  ") is False

    def test_deny_reason(self):
        reason = self.policy.deny_reason(
            "Format-Volume"
        )
        assert reason is not None
        assert (
            "Форматирование" in reason
            or "блок" in reason.lower()
        )

    def test_safe_reason_none(self):
        assert (
            self.policy.deny_reason("git status")
            is None
        )

    def test_deny_remove_recurse(self):
        assert self.policy.is_safe(
            "Remove-Item -Recurse C:\\temp"
        ) is False

    def test_safe_python_run(self):
        assert self.policy.is_safe(
            "python script.py"
        ) is True

    def test_allow_wget(self):
        # Сеть не разрушительна — разрешена (решение Эдди 04.09).
        assert self.policy.is_safe(
            "wget http://example.com"
        ) is True

    def test_deny_diskpart_clean(self):
        assert self.policy.is_safe(
            "diskpart clean"
        ) is False

    def test_deny_shutdown_force(self):
        assert self.policy.is_safe(
            "shutdown /s /f"
        ) is False
