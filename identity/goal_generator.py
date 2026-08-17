from dataclasses import dataclass


@dataclass
class GoalGenerationResult:
    goal: str
    status: str
    motivation: float
    priority: float
    confidence: float
    reason: str
    plan_created: bool = False


class GoalGenerator:
    """
    Преобразует мотивационные кандидаты
    в цели и, после активации, автоматически
    создаёт для них первоначальный план.
    """

    def __init__(
        self,
        motivation_engine,
        goal_manager,
        goal_review,
        goal_plan_generator=None,
    ):
        self.motivation_engine = (
            motivation_engine
        )

        self.goal_manager = (
            goal_manager
        )

        self.goal_review = goal_review

        self.goal_plan_generator = (
            goal_plan_generator
        )

    def generate(self):
        candidates = (
            self.motivation_engine.candidates()
        )

        results = []

        for candidate in candidates:
            existing = self.goal_manager.get(
                candidate.goal
            )

            if existing is not None:
                plan_created = (
                    self.goal_manager.planner
                    .get_plan(
                        candidate.goal
                    )
                    is not None
                )

                results.append(
                    GoalGenerationResult(
                        goal=candidate.goal,
                        status="EXISTS",
                        motivation=(
                            candidate.motivation
                        ),
                        priority=(
                            candidate.priority
                        ),
                        confidence=(
                            candidate.confidence
                        ),
                        reason=(
                            "Такая цель уже существует."
                        ),
                        plan_created=plan_created,
                    )
                )

                continue

            goal = (
                self.goal_manager.add_candidate(
                    value=candidate.goal,
                    motivation=candidate.motivation,
                    priority=candidate.priority,
                    confidence=candidate.confidence,
                    source="motivation_engine",
                )
            )

            decision = (
                self.goal_review.evaluate(
                    goal
                )
            )

            if decision.action == "ACTIVATE":
                activated = (
                    self.goal_manager.activate(
                        goal.value
                    )
                )

                if activated["status"] == "ACTIVATED":
                    status = "ACTIVATED"
                else:
                    status = "DEFERRED"
            else:
                status = "DEFERRED"

            plan_created = False

            if (
                status == "ACTIVATED"
                and self.goal_plan_generator
                is not None
            ):
                self.goal_plan_generator.generate(
                    goal=goal.value,
                    context=(
                        "Цель возникла из "
                        "мотивационной системы. "
                        f"Источник: "
                        f"{candidate.source_traits}"
                    ),
                )

                plan_created = True

            results.append(
                GoalGenerationResult(
                    goal=goal.value,
                    status=status,
                    motivation=(
                        candidate.motivation
                    ),
                    priority=(
                        candidate.priority
                    ),
                    confidence=(
                        candidate.confidence
                    ),
                    reason=decision.reason,
                    plan_created=plan_created,
                )
            )

        return results
