from identity.app_launcher import AppLauncher


def _launcher():
    class _SelfState:
        def __init__(self):
            self._data = {}

        def get(self, key, default=None):
            return self._data.get(key, default)

        def set(self, key, value):
            self._data[key] = value

    launcher = AppLauncher.__new__(AppLauncher)
    launcher._self_state = _SelfState()
    return launcher


def test_is_allowed_any_program():
    launcher = _launcher()
    assert launcher.is_allowed("notepad.exe")
    assert launcher.is_allowed("start chrome")
    assert launcher.is_allowed("calc")


def test_is_allowed_destructive_denied():
    launcher = _launcher()
    assert not launcher.is_allowed(
        "Format-Volume"
    )
    assert not launcher.is_allowed(
        "Remove-Item -Recurse C:\\ -Force"
    )


def test_launch_any_program_ok():
    launcher = _launcher()
    captured = {}
    launcher._policy = lambda: _SafePolicy()
    launcher._real_launch = (
        lambda command: captured.update(
            command=command
        )
        or {"ok": True}
    )
    result = launcher.launch("calc")
    assert result["status"] == "OK"
    assert captured["command"] == "calc"


def test_launch_destructive_denied():
    launcher = _launcher()
    result = launcher.launch("Format-Volume")
    assert result["status"] == "DENIED"


def test_launch_empty_denied():
    launcher = _launcher()
    result = launcher.launch("")
    assert result["status"] == "DENIED"


def test_launch_records_to_self_state():
    launcher = _launcher()
    launcher._policy = lambda: _SafePolicy()
    launcher._real_launch = (
        lambda command: {"ok": True}
    )
    launcher.launch("calc")
    history = launcher._self_state.get(
        "app_launch_history", []
    )
    assert len(history) == 1
    assert history[0]["command"] == "calc"


class _SafePolicy:
    def is_destructive(self, command):
        return False

    def destructive_reason(self, command):
        return None