import time
import threading
from concurrent.futures import ThreadPoolExecutor

def test_background_loop_survives_tick_error():
    from core.autonomous_runtime import AutonomousRuntime
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt._listeners = {}
    rt._loop_stop = threading.Event()
    rt._closed = False
    rt.state = "OK"
    rt.last_error = None
    rt._executor = ThreadPoolExecutor(max_workers=1)
    rt._background_future = None
    call_count = [0]
    def fake_tick():
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("boom")
        return {"status": "OK"}
    rt.tick_background = fake_tick
    t = threading.Thread(target=rt._background_loop)
    t.daemon = True
    t.start()
    time.sleep(3)
    rt._loop_stop.set()
    t.join(timeout=2)
    assert call_count[0] > 1, "loop died after first tick error"
    assert rt.last_error == "boom"
    assert rt.state == "ERROR"
    rt._executor.shutdown(wait=False)

def test_reset_error_changes_state():
    from core.autonomous_runtime import AutonomousRuntime
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt.state = "ERROR"
    rt.last_error = "test error"
    result = rt.reset_error()
    assert rt.state != "ERROR"
    assert rt.state == "IDLE"
    assert rt.last_error is None
    assert result["status"] == "RESET"
