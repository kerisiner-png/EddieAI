import argparse
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))

LOG = str(BASE_DIR / "logs" / "eddie_forever.log")

_stop = threading.Event()


def log(msg):
    stamp = datetime.now().strftime(
        "%H:%M:%S",
    )
    try:
        with open(
            LOG,
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                f"[{stamp}] {msg}\n"
            )
    except Exception:
        pass


def _signal_handler(signum, frame):
    log(f"signal {signum} received — stopping")
    _stop.set()


signal.signal(
    signal.SIGTERM, _signal_handler
)
signal.signal(
    signal.SIGINT, _signal_handler
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Постоянный рантайм EddieAI "
            "(без лимита времени)."
        )
    )
    parser.add_argument(
        "--no-chat",
        action="store_true",
        help="Не поднимать окно чата.",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Не поднимать голосовой контур.",
    )
    args = parser.parse_args()

    log("=== EDDIE FOREVER START ===")

    from core.agent import Agent
    from core.autonomy_runtime_factory import (
        AutonomyRuntimeFactory,
    )
    from core.fault_tolerance import (
        FaultTolerance,
    )
    from core.resource_watchdog import (
        ResourceWatchdog,
    )

    agent = Agent()

    runtime = AutonomyRuntimeFactory(
        agent,
        scheduler_max_ticks_per_window=(
            10**9
        ),
        scheduler_interval_seconds=15,
        enable_decision_core=True,
        resource_watchdog=ResourceWatchdog(
            enabled=True,
            low_ram_mb=256,
            critical_ram_mb=192,
        ),
    ).build()

    fault = FaultTolerance(runtime)

    runtime.start_background_loop()
    log("autonomy loop started")

    server = getattr(
        runtime, "eddie_server", None
    )

    if server is not None:
        server_thread = threading.Thread(
            target=server.serve_forever,
            name="EddieAI-Server",
            daemon=True,
        )
        server_thread.start()
        log(
            f"eddie server started on port "
            f"{server.port}"
        )

    chat = None

    if not args.no_chat:
        try:
            from communication.chat_app import (
                EddieChatApp,
            )

            chat = EddieChatApp(
                agent=agent,
                server=server,
            )
            chat.start_embedded()
            log("chat attached")
        except Exception as exc:
            chat = None
            log(
                f"chat unavailable: "
                f"{type(exc).__name__}: {exc}"
            )

    log("=== EDDIE FOREVER RUNNING ===")

    try:
        while not _stop.is_set():
            try:
                fault.update_heartbeat()
                fault.auto_reset_error()
            except Exception as exc:
                log(
                    f"watchdog error: "
                    f"{type(exc).__name__}: {exc}"
                )

            if chat is not None:
                try:
                    chat.update()
                except Exception:
                    pass

            _stop.wait(timeout=5.0)
    finally:
        log("stopping...")

        if chat is not None:
            try:
                chat.stop()
            except Exception:
                pass

        try:
            runtime.stop_background_loop()
        except Exception:
            pass

        try:
            agent.close()
        except Exception:
            pass

        log("=== EDDIE FOREVER END ===")


if __name__ == "__main__":
    main()