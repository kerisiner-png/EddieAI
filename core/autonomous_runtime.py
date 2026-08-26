from dataclasses import dataclass
from datetime import datetime, timezone
from concurrent.futures import Future, ThreadPoolExecutor
import threading


@dataclass
class RuntimeSnapshot:
    state: str
    started_at: str
    last_error: str | None
    last_result: dict | None
    cycles_completed: int


class AutonomousRuntime:
    def __init__(
        self,
        scheduler,
        memory=None,
        orchestrator=None,
    ):
        self.scheduler = scheduler
        self.memory = memory
        self.orchestrator = orchestrator

        self.state = "IDLE"

        self.started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.last_error = None
        self.last_result = None
        self.cycles_completed = 0

        self.evidence_consolidator = None

        # Один автономный тик за раз.
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="EddieAI-Autonomy",
        )

        self._background_future: Future | None = None

        # Отдельный daemon-loop следит за scheduler.
        self._loop_thread = None
        self._loop_stop = threading.Event()

        self._closed = False

    def snapshot(self):
        return RuntimeSnapshot(
            state=self.state,
            started_at=self.started_at,
            last_error=self.last_error,
            last_result=self.last_result,
            cycles_completed=self.cycles_completed,
        )

    def tick(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "state": "CLOSED",
                "reason": (
                    "Autonomous runtime уже закрыт."
                ),
            }

        if self.state in {
            "THINKING",
            "ACTING",
            "REFLECTING",
        }:
            return {
                "status": "BUSY",
                "state": self.state,
                "reason": (
                    "Автономный цикл уже выполняется."
                ),
            }

        if self.state == "PAUSED":
            return {
                "status": "PAUSED",
                "state": self.state,
                "reason": (
                    "Autonomous runtime находится "
                    "на паузе."
                ),
            }

        self.last_error = None

        try:
            self.state = "ACTING"

            result = self.scheduler.tick()

            self.last_result = result
            self.cycles_completed += 1

            consolidation = None

            if (
                self.evidence_consolidator
                is not None
            ):
                self.state = "REFLECTING"

                consolidation = (
                    self.evidence_consolidator
                    .consolidate()
                )

            if self.decision_core is not None:
                try:
                    self.decision_core.learn_from_memory()
                except Exception:
                    pass

                try:
                    self.decision_core.consolidate_habits()
                except Exception:
                    pass

            if self.speech_habits is not None:
                try:
                    self.speech_habits.learn_from_memory(
                        limit=30
                    )
                except Exception:
                    pass

            self.state = "IDLE"

            wrapped_result = {
                "runtime_result": result,
                "consolidation": consolidation,
            }

            self.last_result = wrapped_result

            return {
                "status": "OK",
                "state": self.state,
                "result": wrapped_result,
            }

        except Exception as exc:
            self.last_error = str(exc)
            self.state = "ERROR"

            return {
                "status": "ERROR",
                "state": self.state,
                "error": str(exc),
            }

    def notify_inbox(self):
        """
        Push-уведомление: Eddie пишет сообщение.
        Немедленно обрабатывает почту (EddieAI решает,
        прочитать ли), не дожидаясь интервала планировщика.
        """
        if self._closed:
            return {"status": "CLOSED"}

        if self.state == "PAUSED":
            return {"status": "PAUSED"}

        if self.orchestrator is None:
            return {"status": "NO_ORCHESTRATOR"}

        try:
            self._executor.submit(
                self._inbox_tick
            )
        except RuntimeError:
            return {"status": "SHUTDOWN"}

        return {"status": "QUEUED"}

    def _inbox_tick(self):
        try:
            return (
                self.orchestrator._handle_inbox()
            )
        except Exception:
            return None

    def tick_background(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "state": "CLOSED",
            }

        if self.state == "PAUSED":
            return {
                "status": "PAUSED",
                "state": self.state,
            }

        if (
            self._background_future is not None
            and not self._background_future.done()
        ):
            return {
                "status": "ALREADY_RUNNING",
                "state": self.state,
                "future": self._background_future,
            }

        self._background_future = (
            self._executor.submit(
                self.tick
            )
        )

        return {
            "status": "STARTED",
            "state": self.state,
            "future": self._background_future,
        }

    def background_status(self):
        future = self._background_future

        if future is None:
            return {
                "running": False,
                "done": False,
                "result": None,
            }

        if not future.done():
            return {
                "running": True,
                "done": False,
                "result": None,
            }

        try:
            result = future.result()
        except Exception as exc:
            result = {
                "status": "ERROR",
                "error": str(exc),
            }

        return {
            "running": False,
            "done": True,
            "result": result,
        }

    def start_background_loop(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "reason": (
                    "Autonomous runtime уже закрыт."
                ),
            }

        if (
            self._loop_thread is not None
            and self._loop_thread.is_alive()
        ):
            return {
                "status": "ALREADY_RUNNING",
            }

        self._loop_stop.clear()

        self._loop_thread = threading.Thread(
            target=self._background_loop,
            name="EddieAI-AutonomyLoop",
            daemon=True,
        )

        self._loop_thread.start()

        return {
            "status": "STARTED",
        }

    def stop_background_loop(self):
        self._loop_stop.set()

        thread = self._loop_thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=2.0
            )

        self._loop_thread = None

        return {
            "status": "STOPPED",
        }

    def _background_loop(self):
        while not self._loop_stop.is_set():
            if self._closed:
                break

            if self.state != "PAUSED":
                self.tick_background()

            # Короткое ожидание нужно только для
            # отзывчивого shutdown. Сам scheduler
            # всё равно контролирует реальный интервал.
            self._loop_stop.wait(
                timeout=1.0
            )

    def pause(self):
        if self.state in {
            "THINKING",
            "ACTING",
            "REFLECTING",
        }:
            return {
                "status": "BUSY",
                "reason": (
                    "Нельзя поставить runtime "
                    "на паузу во время выполнения."
                ),
            }

        self.state = "PAUSED"

        return {
            "status": "PAUSED",
        }

    def resume(self):
        if self.state != "PAUSED":
            return {
                "status": "IGNORED",
                "reason": (
                    "Runtime не находится на паузе."
                ),
            }

        self.state = "IDLE"
        self.last_error = None

        return {
            "status": "RESUMED",
        }

    def reset_error(self):
        if self.state != "ERROR":
            return {
                "status": "IGNORED",
            }

        self.state = "IDLE"
        self.last_error = None

        return {
            "status": "RESET",
        }

    def close(self):
        if self._closed:
            return {
                "status": "ALREADY_CLOSED",
            }

        self.stop_background_loop()

        self._closed = True

        self._executor.shutdown(
            wait=True
        )

        self.state = "CLOSED"

        return {
            "status": "CLOSED",
        }
