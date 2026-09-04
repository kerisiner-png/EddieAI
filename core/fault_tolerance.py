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
                self._runtime.reset_error()
            except Exception:
                pass
