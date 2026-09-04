# Persistent Runtime: Windows Service + Fault Tolerance — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make EddieAI a persistent Windows service: 24/7 uptime, auto-restart on crash, graceful shutdown, fault tolerance.

**Architecture:** `FaultTolerance` watchdog + `EddieService` (pywin32 Windows Service) + fault tolerance in autonomous_runtime and cognition_worker.

**Tech Stack:** pywin32 (Windows Service), threading (watchdog), JSON (heartbeat)

**Spec:** Design approved in chat session 04.09.2026

## Global Constraints

- Python/PowerShell: `$env:PYTHONIOENCODING="utf-8"`
- UTF-8 without BOM, no comments, TDD
- No commits without Eddie's request
- RAM: ≤0.01 GB additional
- pywin32 for Windows Service
- Follow existing code style in autonomous_runtime.py, cognition_worker.py

---

### Task 1: FaultTolerance — watchdog + auto-restart + error recovery

**Files:**
- Create: `core/fault_tolerance.py`
- Create: `tests/test_fault_tolerance.py`

**Interfaces:**
- Produces: `FaultTolerance` class
  - `__init__(self, runtime, heartbeat_dir)` — saves runtime ref, creates heartbeat path
  - `update_heartbeat()` — writes timestamp + state to heartbeat.json
  - `check_health() -> dict` — returns `{"healthy": bool, "heartbeat_stale": bool, "state": str, "error": str|None}`
  - `auto_reset_error()` — if runtime.state == "ERROR" and enough time passed, calls runtime.resume()
  - `restart_cognition_worker()` — restarts cognition worker if dead

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fault_tolerance.py
import time, json, os, tempfile
from unittest.mock import MagicMock

def test_update_heartbeat_creates_file():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb_eddie.json")
    ft.update_heartbeat()
    assert os.path.exists(ft._heartbeat_path)
    with open(ft._heartbeat_path) as f:
        data = json.load(f)
    assert "timestamp" in data
    assert "state" in data
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
    result = ft.check_health()
    assert result.get("heartbeat_stale") == True
    os.remove(ft._heartbeat_path)

def test_check_health_fresh_heartbeat():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._heartbeat_path = os.path.join(tempfile.gettempdir(), "test_hb4_eddie.json")
    ft._stale_threshold = 60
    ft.update_heartbeat()
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._runtime._closed = False
    result = ft.check_health()
    assert result.get("heartbeat_stale") == False
    os.remove(ft._heartbeat_path)

def test_auto_reset_error_resumes_runtime():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "ERROR"
    ft._reset_delay = 0
    ft._last_error_time = time.time() - 10
    ft.auto_reset_error()
    ft._runtime.resume.assert_called_once()

def test_auto_reset_error_skips_if_not_enough_time():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "ERROR"
    ft._reset_delay = 60
    ft._last_error_time = time.time()
    ft.auto_reset_error()
    ft._runtime.resume.assert_not_called()

def test_auto_reset_error_skips_if_not_error():
    from core.fault_tolerance import FaultTolerance
    ft = FaultTolerance.__new__(FaultTolerance)
    ft._runtime = MagicMock()
    ft._runtime.state = "OK"
    ft._reset_delay = 0
    ft._last_error_time = time.time() - 10
    ft.auto_reset_error()
    ft._runtime.resume.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fault_tolerance.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# core/fault_tolerance.py
import json
import os
import time

class FaultTolerance:
    def __init__(self, runtime, heartbeat_dir=None):
        self._runtime = runtime
        self._stale_threshold = 120
        self._reset_delay = 60
        self._last_error_time = 0
        if heartbeat_dir is None:
            heartbeat_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self._heartbeat_path = os.path.join(heartbeat_dir, "heartbeat.json")

    def update_heartbeat(self):
        data = {"timestamp": time.time(), "state": self._runtime.state}
        os.makedirs(os.path.dirname(self._heartbeat_path), exist_ok=True)
        with open(self._heartbeat_path, "w") as f:
            json.dump(data, f)

    def check_health(self):
        result = {"healthy": True, "heartbeat_stale": False, "state": self._runtime.state, "error": None}
        try:
            if self._runtime._closed:
                result["healthy"] = False
                result["error"] = "runtime closed"
                return result
        except AttributeError:
            pass
        if os.path.exists(self._heartbeat_path):
            try:
                with open(self._heartbeat_path) as f:
                    data = json.load(f)
                age = time.time() - data.get("timestamp", 0)
                if age > self._stale_threshold:
                    result["heartbeat_stale"] = True
                    result["healthy"] = False
            except (json.JSONDecodeError, KeyError):
                result["heartbeat_stale"] = True
                result["healthy"] = False
        return result

    def auto_reset_error(self):
        if self._runtime.state != "ERROR":
            return
        elapsed = time.time() - self._last_error_time
        if elapsed >= self._reset_delay:
            try:
                self._runtime.resume()
            except Exception:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fault_tolerance.py -v`
Expected: 7/7 PASS

- [ ] **Step 5: Commit**

```bash
git add core/fault_tolerance.py tests/test_fault_tolerance.py
git commit -m "feat(persistent-runtime): add FaultTolerance watchdog"
```

---

### Task 2: AutonomousRuntime — try/except + heartbeat + auto-reset

**Files:**
- Modify: `core/autonomous_runtime.py` — add heartbeat updates to _background_loop, auto-reset from ERROR, resilient tick
- Create: `tests/test_runtime_fault_tolerance.py`

**Interfaces:**
- Consumes: FaultTolerance (from Task 1)
- Produces: `runtime.reset_error()` method, resilient `_background_loop()`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runtime_fault_tolerance.py
import time, threading

def test_background_loop_survives_tick_error():
    from core.autonomous_runtime import AutonomousRuntime
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt._loop_stop = threading.Event()
    rt._closed = False
    rt.state = "OK"
    rt._fault_tolerance = None
    rt._tick_lock = threading.Lock()
    call_count = [0]
    def fake_tick():
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("boom")
        return {"status": "OK"}
    rt.tick_background = fake_tick
    rt._executor = __import__("concurrent.futures").ThreadPoolExecutor(max_workers=1)
    t = threading.Thread(target=rt._background_loop)
    t.daemon = True
    t.start()
    time.sleep(3)
    rt._loop_stop.set()
    t.join(timeout=2)
    assert call_count[0] > 1

def test_reset_error_changes_state():
    from core.autonomous_runtime import AutonomousRuntime
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt.state = "ERROR"
    rt.last_error = "test error"
    rt.reset_error()
    assert rt.state != "ERROR"
```

- [ ] **Step 2-5:** Standard TDD cycle

---

### Task 3: CognitionWorker — auto-restart

**Files:**
- Modify: `core/cognition_worker.py` — add auto-restart on error
- Create: `tests/test_cognition_worker_restart.py`

**Interfaces:**
- Produces: `_should_restart()`, `_restart_worker()`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cognition_worker_restart.py
def test_should_restart_when_error_and_under_limit():
    from core.cognition_worker import CognitionWorker
    cw = CognitionWorker.__new__(CognitionWorker)
    cw.state = "ERROR"
    cw._restart_count = 0
    cw._max_restarts = 3
    assert cw._should_restart() == True

def test_should_not_restart_when_at_limit():
    from core.cognition_worker import CognitionWorker
    cw = CognitionWorker.__new__(CognitionWorker)
    cw.state = "ERROR"
    cw._restart_count = 3
    cw._max_restarts = 3
    assert cw._should_restart() == False

def test_should_not_restart_when_not_error():
    from core.cognition_worker import CognitionWorker
    cw = CognitionWorker.__new__(CognitionWorker)
    cw.state = "OK"
    cw._restart_count = 0
    cw._max_restarts = 3
    assert cw._should_restart() == False

def test_restart_increments_count():
    from core.cognition_worker import CognitionWorker
    cw = CognitionWorker.__new__(CognitionWorker)
    cw._restart_count = 0
    cw._restart_worker_fn = lambda: None
    cw._restart_worker()
    assert cw._restart_count == 1
```

- [ ] **Step 2-5:** Standard TDD cycle

---

### Task 4: EddieService — Windows Service

**Files:**
- Create: `core/eddie_service.py`
- Create: `tests/test_eddie_service.py`
- Create: `eddie_service_install.bat`

**Interfaces:**
- Consumes: Agent, AutonomyRuntimeFactory, FaultTolerance
- Produces: Windows Service (start/stop/status)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_eddie_service.py
def test_service_class_has_required_methods():
    from core.eddie_service import EddieService
    svc = EddieService.__new__(EddieService)
    assert hasattr(svc, 'SvcDoRun')
    assert hasattr(svc, 'SvcStop')
    assert hasattr(svc, 'SvcInit')

def test_install_script_exists():
    import os
    assert os.path.exists("eddie_service_install.bat")
```

- [ ] **Step 2-5:** Standard TDD cycle

---

### Task 5: Финальная регресс + документация

- [ ] Run all new tests
- [ ] Run full regression
- [ ] Byte-check all files
- [ ] Update CHANGELOG, TODO, PROJECT_STATE
