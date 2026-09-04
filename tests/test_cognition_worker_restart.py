import time

def test_worker_recovers_after_transient_error():
    from core.cognition_worker import CognitionWorker
    calls = [0]
    class FakeProcessor:
        def analyse_next(self):
            calls[0] += 1
            if calls[0] <= 2:
                raise RuntimeError("transient")
            return {"status": "EMPTY"}
    cw = CognitionWorker(FakeProcessor(), poll_interval=0.1)
    cw.start()
    time.sleep(1.5)
    cw.stop()
    assert calls[0] > 2, "worker did not retry after transient error"
    assert cw.restart_count == 0, "restart_count not reset on success"
    assert cw.state != "ERROR"

def test_worker_stops_after_max_restarts():
    from core.cognition_worker import CognitionWorker
    class FailingProcessor:
        def analyse_next(self):
            raise RuntimeError("persistent")
    cw = CognitionWorker(FailingProcessor(), poll_interval=0.1)
    cw.max_restarts = 3
    cw.start()
    deadline = time.time() + 5.0
    while time.time() < deadline and cw.restart_count < 3:
        time.sleep(0.1)
    cw.stop()
    assert cw.restart_count >= 3, "worker did not exhaust restarts"
    assert cw.last_error == "persistent"

def test_restart_count_resets_on_success_then_fails_again():
    from core.cognition_worker import CognitionWorker
    calls = [0]
    class FlakyProcessor:
        def analyse_next(self):
            calls[0] += 1
            if calls[0] == 1:
                raise RuntimeError("fail1")
            if calls[0] == 2:
                return {"status": "EMPTY"}
            raise RuntimeError("fail2")
    cw = CognitionWorker(FlakyProcessor(), poll_interval=0.1)
    cw.max_restarts = 2
    cw.start()
    time.sleep(1.0)
    cw.stop()
    assert calls[0] >= 3, "should have logged at least one failure after recovery"
