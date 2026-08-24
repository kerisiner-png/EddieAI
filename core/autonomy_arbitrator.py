from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AutonomyDecision:
    action: str
    reason: str
    goal: str | None = None
    priority: float = 0.0


class AutonomyArbitrator:
    """
    Решает, стоит ли сейчас отдавать приоритет
    пользовательскому запросу относительно
    фактически выполняемой собственной деятельности.

    Наличие ACTIVE goal само по себе не означает,
    что EddieAI занят.
    """

    STOPWORDS = {
        "который",
        "которая",
        "которые",
        "когда",
        "чтобы",
        "можешь",
        "можно",
        "пожалуйста",
        "расскажи",
        "скажи",
        "помоги",
        "объясни",
        "мне",
        "тебе",
        "тебя",
        "это",
        "есть",
        "как",
        "что",
        "про",
        "для",
        "сейчас",
        "тоже",
        "просто",
    }

    def __init__(
        self,
        goal_manager,
        agent=None,
        high_priority_threshold: float = 0.80,
    ):
        self.goal_manager = goal_manager
        self.agent = agent
        self.high_priority_threshold = (
            high_priority_threshold
        )

    def evaluate(
        self,
        message: str,
    ) -> AutonomyDecision:

        state = getattr(
            self.agent,
            "autonomy_execution_state",
            None,
        )

        if not isinstance(
            state,
            dict,
        ):
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "Фактическое состояние "
                    "автономного выполнения недоступно."
                ),
            )

        if not state.get(
            "busy",
            False,
        ):
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "EddieAI сейчас не выполняет "
                    "автономную задачу."
                ),
            )

        goal_value = state.get(
            "goal"
        )

        if not goal_value:
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "Автономное выполнение активно, "
                    "но текущая цель не определена."
                ),
            )

        goal = self.goal_manager.get(
            goal_value
        )

        if goal is None:
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "Текущая автономная цель "
                    "не найдена в GoalManager."
                ),
            )

        priority = float(
            goal.priority
        )

        if (
            priority
            < self.high_priority_threshold
        ):
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "Текущая автономная деятельность "
                    "не имеет достаточного приоритета "
                    "для откладывания пользовательского запроса."
                ),
                goal=goal.value,
                priority=priority,
            )

        if self._is_related(
            message,
            goal.value,
        ):
            return AutonomyDecision(
                action="ACCEPT",
                reason=(
                    "Пользовательский запрос связан "
                    "с текущей автономной деятельностью."
                ),
                goal=goal.value,
                priority=priority,
            )

        return AutonomyDecision(
            action="DEFER",
            reason=(
                "EddieAI действительно выполняет "
                "собственную задачу высокой приоритетности, "
                "а пользовательский запрос с ней "
                "не связан."
            ),
            goal=goal.value,
            priority=priority,
        )

    @classmethod
    def _tokens(
        cls,
        text: str,
    ) -> set[str]:

        raw = re.findall(
            r"[A-Za-zА-Яа-яЁё]{5,}",
            str(text).casefold(),
        )

        return {
            token.replace(
                "ё",
                "е",
            )
            for token in raw
            if token not in cls.STOPWORDS
        }

    @classmethod
    def _is_related(
        cls,
        message: str,
        goal: str,
    ) -> bool:

        message_tokens = cls._tokens(
            message
        )

        goal_tokens = cls._tokens(
            goal
        )

        if (
            not message_tokens
            or not goal_tokens
        ):
            return False

        for left in message_tokens:
            for right in goal_tokens:

                if left == right:
                    return True

                if (
                    len(left) >= 6
                    and len(right) >= 6
                    and (
                        left[:6] == right[:6]
                        or left in right
                        or right in left
                    )
                ):
                    return True

        return False
