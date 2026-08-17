from json import JSONDecodeError
import json

from ollama import chat

from identity.proposal import Proposal


class SelfReflection:
    MODEL_NAME = "phi4-mini"

    def __init__(self, agent):
        self.agent = agent

    def reflect(
        self,
        user_message: str,
        agent_response: str,
        memory_context: str,
    ) -> dict:

        current_state = self.agent.self_state.snapshot()

        identity_context = (
            self.agent.build_identity_context()
        )

        prompt = f"""
Ты выполняешь отдельную внутреннюю процедуру самоанализа
автономной цифровой личности.

Это НЕ обычный ответ пользователю.
Это структурированный анализ опыта.

СУБЪЕКТЫ ИДЕНТИЧНОСТИ:
{json.dumps(
    identity_context,
    ensure_ascii=False,
    indent=2,
)}

КРИТИЧЕСКИЕ ПРАВИЛА:
- SELF и USER — разные сущности.
- SELF — EddieAI.
- USER/CREATOR — Эдди.
- Факты о USER нельзя записывать как факты о SELF.
- Факты о SELF нельзя записывать как факты о USER.
- Имя "Эдди" относится к USER/CREATOR,
  если явно не доказано обратное.
- Возраст Эдди не является возрастом EddieAI.
- Не выдумывай отсутствующие факты.
- Не изменяй identity напрямую.

ТЕКУЩАЯ ИДЕНТИЧНОСТЬ SELF:
{json.dumps(
    current_state,
    ensure_ascii=False,
    indent=2,
)}

НЕДАВНИЙ КОНТЕКСТ ПАМЯТИ:
{memory_context}

СООБЩЕНИЕ ЭДДИ:
{user_message}

ОТВЕТ АГЕНТА:
{agent_response}

Классифицируй результаты отдельно:

1. observations:
   нейтральные наблюдения о произошедшем.

2. self_knowledge:
   только сведения о самом EddieAI.

3. user_knowledge:
   только сведения об Эдди.

4. proposals:
   только кандидаты на изменение личности EddieAI.

5. reflection:
   краткий общий вывод.

ВАЖНО:
"Эдди 22 года" -> user_knowledge.
"Я интересуюсь космосом" -> self_knowledge.
Не переносить свойства между субъектами.

Верни ТОЛЬКО валидный JSON:

{{
  "observations": [],
  "self_knowledge": [],
  "user_knowledge": [],
  "proposals": [],
  "reflection": ""
}}

Не добавляй markdown.
Не добавляй текст вне JSON.
"""

        response = chat(
            model=self.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты выполняешь внутреннюю "
                        "структурированную рефлексию. "
                        "Строго различай SELF и USER. "
                        "Возвращай только JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        raw = (
            response["message"]["content"]
            .strip()
        )

        data = self._parse_json(raw)

        if data is None:
            return self._empty_result(
                "Не удалось разобрать результат самоанализа."
            )

        return self._validate(data)

    def _empty_result(
        self,
        reflection="",
    ):
        return {
            "observations": [],
            "self_knowledge": [],
            "user_knowledge": [],
            "proposals": [],
            "reflection": reflection,
        }

    def _parse_json(self, raw: str):
        if not isinstance(raw, str):
            return None

        raw = raw.strip()

        if not raw:
            return None

        try:
            return json.loads(raw)
        except JSONDecodeError:
            pass

        cleaned = raw

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip()
                == "```"
            ):
                lines = lines[:-1]

            cleaned = "\n".join(
                lines
            ).strip()

            if cleaned.startswith("json"):
                cleaned = cleaned[4:].lstrip()

            try:
                return json.loads(cleaned)
            except JSONDecodeError:
                pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end <= start:
            return None

        candidate = cleaned[
            start:end + 1
        ]

        try:
            return json.loads(candidate)
        except JSONDecodeError:
            return None

    def _validate(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return self._empty_result()

        observations = data.get(
            "observations",
            [],
        )

        self_knowledge = data.get(
            "self_knowledge",
            [],
        )

        user_knowledge = data.get(
            "user_knowledge",
            [],
        )

        proposals_data = data.get(
            "proposals",
            [],
        )

        reflection = data.get(
            "reflection",
            "",
        )

        if not isinstance(
            observations,
            list,
        ):
            observations = []

        if not isinstance(
            self_knowledge,
            list,
        ):
            self_knowledge = []

        if not isinstance(
            user_knowledge,
            list,
        ):
            user_knowledge = []

        proposals = []

        if isinstance(
            proposals_data,
            list,
        ):
            for item in proposals_data:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                proposal_type = item.get(
                    "proposal_type"
                )

                value = item.get(
                    "value"
                )

                reason = item.get(
                    "reason"
                )

                confidence = item.get(
                    "confidence",
                    0.0,
                )

                evidence = item.get(
                    "evidence",
                    [],
                )

                if not isinstance(
                    proposal_type,
                    str,
                ):
                    continue

                if not isinstance(
                    reason,
                    str,
                ):
                    continue

                if not isinstance(
                    evidence,
                    list,
                ):
                    evidence = []

                try:
                    confidence = float(
                        confidence
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    confidence = 0.0

                confidence = max(
                    0.0,
                    min(
                        1.0,
                        confidence,
                    ),
                )

                proposals.append(
                    Proposal(
                        proposal_type=proposal_type,
                        value=value,
                        reason=reason,
                        confidence=confidence,
                        evidence=evidence,
                    )
                )

        (
            self_knowledge,
            user_knowledge,
        ) = self._apply_ownership_guard(
            self_knowledge,
            user_knowledge,
        )

        return {
            "observations": observations,
            "self_knowledge": self_knowledge,
            "user_knowledge": user_knowledge,
            "proposals": proposals,
            "reflection": (
                reflection
                if isinstance(
                    reflection,
                    str,
                )
                else ""
            ),
        }

    def _apply_ownership_guard(
        self,
        self_knowledge,
        user_knowledge,
    ):
        """
        LLM cannot override known ownership.

        Explicit user facts remain user facts.
        They cannot become self-knowledge merely
        because the model classified them that way.
        """

        protected_user_knowledge = []
        filtered_self_knowledge = []

        user_markers = [
            "????",
            "??? ",
            "??? ",
            "??? ",
            "??? ",
            "? ?????",
            "??? ????????",
            "??? ????? ????????",
            "??? ?????????",
        ]

        for item in user_knowledge:
            if isinstance(item, str):
                protected_user_knowledge.append(
                    item
                )

        for item in self_knowledge:
            if not isinstance(item, str):
                continue

            normalized = item.strip().lower()

            is_user_fact = any(
                marker in normalized
                for marker in user_markers
            )

            if is_user_fact:
                protected_user_knowledge.append(
                    item
                )
            else:
                filtered_self_knowledge.append(
                    item
                )

        return (
            filtered_self_knowledge,
            protected_user_knowledge,
        )
