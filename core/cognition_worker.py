import threading
import time


class CognitionWorker:
    """
    Фоновый worker для отложенной когнитивной обработки.

    Worker только анализирует события.

    Применение результата к:
        - self_state
        - IdentityManager
        - GoalManager
        - Memory

    выполняется главным потоком через
    CognitiveProcessor.apply_analyzed().
    """

    def __init__(
        self,
        processor,
        poll_interval: float = 1.0,
    ):
        self.processor = processor
        self.poll_interval = max(
            0.1,
            float(poll_interval),
        )

        self._thread = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()

        self.state = "STOPPED"
        self.last_result = None
        self.last_error = None
        self.processed_count = 0
        self.max_restarts = 5
        self.restart_count = 0

    def start(self):
        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            return {
                "status": "ALREADY_RUNNING",
            }

        self._stop_event.clear()
        self._wake_event.clear()

        self.state = "RUNNING"
        self.last_error = None

        self._thread = threading.Thread(
            target=self._run,
            name="EddieAI-CognitionWorker",
            daemon=True,
        )

        self._thread.start()

        return {
            "status": "STARTED",
        }

    def stop(
        self,
        timeout: float = 2.0,
    ):
        self._stop_event.set()
        self._wake_event.set()

        thread = self._thread

        if (
            thread is not None
            and thread.is_alive()
        ):
            thread.join(
                timeout=max(
                    0.1,
                    float(timeout),
                )
            )

        if (
            thread is not None
            and thread.is_alive()
        ):
            self.state = "STOPPING"
        else:
            self.state = "STOPPED"

        return {
            "status": self.state,
        }

    def wake(self):
        self._wake_event.set()

    def _should_restart(self):
        return self.restart_count < self.max_restarts

    def snapshot(self):
        return {
            "state": self.state,
            "processed_count": (
                self.processed_count
            ),
            "restart_count": self.restart_count,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

    def _run(self):
        while not self._stop_event.is_set():
            try:
                result = (
                    self.processor.analyse_next()
                )

                self.last_result = result

                if result.get("status") != "EMPTY":
                    self.processed_count += 1

                self.restart_count = 0
                self.last_error = None
                self.state = "RUNNING"
                self._wake_event.clear()

            except Exception as exc:
                self.last_error = str(exc)
                self.restart_count += 1

                if not self._should_restart():
                    self.state = "ERROR"
                    return

                self.state = "RETRYING"
                self._wake_event.clear()

                if self._stop_event.wait(
                    min(
                        self.poll_interval
                        * self.restart_count,
                        60.0,
                    )
                ):
                    return

                continue

            self._wake_event.wait(
                self.poll_interval
            )

        self.state = "STOPPED"
