import ctypes
import time
from datetime import datetime, timezone


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


def _meminfo():
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        )
        if not ok:
            return None
        return {
            "load": int(status.dwMemoryLoad),
            "total_gb": round(
                status.ullTotalPhys / (1024 ** 3), 1
            ),
            "avail_mb": int(
                status.ullAvailPhys // (1024 * 1024)
            ),
        }
    except Exception:
        return None


def _disk_c():
    try:
        free = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        total_free = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p("C:\\"),
            ctypes.byref(free),
            ctypes.byref(total),
            ctypes.byref(total_free),
        )
        if not ok:
            return None
        return {
            "status": "OK",
            "free_gb": round(
                free.value / (1024 ** 3), 1
            ),
            "total_gb": round(
                total.value / (1024 ** 3), 1
            ),
        }
    except Exception:
        return None


class WorldProbe:
    def __init__(self, probe_interval_seconds=900):
        self.probe_interval_seconds = max(
            0, int(probe_interval_seconds)
        )
        self._last_probe = 0.0

    def allow(self):
        now = time.monotonic()
        return now - self._last_probe >= self.probe_interval_seconds

    def probe(self, force=False):
        if not force and not self.allow():
            return {"status": "THROTTLED"}
        self._last_probe = time.monotonic()
        mem = _meminfo()
        disk = _disk_c()
        return {
            "status": "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ram": mem,
            "disk": disk,
        }

    def snapshot_text(self, snapshot):
        if snapshot.get("status") != "OK":
            return "ПК сейчас: нет данных."
        mem = snapshot.get("ram") or {}
        disk = snapshot.get("disk") or {}
        parts = []
        if mem.get("avail_mb") is not None:
            parts.append(f"свободная RAM ~{mem['avail_mb']} МБ")
        if mem.get("load") is not None:
            parts.append(f"нагрузка {mem['load']}%")
        if disk.get("status") == "OK":
            parts.append("диск C: доступен")
        return (
            "Мир сейчас: " + ", ".join(parts) + "."
            if parts
            else "Мир сейчас: данных недостаточно."
        )
