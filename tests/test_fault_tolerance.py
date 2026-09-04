import time, json, os, tempfile
from unittest.mock import MagicMock

def test_update_heartbeat_creates_file():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb_eddie.json")
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    try:
        ft.update_heartbeat()
        assert os.path.exists(ft._heartbeat_path)
        with open(ft._heartbeat_path) as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "state" in data
    finally:
        os.remove(ft._heartbeat_path)

def test_check_health_returns_dict():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb2_eddie.json")
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._runtime._closed = False
    result = ft.check_health()
    assert isinstance(result, dict)
    assert "healthy" in result

def test_check_health_detects_stale_heartbeat():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb3_eddie.json")
    ft._stale_threshold = 60
    with open(ft._heartbeat_path, "w") as f:
        json.dump({"timestamp": time.time() - 300, "state": "OK"}, f)
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._runtime._closed = False
    try:
        result = ft.check_health()
        assert result.get("heartbeat_stale") == True
    finally:
        os.remove(ft._heartbeat_path)

def test_check_health_fresh_heartbeat():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb4_eddie.json")
    ft._stale_threshold = 60
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._runtime._closed = False
    try:
        ft.update_heartbeat()
        result = ft.check_health()
        assert result.get("heartbeat_stale") == False
    finally:
        os.remove(ft._heartbeat_path)

def test_auto_reset_error_resumes_runtime():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "ERROR"
    ft._reset_delay = 0
    ft._last_error_time = time.time() - 10
    ft.auto_reset_error()
    ft._runtime.reset_error.assert_called_once()

def test_auto_reset_error_skips_if_not_enough_time():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "ERROR"
    ft._reset_delay = 60
    ft._last_error_time = time.time()
    ft.auto_reset_error()
    ft._runtime.reset_error.assert_not_called()

def test_auto_reset_error_skips_if_not_error():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._reset_delay = 0
    ft._last_error_time = time.time() - 10
    ft.auto_reset_error()
    ft._runtime.reset_error.assert_not_called()
