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
        agent=None,
        affective_behavior_policy=None,
    ):
        self.goal_manager = goal_manager
        self.goal_generator = goal_generator
        self.goal_plan_generator = goal_plan_generator
        self.agent_loop = agent_loop
        self.agent = agent
        self.affective_behavior_policy = (
            affective_behavior_policy
        )

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
            scored_goals = []

            for item in active:
                base_score = (
                    float(item.priority) * 0.50
                    + float(item.motivation) * 0.30
                    + float(item.confidence) * 0.20
                )

                affective_bias = 0.0

                if (
                    self.affective_behavior_policy
                    is not None
                ):
                    affective_bias = (
                        self.affective_behavior_policy
                        .goal_bias(item)
                    )

                scored_goals.append({
                    "goal": item,
                    "base_score": round(
                        base_score,
                        4,
                    ),
                    "affective_bias": (
                        affective_bias
                    ),
                    "total_score": round(
                        base_score
                        + affective_bias,
                        4,
                    ),
                })

            scored_goals.sort(
                key=lambda item: (
                    item["total_score"],
                    float(
                        item["goal"].priority
                    ),
                    float(
                        item["goal"].motivation
                    ),
                ),
                reverse=True,
            )

            goal = scored_goals[0]["goal"]

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

        if self.agent is not None:
            self.agent.autonomy_execution_state = {
                "busy": True,
                "goal": goal.value,
                "task": None,
            }

        try:
            execution = (
                self.agent_loop.run_once()
            )
        finally:
            if self.agent is not None:
                self.agent.autonomy_execution_state = {
                    "busy": False,
                    "goal": None,
                    "task": None,
                }

        return OrchestrationResult(
            status="EXECUTED",
            reason=(
                "Выполнен один автономный "
                "шаг активной цели."
            ),
            execution=execution,
        )
