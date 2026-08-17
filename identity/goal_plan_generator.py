import json

from ollama import chat


MODEL_NAME = "phi4-mini"

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

    def __init__(self, goal_planner):
        self.goal_planner = goal_planner

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

        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты создаёшь исполнимые планы "
                        "для автономного агента. "
                        "Каждый шаг должен быть "
                        "однозначно классифицируем."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options=MODEL_OPTIONS,
            keep_alive=-1,
        )

        raw = response[
            "message"
        ][
            "content"
        ].strip()

        tasks = self._parse_tasks(raw)

        if not tasks:
            tasks = self._fallback(
                goal
            )

        return self.goal_planner.create_plan(
            goal=goal,
            tasks=tasks,
        )

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
