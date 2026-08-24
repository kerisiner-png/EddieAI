from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


@dataclass
class ScheduleDecision:
    should_tick: bool
    reason: str
    next_allowed_at: str | None = None


class AutonomyScheduler:
    """
    Планировщик автономных тиков.

    Не выполняет действия сам.
    Он только решает, разрешено ли сейчас
    передать управление AutonomousCycle.
    """

    def __init__(
        self,
        autonomous_cycle,
        interval_seconds: int = 300,
        max_ticks_per_window: int = 3,
        window_seconds: int = 3600,
    ):
        self.autonomous_cycle = autonomous_cycle

        self.interval_seconds = max(
            1,
            int(interval_seconds),
        )

        self.max_ticks_per_window = max(
            1,
            int(max_ticks_per_window),
        )

        self.window_seconds = max(
            self.interval_seconds,
            int(window_seconds),
        )

        self.enabled = True

        self.last_tick_at = None
        self.tick_history = []

    def evaluate(self) -> ScheduleDecision:
        if not self.enabled:
            return ScheduleDecision(
                should_tick=False,
                reason="Автономный режим отключён.",
            )

        now = datetime.now(
            timezone.utc
        )

        self._cleanup_history(now)

        if len(
            self.tick_history
        ) >= self.max_ticks_per_window:
            next_allowed = (
                self._next_window_time()
            )

            return ScheduleDecision(
                should_tick=False,
                reason=(
                    "Достигнут лимит автономных "
                    "тиков за окно."
                ),
                next_allowed_at=(
                    next_allowed.isoformat()
                    if next_allowed
                    else None
                ),
            )

        if self.last_tick_at is not None:
            elapsed = (
                now - self.last_tick_at
            ).total_seconds()

            if elapsed < self.interval_seconds:
                next_time = (
                    self.last_tick_at
                    + timedelta(
                        seconds=self.interval_seconds
                    )
                )

                return ScheduleDecision(
                    should_tick=False,
                    reason=(
                        "Интервал между "
                        "автономными тиками ещё "
                        "не истёк."
                    ),
                    next_allowed_at=(
                        next_time.isoformat()
                    ),
                )

        return ScheduleDecision(
            should_tick=True,
            reason=(
                "Автономный тик разрешён."
            ),
        )

    def tick(self):
        decision = self.evaluate()

        if not decision.should_tick:
            return {
                "status": "SCHEDULED_IDLE",
                "decision": decision,
                "result": None,
            }

        result = (
            self.autonomous_cycle.tick()
        )

        now = datetime.now(
            timezone.utc
        )

        self.last_tick_at = now

        self.tick_history.append(
            now
        )

        return {
            "status": "TICK_EXECUTED",
            "decision": decision,
            "result": result,
        }

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def reset(self):
        self.last_tick_at = None
        self.tick_history.clear()

    def _cleanup_history(self, now):
        cutoff = (
            now
            - timedelta(
                seconds=self.window_seconds
            )
        )

        self.tick_history = [
            timestamp
            for timestamp in self.tick_history
            if timestamp >= cutoff
        ]

    def _next_window_time(self):
        if not self.tick_history:
            return None

        oldest = min(
            self.tick_history
        )

        return oldest + timedelta(
            seconds=self.window_seconds
        )
