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


def _write_status_hb(runtime):
    import json

    data = {
        "timestamp": time.time(),
        "state": getattr(
            runtime, "state", "?"
        ),
    }
    try:
        life = getattr(
            runtime, "life_cycle", None
        )
        if life is not None:
            data["asleep"] = life.is_asleep()
    except Exception:
        pass
    try:
        orch = getattr(
            runtime, "orchestrator", None
        )
        decision = getattr(
            orch, "_last_decision", None
        )
        if decision:
            data["decision"] = str(decision)
    except Exception:
        pass
    try:
        cycles = getattr(
            runtime, "cycles_completed", None
        )
        if cycles is not None:
            data["cycles"] = cycles
        future = getattr(
            runtime,
            "_background_future",
            None,
        )
        data["future_done"] = (
            future.done()
            if future is not None
            else None
        )
        if future is not None and future.done():
            try:
                exc = future.exception(
                    timeout=0.1
                )
                data["future_exc"] = (
                    repr(exc)[:200]
                    if exc
                    else None
                )
            except Exception:
                pass
        err = getattr(
            runtime, "last_error", None
        )
        if err:
            data["last_error"] = str(err)[
                :200
            ]
    except Exception:
        pass
    try:
        last = getattr(
            runtime, "last_result", None
        )
        if isinstance(last, dict):
            inner = last.get(
                "runtime_result"
            ) or last
            status = inner.get("status")
            if status:
                data["last_status"] = status
    except Exception:
        pass
    try:
        with open(
            str(BASE_DIR / "data" / "status.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(data, f)
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
    parser.add_argument(
        "--no-senses",
        action="store_true",
        help="Не поднимать микрофон/вебку.",
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
    # Отключаем прогрев локальных моделей – будем пользоваться облачной gpt‑oss:120b‑cloud сразу
    agent.model_orchestrator.warm_up_models(enabled=False)


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

    senses = None

    if not args.no_senses:
        try:
            from identity.sense_listener import SenseListener

            senses = SenseListener(
                agent=agent,
                server=server,
                screen_perceiver=getattr(
                    runtime,
                    "_screen_perceiver",
                    None,
                ),
            )
            senses.start()
            agent.sense_listener = senses
            log("senses started (mic + webcam)")
        except Exception as exc:
            senses = None
            log(
                f"senses unavailable: "
                f"{type(exc).__name__}: {exc}"
            )

    pc_audio = None

    if not args.no_senses:
        try:
            from identity.pc_audio_listener import (
                PcAudioListener,
            )

            pc_audio = PcAudioListener(
                agent=agent
            )
            pc_audio.start()
            agent.pc_audio = pc_audio
            log("pc audio listener started")
        except Exception as exc:
            pc_audio = None
            log(
                f"pc audio unavailable: "
                f"{type(exc).__name__}: {exc}"
            )

    try:
        from identity.self_model import SelfModel

        agent.self_model = SelfModel(
            agent.self_state
        ).build(
            agent.capabilities,
            agent=agent,
        )
    except Exception as exc:
        log(
            f"self_model rebuild failed: "
            f"{type(exc).__name__}: {exc}"
        )

    try:
        while not _stop.is_set():
            try:
                fault.update_heartbeat()
                fault.auto_reset_error()
                _write_status_hb(runtime)
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

        if senses is not None:
            try:
                senses.stop()
            except Exception:
                pass

        if pc_audio is not None:
            try:
                pc_audio.stop()
            except Exception:
                pass

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