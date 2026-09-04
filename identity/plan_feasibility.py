from dataclasses import dataclass

from identity.action_planner import ActionPlanner


DEFAULT_AVAILABLE_ACTIONS = {
    "RESEARCH",
    "WEB_SEARCH",
    "READ_FILE",
    "WRITE_FILE",
    "LIST_DIR",
    "SEARCH_FILES",
    "RUN_COMMAND",
    "THINK",
}


@dataclass
class FeasibilityIssue:
    task: str
    action_type: str
    reason: str


class PlanFeasibility:
    """
    Оценка выполнимости плана по доступным инструментам.

    Классифицирует каждый шаг через ActionPlanner
    в конкретный action_type и сверяет с множеством
    доступных действий. Никаких LLM-вызовов —
    чисто детерминированная проверка.
    """

    RESEARCH_PHASE_KEYWORDS = (
        "провести исследование",
        "исследовать",
        "найти информацию",
        "найти данные",
        "найти материал",
        "найти источник",
        "прочитать",
        "открыть файл",
        "посмотреть файл",
        "изучить",
    )

    ANALYZE_PHASE_KEYWORDS = (
        "анализировать",
        "анализ",
        "разобраться",
        "подумать",
        "сформулировать выводы",
        "оценить",
        "проанализировать",
    )

    WRITE_PHASE_KEYWORDS = (
        "записать",
        "создать файл",
        "сохранить",
        "зафиксировать",
        "оформить",
        "добавить запись",
    )

    def __init__(
        self,
        planner=None,
        available_actions=None,
    ):
        self.planner = (
            planner
            if planner is not None
            else ActionPlanner()
        )

        self.available_actions = (
            available_actions
            if available_actions is not None
            else set(DEFAULT_AVAILABLE_ACTIONS)
        )

    def action_type_of(
        self,
        task: str,
    ):
        try:
            plan = self.planner.plan(
                _TaskLike(task)
            )
        except Exception:
            return "THINK"

        return plan.action_type

    def check(
        self,
        tasks: list[str],
    ) -> list[FeasibilityIssue]:
        issues = []

        for task in tasks:
            action_type = self.action_type_of(
                task
            )

            if action_type not in self.available_actions:
                issues.append(
                    FeasibilityIssue(
                        task=task,
                        action_type=action_type,
                        reason=(
                            f"{action_type} недоступен: "
                            "нет инструмента для "
                            "выполнения шага."
                        ),
                    )
                )

        return issues

    def assess(
        self,
        goal: str,
        tasks: list[str],
    ):
        issues = self.check(tasks)

        unavailable = {
            issue.task
            for issue in issues
        }

        feasible = [
            task
            for task in tasks
            if task not in unavailable
        ]

        return feasible, issues

    def ensure_phases(
        self,
        goal: str,
        tasks: list[str],
    ) -> list[str]:
        """
        Декомпозиция цели на этапы достижения.

        Проверяет наличие ключевых фаз
        (добыча -> анализ -> фиксация) и добавляет
        недостающие выполнимые фазы детерминированно.
        """

        result = list(tasks)

        phases_present = set()

        for task in result:
            phase = self._phase_of(task)

            if phase is not None:
                phases_present.add(phase)

        if (
            "research" not in phases_present
            and "RESEARCH" in self.available_actions
        ):
            phases_present.add("research")

        if (
            "analyze" not in phases_present
            and "THINK" in self.available_actions
        ):
            phases_present.add("analyze")

        if (
            "write" not in phases_present
            and "WRITE_FILE" in self.available_actions
        ):
            phases_present.add("write")

        for phase in (
            "research",
            "analyze",
            "write",
        ):
            task = self._phase_task(
                phase,
                goal,
            )

            if task is None:
                continue

            if self.action_type_of(
                task
            ) not in self.available_actions:
                continue

            if self._phase_of(task) in (
                phases_present
            ) and task not in result:
                result.append(task)

        return result

    def _phase_of(
        self,
        task: str,
    ):
        text = task.lower()

        if any(
            keyword in text
            for keyword in (
                self.RESEARCH_PHASE_KEYWORDS
            )
        ):
            return "research"

        if any(
            keyword in text
            for keyword in (
                self.WRITE_PHASE_KEYWORDS
            )
        ):
            return "write"

        if any(
            keyword in text
            for keyword in (
                self.ANALYZE_PHASE_KEYWORDS
            )
        ):
            return "analyze"

        return None

    def _phase_task(
        self,
        phase: str,
        goal: str,
    ):
        if phase == "research":
            return (
                "Провести исследование: "
                f"{goal}"
            )

        if phase == "analyze":
            return (
                "Проанализировать результаты "
                f"по цели: {goal}"
            )

        if phase == "write":
            return (
                "Записать результаты "
                f"по цели: {goal}"
            )

        return None


class _TaskLike:
    """
    Минимальная обёртка задачи для ActionPlanner,
    у которого API ожидает объект с атрибутом title.
    """

    def __init__(self, title: str):
        self.title = title
