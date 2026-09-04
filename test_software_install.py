from identity.software_install import SoftwareInstaller


def _installer():
    inst = SoftwareInstaller.__new__(SoftwareInstaller)
    inst._self_state = None
    inst._history = []
    return inst


def test_install_pip_ok():
    inst = _installer()
    executed = []
    inst._do_install = (
        lambda command: executed.append(command)
        or {"status": "OK", "stdout": "done"}
    )
    result = inst.install(
        package="requests", manager="pip"
    )
    assert result["status"] == "OK"
    assert ("pip install requests") in executed[0]


def test_install_records_history():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    inst.install("requests", "pip")
    assert len(inst._history) == 1
    assert inst._history[0]["package"] == "requests"


def test_install_format_volume_denied():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    result = inst.install(
        package="C:", manager="Format-Volume"
    )
    assert result["status"] == "DENIED"


def test_install_dangerous_command_denied():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    result = inst.install(
        package="windows", manager="Remove-Item -Recurse"
    )
    assert result["status"] == "DENIED"


def test_install_winget_ok():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    result = inst.install(
        package="firefox", manager="winget"
    )
    assert result["status"] == "OK"


def test_install_npm_ok():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    result = inst.install(
        package="lodash", manager="npm"
    )
    assert result["status"] == "OK"


def test_install_manager_injection_blocked():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "OK"}
    )
    result = inst.install(
        package="requests",
        manager="pip && Format-Volume",
    )
    assert result["status"] == "DENIED"


def test_install_failure_reported():
    inst = _installer()
    inst._do_install = (
        lambda command: {"status": "ERROR", "stderr": "no"}
    )
    result = inst.install("requests", "pip")
    assert result["status"] == "ERROR"