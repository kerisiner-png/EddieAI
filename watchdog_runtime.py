import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATUS = BASE / "data" / "status.json"
LOG = BASE / "logs" / "watchdog_runtime.log"
STALL_SEC = 240
RAM_FLOOR_MB = 700
OLLAMA_URL = (
    "http://127.0.0.1:11434/api/version"
)


def log(msg):
    stamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    try:
        with open(
            LOG, "a", encoding="utf-8"
        ) as f:
            f.write(f"[{stamp}] {msg}\n")
    except Exception:
        pass


def ollama_alive():
    try:
        with urllib.request.urlopen(
            OLLAMA_URL, timeout=5
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama():
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Start-Process -FilePath ollama "
                "-ArgumentList 'serve' "
                "-WindowStyle Hidden",
            ]
        )
        log("ollama serve start issued")
    except Exception as exc:
        log(f"ollama start failed: {exc}")


def free_ram_mb():
    try:
        out = (
            subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "[math]::Round((Get-CimInstance "
                    "Win32_OperatingSystem)"
                    ".FreePhysicalMemory/1KB)",
                ],
                timeout=30,
            )
            .decode()
            .strip()
        )
        return int(float(out))
    except Exception:
        return None


def kill(name):
    try:
        subprocess.run(
            ["taskkill", "/IM", name, "/F"],
            capture_output=True,
            timeout=30,
        )
        log(f"killed {name}")
    except Exception as exc:
        log(f"kill {name} failed: {exc}")


def runtime_pids():
    try:
        out = (
            subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance "
                    "Win32_Process -Filter "
                    "\"Name='python.exe'\" | "
                    "Where-Object { "
                    "$_.CommandLine -like "
                    "'*run_forever.py*' } | "
                    "ForEach-Object { "
                    "$_.ProcessId }",
                ],
                timeout=30,
            )
            .decode(errors="replace")
        )
        pids = []
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(line)
        return pids
    except Exception:
        return []


def restart_runtime():
    for pid in runtime_pids():
        try:
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True,
                timeout=30,
            )
            log(f"killed stale runtime pid {pid}")
        except Exception:
            pass
    time.sleep(5)
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Start-Process -FilePath python "
            "-ArgumentList 'run_forever.py' "
            "-WorkingDirectory 'C:\\EddieAI' "
            "-WindowStyle Hidden",
        ]
    )
    log("runtime restart issued")


def main():
    log("watchdog started")
    while True:
        try:
            ram = free_ram_mb()
            if (
                ram is not None
                and ram < RAM_FLOOR_MB
            ):
                out = (
                    subprocess.run(
                        [
                            "tasklist",
                            "/FI",
                            "IMAGENAME eq "
                            "llama-server.exe",
                        ],
                        capture_output=True,
                        timeout=30,
                    ).stdout.decode(
                        errors="replace"
                    )
                )
                if "llama-server" in out:
                    kill("llama-server.exe")
                    log(
                        "RAM guard: llama-server "
                        f"stopped (free={ram}MB)"
                    )

            if not ollama_alive():
                start_ollama()

            stale = True
            if STATUS.exists():
                age = (
                    time.time()
                    - STATUS.stat().st_mtime
                )
                stale = age > STALL_SEC

            if stale and not runtime_pids():
                log(
                    "runtime down (status stale "
                    "or absent) — restarting"
                )
                restart_runtime()
            elif stale:
                log(
                    "status stale but runtime "
                    "process alive — waiting "
                    "next cycle"
                )
        except Exception as exc:
            log(
                f"watchdog error: "
                f"{type(exc).__name__}: {exc}"
            )
        time.sleep(60)


if __name__ == "__main__":
    main()
