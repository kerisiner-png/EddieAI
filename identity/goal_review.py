from dataclasses import dataclass


@dataclass
class GoalDecision:
    action: str
    goal: str
    score: float
    reason: str


class GoalReview:
    """
    Детерминированная проверка целей.

    Принимает как MotivationCandidate,
    так и уже созданный Goal.
    """

    MIN_SCORE = 0.60
    MIN_CONFIDENCE = 0.55

    def __init__(self, goal_manager):
        self.goal_manager = goal_manager

    def score(self, candidate):
        priority = float(
            getattr(candidate, "priority", 0.0)
        )

        motivation = float(
            getattr(candidate, "motivation", 0.0)
        )

        confidence = float(
            getattr(candidate, "confidence", 0.0)
        )

        return round(
            priority * 0.45
            + motivation * 0.35
            + confidence * 0.20,
            3,
        )

    def evaluate(self, candidate):
        goal_name = getattr(
            candidate,
            "goal",
            None,
        )

        if goal_name is None:
            goal_name = getattr(
                candidate,
                "value",
                None,
            )

        if not goal_name:
            return GoalDecision(
                action="REJECT",
                goal="",
                score=0.0,
                reason=(
                    "Объект не содержит "
                    "названия цели."
                ),
            )

        score = self.score(candidate)

        confidence = float(
            getattr(
                candidate,
                "confidence",
                0.0,
            )
        )

        if confidence < self.MIN_CONFIDENCE:
            return GoalDecision(
                action="DEFER",
                goal=goal_name,
                score=score,
                reason=(
                    "Недостаточная уверенность "
                    "в основании цели."
                ),
            )

        if score < self.MIN_SCORE:
            return GoalDecision(
                action="DEFER",
                goal=goal_name,
                score=score,
                reason=(
                    "Общая мотивационная ценность "
                    "пока слишком мала."
                ),
            )

        active = self.goal_manager.active()

        # Если сама цель уже активна, повторно
        # активировать её не требуется.
        existing = self.goal_manager.get(
            goal_name
        )

        if (
            existing is not None
            and existing.status == "ACTIVE"
        ):
            return GoalDecision(
                action="ALREADY_ACTIVE",
                goal=goal_name,
                score=score,
                reason=(
                    "Цель уже активна."
                ),
            )

        if (
            len(active)
            >= self.goal_manager.MAX_ACTIVE_GOALS
        ):
            return GoalDecision(
                action="DEFER",
                goal=goal_name,
                score=score,
                reason=(
                    "Все слоты активных целей заняты."
                ),
            )

        return GoalDecision(
            action="ACTIVATE",
            goal=goal_name,
            score=score,
            reason=(
                "Цель имеет достаточную "
                "мотивацию, приоритет "
                "и уверенность."
            ),
        )
