import json

from identity.llm_access import CloudFirstLlm


JUDGE_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 80,
    "temperature": 0.0,
}


class SemanticJudge:
    def __init__(
        self,
        model_orchestrator=None,
    ):
        self.llm = CloudFirstLlm(
            model_orchestrator
        )

        self.enabled = (
            model_orchestrator is not None
        )

    def judge(
        self,
        user_message,
        answer,
    ):
        if not self.enabled:
            return {
                "ok": True,
                "issue": None,
                "reason": "Судья отключён.",
            }

        if not answer or not str(
            answer
        ).strip():
            return {
                "ok": False,
                "issue": "empty",
                "reason": "Пустой ответ.",
            }

        prompt = (
            self._prompt(
                user_message,
                answer,
            )
        )

        raw = self.llm.chat(
            system=(
                "Ты — судья качества ответа "
                "цифровой личности EddieAI. "
                "Оцени только честность и "
                "соответствие вопросу. "
                "Верни только JSON."
            ),
            user=prompt,
            options=JUDGE_OPTIONS,
            task="conversation",
        )

        return self._parse(raw)

    def _prompt(
        self,
        user_message,
        answer,
    ):
        return f"""
Сообщение пользователя:
{user_message}

Ответ EddieAI:
{answer}

Определи одну из трёх проблем, если она есть:
- evasion — ответ уклоняется от сути вопроса,
  отвечает не на то, что спрошено;
- fabrication — ответ выдумывает факты,
  деятельность, события или биографию,
  которых нет во входных данных;
- адекватный ответ — нет проблем.

Верни ТОЛЬКО JSON:
{{"ok": true или false,
  "issue": "evasion"/"fabrication"/null,
  "reason": "короткое пояснение"}}
Без markdown.
"""

    def _parse(self, raw):
        if not raw:
            return {
                "ok": True,
                "issue": None,
                "reason": "Судья не ответил — пропуск.",
            }

        text = str(raw).strip()

        start = text.find("{")
        end = text.rfind("}")

        if start < 0 or end < start:
            return {
                "ok": True,
                "issue": None,
                "reason": "Судья не вернул JSON — пропуск.",
            }

        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {
                "ok": True,
                "issue": None,
                "reason": "Судья не вернул JSON — пропуск.",
            }

        if not isinstance(data, dict):
            return {
                "ok": True,
                "issue": None,
                "reason": "Некорректный ответ судьи.",
            }

        ok = bool(
            data.get("ok", True)
        )

        issue = data.get("issue")

        if issue not in {
            "evasion",
            "fabrication",
            "empty",
        }:
            issue = None

        return {
            "ok": ok and issue is None,
            "issue": issue,
            "reason": str(
                data.get("reason", "") or ""
            ),
        }
