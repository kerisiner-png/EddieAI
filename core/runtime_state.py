class RuntimeState:
    """
    Read-only снимок фактического состояния runtime EddieAI.

    Ничего не запускает, не останавливает и не изменяет.
    """

    def __init__(
        self,
        agent,
    ):
        self.agent = agent

    def snapshot(self) -> dict:
        result = {
            "worker": self._worker_state(),
            "cognition": self._cognition_state(),
            "activity": self._activity_state(),
        }

        return result

    def render(self) -> str:
        state = self.snapshot()

        worker = state["worker"]
        cognition = state["cognition"]
        activity = state["activity"]

        return f"""
CURRENT RUNTIME STATE OF EDDIEAI

Worker:
state = {worker.get("state")}
processed_count = {worker.get("processed_count")}
last_error = {worker.get("last_error")}

Cognition:
queue = {cognition.get("queue")}
pending = {cognition.get("pending")}
analyzed = {cognition.get("analyzed")}
done = {cognition.get("done")}
failed = {cognition.get("failed")}

Activity:
mode = {activity.get("mode")}
background_cognition = {activity.get("background_cognition")}

IMPORTANT:
This block describes the actual current runtime state.
Do not claim that a background process is running unless
the state above says that it is RUNNING.
"""

    def _worker_state(self):
        worker = getattr(
            self.agent,
            "cognition_worker",
            None,
        )

        if worker is None:
            return {
                "state": "UNAVAILABLE",
                "processed_count": 0,
                "last_error": None,
            }

        try:
            snapshot = worker.snapshot()

            return {
                "state": snapshot.get(
                    "state",
                    "UNKNOWN",
                ),
                "processed_count": snapshot.get(
                    "processed_count",
                    0,
                ),
                "last_error": snapshot.get(
                    "last_error",
                ),
            }

        except Exception as exc:
            return {
                "state": "ERROR",
                "processed_count": 0,
                "last_error": str(exc),
            }

    def _cognition_state(self):
        queue = getattr(
            self.agent,
            "cognitive_queue",
            None,
        )

        if queue is None:
            return {
                "queue": {},
                "pending": 0,
                "analyzed": 0,
                "done": 0,
                "failed": 0,
            }

        try:
            stats = queue.stats()

            return {
                "queue": stats,
                "pending": stats.get(
                    "PENDING",
                    0,
                ),
                "analyzed": stats.get(
                    "ANALYZED",
                    0,
                ),
                "done": stats.get(
                    "DONE",
                    0,
                ),
                "failed": stats.get(
                    "FAILED",
                    0,
                ),
            }

        except Exception:
            return {
                "queue": {},
                "pending": 0,
                "analyzed": 0,
                "done": 0,
                "failed": 0,
            }

    def _activity_state(self):
        worker = self._worker_state()

        return {
            "mode": "conversation",
            "background_cognition": (
                worker.get("state") == "RUNNING"
            ),
        }
