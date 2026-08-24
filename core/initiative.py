from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class InitiativeDecision:
    should_act: bool
    reason: str
    goal: str | None = None


class InitiativeEngine:
    """
    Определяет, есть ли у EddieAI основание
    самостоятельно сделать один шаг.

    Пока решение полностью детерминированное.
    """

    def __init__(
        self,
        goal_manager,
        cooldown_seconds: int = 60,
    ):
        self.goal_manager = goal_manager
        self.cooldown_seconds = cooldown_seconds
        self.last_action_at = None

    def evaluate(self) -> InitiativeDecision:
        active = self.goal_manager.active()

        if not active:
            return InitiativeDecision(
                should_act=False,
                reason=(
                    "Нет активных целей."
                ),
            )

        now = datetime.now(
            timezone.utc
        )

        if self.last_action_at is not None:
            elapsed = (
                now - self.last_action_at
            ).total_seconds()

            if elapsed < self.cooldown_seconds:
                return InitiativeDecision(
                    should_act=False,
                    reason=(
                        "Cooldown ещё не завершён."
                    ),
                )

        goal = sorted(
            active,
            key=lambda item: (
                item.priority,
                item.motivation,
                item.confidence,
            ),
            reverse=True,
        )[0]

        return InitiativeDecision(
            should_act=True,
            reason=(
                "Есть активная цель, "
                "требующая следующего шага."
            ),
            goal=goal.value,
        )

    def mark_action(self):
        self.last_action_at = (
            datetime.now(
                timezone.utc
            )
        )

    def reset(self):
        self.last_action_at = None
