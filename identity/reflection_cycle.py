import json

from ollama import chat


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 512,
    "temperature": 0.2,
}


class ReflectionCycle:
    """
    Единый когнитивный цикл рефлексии.

    LLM только оценивает уже существующие
    personality candidates.

    LLM не имеет права создавать новые
    identity fields или изменять self_state.
    """

    def __init__(self, agent):
        self.agent = agent

    def run_snapshot(
        self,
        snapshot: dict,
    ):
        """
        Reflection безопасная для worker-thread.

        Использует только сериализованный snapshot.
        Не обращается к SQLite, self_state или другим
        thread-bound объектам Agent.
        """

        self_state = snapshot.get(
            "self_state",
            {},
        )

        candidates = snapshot.get(
            "candidates",
            [],
        )

        if not isinstance(candidates, list):
            candidates = []

        if not candidates:
            return {
                "candidate_decisions": [],
            }

        prompt = f"""
Ты выполняешь внутреннюю рефлексию личности EddieAI.

Твоя задача — ТОЛЬКО оценить уже существующие
кандидаты личности.

Ты НЕ МОЖЕШЬ создавать новые кандидаты.

ТЕКУЩЕЕ СОСТОЯНИЕ SELF:

{json.dumps(self_state, ensure_ascii=False, indent=2)}

КАНДИДАТЫ:

{json.dumps(candidates, ensure_ascii=False, indent=2)}

Для каждого кандидата выбери:
"promote", "defer" или "reject".

Не создавай новых полей.
Не придумывай факты.
Не изменяй self_state.

Верни ТОЛЬКО JSON:
{{
  "candidate_decisions": [
    {{
      "field": "точное поле",
      "value": "точное значение",
      "decision": "promote",
      "reason": "краткая причина"
    }}
  ]
}}
"""

        cloud_content = (
            self.agent.model_orchestrator
            ._cloud_chat(
                system=(
                    "Ты выполняешь внутренний "
                    "reflection cycle. "
                    "Оценивай только предоставленные "
                    "кандидаты. Возвращай только JSON."
                ),
                user=prompt,
                options={
                    "temperature": 0.2,
                    "num_predict": 512,
                    "response_format": {
                        "type": "json_object"
                    },
                },
                task="reflection",
            )
        )

        if cloud_content is not None:

            raw = cloud_content

        else:

            orchestrator = (
                self.agent.model_orchestrator
            )

            free_gb = (
                orchestrator.available_ram_gb()
            )

            need_gb = (
                orchestrator.MODEL_RAM_GB.get(
                    "phi4-mini:latest"
                )
            )

            if (
                need_gb is not None
                and free_gb < need_gb
            ):
                print(
                    "[reflection] мало RAM для "
                    f"локального анализа "
                    f"({free_gb:.1f} GB), "
                    "решения по кандидатам "
                    "переносятся"
                )

                return {
                    "candidate_decisions": [],
                }

            response = chat(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты выполняешь внутренний "
                            "reflection cycle. "
                            "Оценивай только предоставленные "
                            "кандидаты. "
                            "Возвращай только JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                options=MODEL_OPTIONS,
                format="json",
                keep_alive="3m",
            )

            raw = (
                response["message"]["content"]
                .strip()
            )

        result = self._parse_json(raw)

        if not isinstance(result, dict):
            return {
                "candidate_decisions": [],
            }

        candidate_decisions = result.get(
            "candidate_decisions",
            [],
        )

        if not isinstance(candidate_decisions, list):
            candidate_decisions = []

        valid_candidates = {
            (
                str(item.get("field")),
                str(item.get("value")),
            )
            for item in candidates
        }

        filtered = []

        for item in candidate_decisions:
            if not isinstance(item, dict):
                continue

            field = item.get("field")
            value = item.get("value")
            decision = item.get("decision")
            reason = item.get("reason", "")

            if field is None or value is None:
                continue

            key = (
                str(field),
                str(value),
            )

            if key not in valid_candidates:
                continue

            if decision not in {
                "promote",
                "defer",
                "reject",
            }:
                continue

            filtered.append({
                "field": str(field),
                "value": str(value),
                "decision": decision,
                "reason": str(reason),
            })

        return {
            "candidate_decisions": filtered,
        }

    def run(self):
        memory_context = (
            self.agent.memory_manager.build_context(
                limit=20
            )
        )

        candidates = (
            self.agent.personality.candidates(
                self_state=self.agent.self_state
            )
        )

        candidate_data = [
            {
                "field": item.field,
                "value": item.value,
                "category": item.category,
                "strength": item.strength,
                "weighted_score": item.weighted_score,
                "evidence_count": item.evidence_count,
                "source_types": item.source_types,
            }
            for item in candidates
        ]

        self_state = (
            self.agent.self_state.snapshot()
        )

        prompt = f"""
Ты выполняешь внутреннюю рефлексию личности EddieAI.

Твоя задача — ТОЛЬКО оценить уже существующие
кандидаты личности.

ТЫ НЕ МОЖЕШЬ СОЗДАВАТЬ НОВЫЕ КАНДИДАТЫ.

ТЕКУЩЕЕ СОСТОЯНИЕ SELF:

{json.dumps(
    self_state,
    ensure_ascii=False,
    indent=2,
)}

КАНДИДАТЫ, КОТОРЫЕ РАЗРЕШЕНО ОЦЕНИВАТЬ:

{json.dumps(
    candidate_data,
    ensure_ascii=False,
    indent=2,
)}

Для КАЖДОГО переданного кандидата выбери:

"promote" — кандидат достаточно подтверждён;
"defer" — нужно больше наблюдений;
"reject" — кандидат недостаточно обоснован.

КРИТИЧЕСКИЕ ПРАВИЛА:

- Используй только кандидатов из списка выше.
- Не добавляй age.
- Не добавляй gender.
- Не добавляй name.
- Не добавляй values.
- Не добавляй interests, если их нет среди кандидатов.
- Не создавай новые personality fields.
- Не изменяй self_state.
- Не придумывай отсутствующие факты.

Верни JSON следующего вида:

{{
  "candidate_decisions": [
    {{
      "field": "точное поле кандидата",
      "value": "точное значение кандидата",
      "decision": "promote",
      "reason": "краткая причина"
    }}
  ]
}}

Если кандидатов нет:

{{
  "candidate_decisions": []
}}
"""

        cloud_content = (
            self.agent.model_orchestrator
            ._cloud_chat(
                system=(
                    "Ты выполняешь внутренний "
                    "reflection cycle. "
                    "Оценивай только предоставленные "
                    "кандидаты. "
                    "Возвращай только JSON."
                ),
                user=prompt,
                options={
                    "temperature": 0.2,
                    "num_predict": 512,
                    "response_format": {
                        "type": "json_object"
                    },
                },
                task="reflection",
            )
        )

        if cloud_content is not None:
            raw = cloud_content.strip()
        else:
            response = chat(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты выполняешь внутренний "
                            "reflection cycle. "
                            "Оценивай только предоставленные "
                            "кандидаты. "
                            "Возвращай только JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                options=MODEL_OPTIONS,
                format="json",
                keep_alive="3m",
            )

            raw = (
                response["message"]["content"]
                .strip()
            )

        result = self._parse_json(raw)

        if result is None:
            result = {
                "candidate_decisions": [],
            }

        if not isinstance(result, dict):
            result = {
                "candidate_decisions": [],
            }

        candidate_decisions = (
            result.get(
                "candidate_decisions",
                [],
            )
        )

        if not isinstance(
            candidate_decisions,
            list,
        ):
            candidate_decisions = []

        valid_candidates = {
            (
                candidate.field,
                str(candidate.value),
            )
            for candidate in candidates
        }

        filtered_decisions = []

        for item in candidate_decisions:
            if not isinstance(item, dict):
                continue

            field = item.get("field")
            value = item.get("value")
            decision = item.get("decision")
            reason = item.get("reason", "")

            if not isinstance(field, str):
                continue

            if value is None:
                continue

            value_text = str(value)

            if (
                field,
                value_text,
            ) not in valid_candidates:
                continue

            if decision not in {
                "promote",
                "defer",
                "reject",
            }:
                continue

            if not isinstance(reason, str):
                reason = ""

            filtered_decisions.append(
                {
                    "field": field,
                    "value": value_text,
                    "decision": decision,
                    "reason": reason,
                }
            )

        return {
            "candidate_decisions": (
                filtered_decisions
            ),
        }

    def _parse_json(self, raw: str):
        if not isinstance(raw, str):
            return None

        raw = raw.strip()

        if not raw:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        if raw.startswith("```"):
            lines = raw.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            cleaned = "\n".join(
                lines
            ).strip()

            if cleaned.startswith("json"):
                cleaned = cleaned[4:].lstrip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        start = raw.find("{")
        end = raw.rfind("}")

        if start >= 0 and end > start:
            try:
                return json.loads(
                    raw[start:end + 1]
                )
            except json.JSONDecodeError:
                pass

        return None
