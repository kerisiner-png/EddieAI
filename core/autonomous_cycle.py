from dataclasses import dataclass


@dataclass
class AutonomousTick:
    status: str
    reason: str
    goal: str | None = None
    result: object | None = None


class AutonomousCycle:
    """
    Один контролируемый автономный тик.

    InitiativeEngine:
        решает, стоит ли действовать.

    AgentLoop:
        выполняет ограниченный набор действий.

    Здесь мы связываем их, но не создаём
    бесконечный фоновый процесс.
    """

    def __init__(
        self,
        initiative,
        agent_loop,
    ):
        self.initiative = initiative
        self.agent_loop = agent_loop

    def tick(self) -> AutonomousTick:
        decision = self.initiative.evaluate()

        if not decision.should_act:
            return AutonomousTick(
                status="IDLE",
                reason=decision.reason,
            )

        result = self.agent_loop.run_once()

        self.initiative.mark_action()

        return AutonomousTick(
            status="ACTED",
            reason=decision.reason,
            goal=decision.goal,
            result=result,
        )
