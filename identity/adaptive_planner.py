import json

from ollama import chat


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 320,
    "temperature": 0.3,
}


class AdaptivePlanner:
    """
    Предлагает изменения плана после получения нового опыта.

    Важно:
    он только предлагает изменения.
    Сам GoalPlanner пока ничего не переписывает.
    """

    def __init__(self):
        pass

    def review(
        self,
        goal: str,
        completed_task: str,
        result: dict,
        remaining_tasks: list[str],
    ):
        result_text = self._result_text(
            result
        )

        prompt = f"""
Ты пересматриваешь план автономного агента.

ЦЕЛЬ:
{goal}

ЗАВЕРШЁННАЯ ЗАДАЧА:
{completed_task}

РЕЗУЛЬТАТ:
{result_text}

ОСТАВШИЕСЯ ЗАДАЧИ:
{json.dumps(
    remaining_tasks,
    ensure_ascii=False,
    indent=2,
)}

Определи, нужен ли пересмотр плана.

Возможные решения:

"KEEP"
Оставить оставшиеся задачи без изменений.

"REPLACE"
Заменить оставшиеся задачи новыми.

"APPEND"
Сохранить оставшиеся задачи и добавить новые.

Правила:
- Не меняй саму цель.
- Не придумывай факты.
- Используй только предоставленный результат.
- Не повторяй уже выполненную задачу.
- Новые задачи должны быть конкретными и исполнимыми.
- Максимум 5 новых задач.
- Если пересмотр не нужен, используй KEEP.

Верни только JSON:

{{
  "decision": "KEEP|REPLACE|APPEND",
  "reason": "...",
  "tasks": [
    "Провести исследование: ...",
    "Проанализировать: ..."
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
                        "Ты занимаешься adaptive planning. "
                        "Отвечай только JSON."
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

        return self._parse(
            raw
        )

    def _result_text(
        self,
        result: dict,
    ):
        if not isinstance(
            result,
            dict,
        ):
            return str(result)

        payload = result.get(
            "result"
        )

        if isinstance(
            payload,
            dict,
        ):
            content = payload.get(
                "content"
            )

            if content:
                return str(content)

            interpretation = payload.get(
                "interpretation"
            )

            if interpretation:
                return str(
                    interpretation
                )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    def _parse(
        self,
        raw: str,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "decision": "KEEP",
                "reason": (
                    "Не удалось разобрать "
                    "решение adaptive planner."
                ),
                "tasks": [],
            }

        if not isinstance(
            data,
            dict,
        ):
            return {
                "decision": "KEEP",
                "reason": (
                    "Некорректный формат "
                    "adaptive planner."
                ),
                "tasks": [],
            }

        decision = data.get(
            "decision",
            "KEEP",
        )

        if decision not in {
            "KEEP",
            "REPLACE",
            "APPEND",
        }:
            decision = "KEEP"

        tasks = data.get(
            "tasks",
            [],
        )

        if not isinstance(
            tasks,
            list,
        ):
            tasks = []

        cleaned = []
        seen = set()

        for item in tasks:
            if not isinstance(
                item,
                str,
            ):
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

            if len(cleaned) >= 5:
                break

        return {
            "decision": decision,
            "reason": str(
                data.get(
                    "reason",
                    "",
                )
            ),
            "tasks": cleaned,
        }
