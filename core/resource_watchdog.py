import ctypes
import time


LOW_RAM_MB = 1024
CRITICAL_RAM_MB = 700
PROBE_INTERVAL_SECONDS = 30
HOLD_OFF_SECONDS = 60


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _available_memory_mb():
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        )
        if not ok:
            return None
        return int(
            status.ullAvailPhys // (1024 * 1024)
        )
    except Exception:
        return None


class ResourceWatchdog:
    def __init__(
        self,
        enabled=False,
        low_ram_mb=LOW_RAM_MB,
        critical_ram_mb=CRITICAL_RAM_MB,
        probe_interval_seconds=PROBE_INTERVAL_SECONDS,
        hold_off_seconds=HOLD_OFF_SECONDS,
    ):
        self.enabled = enabled
        self.low_ram_mb = low_ram_mb
        self.critical_ram_mb = critical_ram_mb
        self.probe_interval_seconds = probe_interval_seconds
        self.hold_off_seconds = hold_off_seconds

        self._last_probe = 0.0
        self._last_available_mb = None
        self._last_level = "ok"
        self._throttle_until = 0.0

    def level(self, available_mb=None):
        if available_mb is None:
            available_mb = self._last_available_mb
        if available_mb is None:
            return "ok"
        if available_mb < self.critical_ram_mb:
            return "critical"
        if available_mb < self.low_ram_mb:
            return "low"
        return "ok"

    def check(self):
        now = time.monotonic()
        if not self.enabled:
            return {
                "available_mb": self._last_available_mb,
                "level": "ok",
                "enabled": False,
            }

        if (
            self._last_available_mb is None
            or now - self._last_probe
            >= self.probe_interval_seconds
        ):
            self._last_available_mb = (
                _available_memory_mb()
            )
            self._last_probe = now

        level = self.level()
        self._last_level = level

        return {
            "available_mb": self._last_available_mb,
            "level": level,
            "enabled": True,
        }

    def should_throttle(self):
        if not self.enabled:
            return False

        result = self.check()
        now = time.monotonic()

        if result["level"] == "critical":
            self._throttle_until = (
                now + self.hold_off_seconds
            )
            return True

        if result["level"] == "low":
            if now < self._throttle_until:
                return True
            self._throttle_until = (
                now + self.hold_off_seconds
            )
            return True

        return False
