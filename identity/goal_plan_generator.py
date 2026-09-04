import json

from identity.llm_access import CloudFirstLlm
from identity.plan_feasibility import PlanFeasibility


MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 320,
    "temperature": 0.3,
}


class GoalPlanGenerator:
    """
    Создаёт исполнимый план для активной цели.

    Особенность:
    шаг должен быть достаточно конкретным, чтобы
    ActionPlanner мог сопоставить его с инструментом.
    """

    MIN_TASKS = 3
    MAX_TASKS = 5

    def __init__(
        self,
        goal_planner,
        model_orchestrator=None,
        feasibility=None,
    ):
        self.goal_planner = goal_planner
        self.feasibility = (
            feasibility
            if feasibility is not None
            else PlanFeasibility()
        )
        self.llm = CloudFirstLlm(
            model_orchestrator
        )

    def generate(
        self,
        goal: str,
        context: str = "",
    ):
        existing = self.goal_planner.get_plan(
            goal
        )

        if existing is not None:
            return existing

        prompt = f"""
Составь исполнимый план для цели:

{goal}

Контекст:
{context}

Нужно 3–5 шагов.

КРИТИЧЕСКОЕ ТРЕБОВАНИЕ:
каждый шаг должен начинаться с понятного
действия, которое автономный агент может выполнить.

Используй такие формы:

- "Провести исследование: ..."
- "Найти информацию: ..."
- "Прочитать файл: ..."
- "Проанализировать: ..."
- "Записать: ..."

Не используй расплывчатые формулировки:

- "Получить необходимую информацию..."
- "Заняться изучением..."
- "Дальше изучать..."
- "Сделать вывод..."

Если требуется внешний поиск,
начинай шаг с "Провести исследование:"
или "Найти информацию:".

Если требуется внутренний анализ,
используй "Проанализировать:".

Верни только JSON:

{{
  "tasks": [
    "Провести исследование: ...",
    "Проанализировать: ...",
    "Записать: ..."
  ]
}}

Без markdown.
"""

        raw = self.llm.chat(
            system=(
                "Ты создаёшь исполнимые планы "
                "для автономного агента. "
                "Каждый шаг должен быть "
                "однозначно классифицируем."
            ),
            user=prompt,
            options=MODEL_OPTIONS,
            task="plan",
        )

        tasks = []

        if raw:
            tasks = self._parse_tasks(raw)

        tasks = self._sanitize_tasks(
            goal,
            tasks,
        )

        if not tasks:
            tasks = self._fallback(
                goal
            )

            tasks = self._sanitize_tasks(
                goal,
                tasks,
            )

        return self.goal_planner.create_plan(
            goal=goal,
            tasks=tasks,
        )

    def _sanitize_tasks(
        self,
        goal: str,
        tasks: list[str],
    ) -> list[str]:
        """
        Прогон плана через оценку выполнимости
        и декомпозицию фаз.

        Отсекает шаги без доступного инструмента
        и добавляет недостающие выполнимые фазы.
        """

        if not tasks:
            return []

        feasible, _ = self.feasibility.assess(
            goal,
            tasks,
        )

        if not feasible:
            return []

        phases = self.feasibility.ensure_phases(
            goal,
            feasible,
        )

        seen = set()
        cleaned = []

        for task in phases:
            key = task.strip().lower()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(task)

        if len(cleaned) < self.MIN_TASKS:
            return []

        return cleaned[: self.MAX_TASKS]

    def _parse_tasks(
        self,
        raw: str,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(data, dict):
            return []

        tasks = data.get(
            "tasks",
            [],
        )

        if not isinstance(tasks, list):
            return []

        cleaned = []

        seen = set()

        for item in tasks:
            if not isinstance(item, str):
                continue

            task = " ".join(
                item.strip().split()
            )

            if not task:
                continue

            key = task.lower()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(task)

            if len(cleaned) >= self.MAX_TASKS:
                break

        if len(cleaned) < self.MIN_TASKS:
            return []

        return cleaned

    def _fallback(
        self,
        goal: str,
    ):
        return [
            (
                "Провести исследование: "
                f"{goal}"
            ),
            (
                "Проанализировать результаты "
                f"исследования по цели: {goal}"
            ),
            (
                "Сформулировать выводы по цели: "
                f"{goal}"
            ),
        ]
