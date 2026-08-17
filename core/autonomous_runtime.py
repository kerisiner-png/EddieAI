from dataclasses import dataclass
from datetime import datetime, timezone


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

        # Optional post-cycle consolidation.
        self.evidence_consolidator = None

    def snapshot(self):
        return RuntimeSnapshot(
            state=self.state,
            started_at=self.started_at,
            last_error=self.last_error,
            last_result=self.last_result,
            cycles_completed=self.cycles_completed,
        )

    def tick(self):
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
            # -------------------------------------
            # AUTONOMOUS ACTION
            # -------------------------------------

            self.state = "ACTING"

            result = self.scheduler.tick()

            self.last_result = result
            self.cycles_completed += 1

            # -------------------------------------
            # POST-CYCLE CONSOLIDATION
            # -------------------------------------

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
