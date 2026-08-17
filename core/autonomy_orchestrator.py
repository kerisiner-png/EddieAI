from dataclasses import dataclass


@dataclass
class OrchestrationResult:
    status: str
    reason: str
    goal_generation: object | None = None
    execution: object | None = None


class AutonomyOrchestrator:
    """
    Решает, какой этап автономного цикла нужен сейчас.

    Приоритет:
    1. проверить активные цели;
    2. при отсутствии — попробовать создать цель;
    3. при наличии цели без плана — создать план;
    4. при готовой цели — выполнить один шаг.
    """

    def __init__(
        self,
        goal_manager,
        goal_generator,
        goal_plan_generator,
        agent_loop,
    ):
        self.goal_manager = goal_manager
        self.goal_generator = goal_generator
        self.goal_plan_generator = goal_plan_generator
        self.agent_loop = agent_loop

    def tick(self):
        active = self.goal_manager.active()

        # -----------------------------------------
        # Нет активных целей
        # -----------------------------------------

        if not active:
            generated = (
                self.goal_generator.generate()
            )

            active = self.goal_manager.active()

            if not active:
                return OrchestrationResult(
                    status="NO_MOTIVATION",
                    reason=(
                        "Нет активных целей и "
                        "мотивационная система "
                        "не создала новую цель."
                    ),
                    goal_generation=generated,
                )

            goal = active[0]

        else:
            goal = sorted(
                active,
                key=lambda item: (
                    item.priority,
                    item.motivation,
                    item.confidence,
                ),
                reverse=True,
            )[0]

        # -----------------------------------------
        # Нет плана
        # -----------------------------------------

        existing_plan = (
            self.goal_manager.planner
            .get_plan(
                goal.value
            )
        )

        if existing_plan is None:
            plan = (
                self.goal_plan_generator.generate(
                    goal=goal.value,
                    context=(
                        "Автономно созданная "
                        "активная цель."
                    ),
                )
            )

            return OrchestrationResult(
                status="PLAN_CREATED",
                reason=(
                    "Для активной цели "
                    "создан план."
                ),
                execution=None,
                goal_generation=None,
            )

        # -----------------------------------------
        # Есть цель и план
        # -----------------------------------------

        execution = (
            self.agent_loop.run_once()
        )

        return OrchestrationResult(
            status="EXECUTED",
            reason=(
                "Выполнен один автономный "
                "шаг активной цели."
            ),
            execution=execution,
        )
