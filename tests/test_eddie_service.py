import os

def test_service_class_has_required_methods():
    from core.eddie_service import EddieService
    svc = EddieService.__new__(EddieService)
    assert hasattr(svc, "SvcInit")
    assert hasattr(svc, "SvcDoRun")
    assert hasattr(svc, "SvcStop")

def test_service_metadata():
    from core.eddie_service import EddieService
    assert EddieService._svc_name_ == "EddieAI"
    assert EddieService._svc_display_name_ == (
        "EddieAI Persistent Runtime"
    )

def test_module_guards_pywin32():
    import core.eddie_service as m
    assert m.PYWIN32 in (True, False)
    assert callable(getattr(m, "EddieService", None))

def test_install_script_exists():
    assert os.path.exists("eddie_service_install.bat")

def test_watchdog_runs_and_updates_heartbeat(tmp_path):
    import time
    from unittest.mock import MagicMock
    from core.eddie_service import EddieService
    import core.eddie_service as m
    svc = EddieService.__new__(EddieService)
    runtime = MagicMock()
    from core.fault_tolerance import FaultTolerance
    svc.fault_tolerance = FaultTolerance(
        runtime, heartbeat_dir=str(tmp_path)
    )
    svc._fault_stop = m.threading.Event()
    svc.agent = MagicMock()
    t = m.threading.Thread(target=svc._watchdog)
    t.daemon = True
    t.start()
    time.sleep(0.3)
    svc._fault_stop.set()
    t.join(timeout=2)
    hb = tmp_path / "heartbeat.json"
    assert hb.exists(), "watchdog did not write heartbeat"
