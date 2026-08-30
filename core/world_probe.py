import ctypes
import time
from datetime import datetime, timezone


class _FileTime(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", ctypes.c_ulong),
        ("dwHighDateTime", ctypes.c_ulong),
    ]


class _ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


_cpu_state = {"idle": None, "total": None}


def _cpu_percent():
    try:
        idle = _FileTime()
        kernel = _FileTime()
        user = _FileTime()
        ok = ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            return None

        def _val(ft):
            return (
                ft.dwHighDateTime << 32
            ) | ft.dwLowDateTime

        idle_now = _val(idle)
        total_now = (
            _val(kernel) + _val(user)
        )

        prev_idle = _cpu_state["idle"]
        prev_total = _cpu_state["total"]

        _cpu_state["idle"] = idle_now
        _cpu_state["total"] = total_now

        if (
            prev_idle is None
            or prev_total is None
        ):
            return 0.0

        idle_delta = idle_now - prev_idle
        total_delta = total_now - prev_total

        if total_delta <= 0:
            return 0.0

        busy = total_delta - idle_delta

        return round(
            max(0.0, min(100.0, busy / total_delta * 100.0)),
            1,
        )
    except Exception:
        return None


def _top_processes(limit=5):
    try:
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(
            0x00000002,
            0,
        )
        if snapshot == -1:
            return []

        processes = []

        try:
            entry = _ProcessEntry32W()
            entry.dwSize = ctypes.sizeof(
                _ProcessEntry32W
            )

            ok = ctypes.windll.kernel32.Process32FirstW(
                snapshot,
                ctypes.byref(entry),
            )

            while ok:
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(
                        0x0400,
                        False,
                        entry.th32ProcessID,
                    )
                    memory_mb = None
                    if handle:
                        try:
                            from ctypes import wintypes

                            class _ProcessMemoryCounters(
                                ctypes.Structure,
                            ):
                                _fields_ = [
                                    (
                                        "cb",
                                        wintypes.DWORD,
                                    ),
                                    (
                                        "PageFaultCount",
                                        wintypes.DWORD,
                                    ),
                                    (
                                        "PeakWorkingSetSize",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "WorkingSetSize",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "QuotaPeakPagedPoolUsage",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "QuotaPagedPoolUsage",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "QuotaPeakNonPagedPoolUsage",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "QuotaNonPagedPoolUsage",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "PagefileUsage",
                                        ctypes.c_size_t,
                                    ),
                                    (
                                        "PeakPagefileUsage",
                                        ctypes.c_size_t,
                                    ),
                                ]

                            counters = (
                                _ProcessMemoryCounters()
                            )
                            counters.cb = ctypes.sizeof(
                                _ProcessMemoryCounters
                            )
                            got = (
                                ctypes.windll
                                .psapi
                                .GetProcessMemoryInfo(
                                    handle,
                                    ctypes.byref(
                                        counters
                                    ),
                                    ctypes.sizeof(
                                        counters
                                    ),
                                )
                            )
                            if got:
                                memory_mb = round(
                                    counters.WorkingSetSize
                                    / (1024 * 1024),
                                    1,
                                )
                        finally:
                            ctypes.windll.kernel32.CloseHandle(
                                handle
                            )

                    processes.append({
                        "name": entry.szExeFile,
                        "pid": entry.th32ProcessID,
                        "memory_mb": memory_mb,
                    })
                except Exception:
                    pass

                ok = ctypes.windll.kernel32.Process32NextW(
                    snapshot,
                    ctypes.byref(entry),
                )
        finally:
            ctypes.windll.kernel32.CloseHandle(
                snapshot
            )

        scored = [
            proc
            for proc in processes
            if proc["memory_mb"] is not None
        ]

        scored.sort(
            key=lambda item: item["memory_mb"],
            reverse=True,
        )

        return scored[:limit]
    except Exception:
        return []


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
        cpu = _cpu_percent()
        top_procs = _top_processes(limit=5)
        return {
            "status": "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ram": mem,
            "disk": disk,
            "cpu": cpu,
            "top_processes": top_procs,
        }

    def snapshot_text(self, snapshot):
        if snapshot.get("status") != "OK":
            return "ПК сейчас: нет данных."
        mem = snapshot.get("ram") or {}
        disk = snapshot.get("disk") or {}
        cpu = snapshot.get("cpu")
        top_procs = snapshot.get("top_processes") or []
        parts = []
        if mem.get("avail_mb") is not None:
            parts.append(f"свободная RAM ~{mem['avail_mb']} МБ")
        if mem.get("load") is not None:
            parts.append(f"нагрузка {mem['load']}%")
        if cpu is not None:
            parts.append(f"CPU ~{cpu}%")
        if disk.get("status") == "OK":
            parts.append("диск C: доступен")
        if top_procs:
            names = ", ".join(
                proc["name"]
                for proc in top_procs
            )
            parts.append(f"активные процессы: {names}")
        return (
            "Мир сейчас: " + ", ".join(parts) + "."
            if parts
            else "Мир сейчас: данных недостаточно."
        )
