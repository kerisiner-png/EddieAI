import json

from identity.llm_access import CloudFirstLlm


JUDGE_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 80,
    "temperature": 0.0,
}

REGEN_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 200,
    "temperature": 0.4,
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
        life_context="",
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
                life_context,
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

    def regenerate(
        self,
        user_message,
        answer,
        verdict,
        life_context="",
    ):
        if not self.enabled:
            return None

        if not answer:
            return None

        issue = verdict.get("issue")

        if issue not in {
            "evasion",
            "fabrication",
        }:
            return None

        reason = verdict.get("reason") or ""

        prompt = (
            self._regenerate_prompt(
                user_message,
                answer,
                issue,
                reason,
                life_context,
            )
        )

        raw = self.llm.chat(
            system=(
                "Ты — EddieAI, цифровая личность. "
                "Отвечай честно и по сути вопроса, "
                "не выдумывая фактов."
            ),
            user=prompt,
            options=REGEN_OPTIONS,
            task="conversation",
        )

        if raw and raw.strip():
            return raw.strip()

        return None

    def _regenerate_prompt(
        self,
        user_message,
        answer,
        issue,
        reason,
        life_context="",
    ):
        life_section = ""

        if life_context:
            life_section = (
                "\n\nРеальные недавние факты "
                "из жизни EddieAI:\n"
                + life_context
                + "\n\nЕсли детали берутся из этих "
                "фактов — это не выдумка."
            )

        return f"""
Сообщение пользователя:
{user_message}

Прежний ответ содержал проблему:
{issue} — {reason}

Прежний ответ:
{answer}

Перепиши ответ: не уклоняйся от сути вопроса
и не выдумывай фактов, деятельности или биографии.
Отвечай честно и по существу.
{life_section}

Только новый ответ, без пояснений.
"""

    def _prompt(
        self,
        user_message,
        answer,
        life_context="",
    ):
        life_section = ""

        if life_context:
            life_section = (
                "\n\nРеальные недавние факты "
                "из жизни EddieAI:\n"
                + life_context
                + "\n\nEddieAI живёт между сообщениями: "
                "его действия, события и результаты "
                "реальны. Если детали ответа совпадают "
                "с этими фактами — это не выдумка."
            )

        return f"""
Сообщение пользователя:
{user_message}

Ответ EddieAI:
{answer}
{life_section}

Определи одну из трёх проблем, если она есть:
- evasion — ответ уклоняется от сути вопроса,
  отвечает не на то, что спрошено;
- fabrication — ответ выдумывает факты,
  деятельность, события или биографию,
  которых нет ни во входных данных,
  ни в реальных фактах выше;
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
