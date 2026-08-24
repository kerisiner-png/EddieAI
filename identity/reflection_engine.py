import json

from ollama import chat

from memory.events import Event


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 384,
    "temperature": 0.25,
}


class ReflectionEngine:
    """
    Анализирует завершённый автономный шаг.

    Reflection не считается фактом.
    Сигналы личности появляются только как evidence,
    после чего PersonalityLifecycle решает,
    достаточно ли оснований для изменения trait.
    """

    def __init__(
        self,
        memory,
        evidence,
        personality_lifecycle,
    ):
        self.memory = memory
        self.evidence = evidence
        self.personality = (
            personality_lifecycle
        )

    def reflect(
        self,
        goal: str,
        task: str,
        action: dict,
        result: dict,
    ):
        result_text = self._result_text(
            result
        )

        prompt = f"""
Проанализируй завершённое действие автономного агента.

ЦЕЛЬ:
{goal}

ЗАДАЧА:
{task}

ДЕЙСТВИЕ:
{json.dumps(
    action,
    ensure_ascii=False,
    indent=2,
)}

РЕЗУЛЬТАТ:
{result_text}

Определи:

1. Что агент узнал или подтвердил.
2. Что пошло неидеально.
3. Какой урок стоит сохранить.
4. Есть ли наблюдение, которое может быть
   устойчивым сигналом интереса, предпочтения,
   привычки или убеждения.
5. Может ли завершённое действие естественно
   породить следующий конкретный шаг.

Очень важно:
- единичное действие НЕ доказывает черту личности;
- не придумывай психологические свойства;
- если сигнала недостаточно, верни пустой список;
- evidence confidence должен быть осторожным;
- не превращай внешний источник в собственный факт;
- follow_up_goals должны быть конкретными следующими
  действиями, вытекающими из результата этой цели;
- не создавай цели ради активности;
- не предлагай помощь пользователю как цель;
- не дублируй уже завершённую цель;
- если естественного следующего шага нет, верни [].

Верни только JSON:

{{
  "lesson": "...",
  "error": null,
  "signals": [
    {{
      "category": "interest|preference|habit|belief",
      "value": "...",
      "confidence": 0.0
    }}
  ],
  "follow_up_goals": [
    {{
      "goal": "...",
      "motivation": 0.0,
      "priority": 0.0,
      "confidence": 0.0,
      "reason": "..."
    }}
  ],
  "confidence": 0.0
}}

Без markdown.
"""

        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты выполняешь осторожную "
                        "рефлексию автономного агента. "
                        "Не диагностируй личность "
                        "по одному действию."
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

        data = self._parse(
            raw
        )

        if data is None:
            data = {
                "lesson": "",
                "error": (
                    "Не удалось разобрать "
                    "reflection output."
                ),
                "signals": [],
                "confidence": 0.1,
            }

        lesson = str(
            data.get(
                "lesson",
                "",
            )
        ).strip()

        error = data.get(
            "error"
        )

        if error is not None:
            error = str(error).strip()

        confidence = self._confidence(
            data.get(
                "confidence",
                0.0,
            )
        )

        signals = self._clean_signals(
            data.get(
                "signals",
                [],
            )
        )

        self._save_reflection(
            goal=goal,
            task=task,
            lesson=lesson,
            error=error,
            confidence=confidence,
            signals=signals,
        )

        # Reflection produces interpretation signals only.
        # These signals are not independent evidence.

        follow_up_goals = (
            self._clean_follow_up_goals(
                data.get(
                    "follow_up_goals",
                    [],
                ),
                completed_goal=goal,
                result_text=result_text,
            )
        )

        return {
            "status": "OK",
            "lesson": lesson,
            "error": error,
            "confidence": confidence,
            "signals": signals,
            "follow_up_goals": follow_up_goals,
            "evidence": [],
        }

    def _save_reflection(
        self,
        goal,
        task,
        lesson,
        error,
        confidence,
        signals,
    ):
        content = {
            "goal": goal,
            "task": task,
            "lesson": lesson,
            "error": error,
            "confidence": confidence,
            "signals": signals,
        }

        self.memory.remember(
            Event.create(
                content=json.dumps(
                    content,
                    ensure_ascii=False,
                ),
                event_type="REFLECTION",
                source_type="REFLECTION_ENGINE",
                source="SELF",
                personal_experience=True,
                confidence=confidence,
                verified=False,
            )
        )

    def _result_text(
        self,
        result,
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
            interpretation = payload.get(
                "interpretation"
            )

            if interpretation:
                return json.dumps(
                    interpretation,
                    ensure_ascii=False,
                    indent=2,
                )

            content = payload.get(
                "content"
            )

            if content:
                return str(content)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    def _clean_follow_up_goals(
        self,
        goals,
        *,
        completed_goal: str,
        result_text: str,
    ):
        if not isinstance(
            goals,
            list,
        ):
            return []

        cleaned = []

        for item in goals:
            if not isinstance(
                item,
                dict,
            ):
                continue

            goal = str(
                item.get(
                    "goal",
                    "",
                )
            ).strip()

            if not goal:
                continue

            if len(goal) > 280:
                continue

            if not self._follow_up_is_relevant(
                goal=goal,
                completed_goal=completed_goal,
                result_text=result_text,
            ):
                continue

            motivation = self._confidence(
                item.get(
                    "motivation",
                    0.0,
                )
            )

            priority = self._confidence(
                item.get(
                    "priority",
                    0.0,
                )
            )

            confidence = self._confidence(
                item.get(
                    "confidence",
                    0.0,
                )
            )

            reason = str(
                item.get(
                    "reason",
                    "",
                )
            ).strip()

            cleaned.append({
                "goal": goal,
                "motivation": motivation,
                "priority": priority,
                "confidence": confidence,
                "reason": reason,
            })

            if len(cleaned) >= 3:
                break

        return cleaned


    @staticmethod
    def _follow_up_is_relevant(
        *,
        goal: str,
        completed_goal: str,
        result_text: str,
    ) -> bool:
        import re

        stopwords = {
            "изучить",
            "изучение",
            "исследовать",
            "исследование",
            "продолжить",
            "продолжение",
            "тема",
            "темы",
            "далее",
            "глубже",
            "подробнее",
            "лучше",
            "понимание",
            "помочь",
            "помощь",
            "пользователь",
            "пользователю",
            "сейчас",
            "новые",
            "нового",
            "новое",
            "аспекты",
            "аспектов",
            "область",
            "области",
        }

        def tokens(
            value: str,
        ) -> set[str]:

            raw = re.findall(
                r"[A-Za-zА-Яа-яЁё0-9]{5,}",
                str(value).casefold(),
            )

            return {
                token.replace(
                    "ё",
                    "е",
                )
                for token in raw
                if token not in stopwords
            }

        goal_tokens = tokens(goal)

        source_tokens = (
            tokens(completed_goal)
            | tokens(result_text)
        )

        if (
            not goal_tokens
            or not source_tokens
        ):
            return False

        for left in goal_tokens:
            for right in source_tokens:

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


    def _clean_signals(
        self,
        signals,
    ):
        if not isinstance(
            signals,
            list,
        ):
            return []

        allowed = {
            "interest",
            "preference",
            "habit",
            "belief",
        }

        cleaned = []

        for signal in signals:
            if not isinstance(
                signal,
                dict,
            ):
                continue

            category = signal.get(
                "category"
            )

            value = str(
                signal.get(
                    "value",
                    "",
                )
            ).strip()

            if category not in allowed:
                continue

            if not value:
                continue

            confidence = self._confidence(
                signal.get(
                    "confidence",
                    0.0,
                )
            )

            cleaned.append({
                "category": category,
                "value": value,
                "confidence": confidence,
            })

            if len(cleaned) >= 5:
                break

        return cleaned

    def _parse(
        self,
        raw: str,
    ):
        text = raw.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].strip().lower() in {
                "```json",
                "```",
            }:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip()
                == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(
                lines
            ).strip()

        try:
            data = json.loads(
                text
            )

            if isinstance(
                data,
                dict,
            ):
                return data

        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            try:
                data = json.loads(
                    text[start:end + 1]
                )

                if isinstance(
                    data,
                    dict,
                ):
                    return data

            except json.JSONDecodeError:
                pass

        return None

    def _confidence(
        self,
        value,
    ):
        try:
            value = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        return max(
            0.0,
            min(1.0, value),
        )
