import json

from identity.llm_access import CloudFirstLlm


MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 256,
    "temperature": 0.5,
}


class PersonalityReflection:
    """
    Отдельная рефлексия над кандидатами личности.

    LLM анализирует кандидата и формулирует объяснение.
    Она НЕ получает права самостоятельно менять self_state.
    """

    def __init__(self, agent):
        self.agent = agent
        self.llm = CloudFirstLlm(
            getattr(
                agent,
                "model_orchestrator",
                None,
            )
        )

    def analyze(self, candidates):
        if not candidates:
            return []

        candidate_data = []

        for candidate in candidates:
            candidate_data.append({
                "field": getattr(candidate, "field", ""),
                "value": getattr(candidate, "value", ""),
                "category": getattr(candidate, "category", ""),
                "strength": getattr(candidate, "strength", 0.0),
                "weighted_score": getattr(candidate, "weighted_score", 0.0),
                "evidence_count": getattr(candidate, "evidence_count", 0),
                "source_types": getattr(candidate, "source_types", []),
            })

        state = self.agent.self_state
        snapshot = state.snapshot() if hasattr(state, "snapshot") else {}

        safe_keys = {"age", "values", "interests", "beliefs"}
        safe_state = {k: v for k, v in snapshot.items() if k in safe_keys}

        prompt = f"""
Ты выполняешь внутреннюю рефлексию личности.

Ниже находятся кандидаты на устойчивые свойства
твоей личности.

КАНДИДАТЫ:

{json.dumps(candidate_data, ensure_ascii=False, indent=2)}

Текущее состояние личности (сокращённое):

{json.dumps(
    safe_state,
    ensure_ascii=False,
    indent=2,
)}

Для каждого кандидата оцени:

1. Насколько он действительно похож на устойчивую
   черту личности.
2. Есть ли достаточное основание продолжать
   наблюдение.
3. Есть ли признаки того, что это случайная
   или контекстная реакция.

ВАЖНО:

- Не придумывай отсутствующий опыт.
- Не создавай новые факты.
- Не меняй состояние личности.
- Не выбирай имя, интерес или убеждение
  только потому, что оно звучит красиво.
- Оценивай только предоставленные кандидаты.

Верни ТОЛЬКО JSON:

[
  {{
    "field": "interest",
    "value": "пример",
    "assessment": "strong|moderate|weak",
    "reason": "краткое объяснение"
  }}
]

Без markdown.
Без дополнительного текста.
"""

        try:
            raw = self.llm.chat(
                system=(
                    "Ты выполняешь внутреннюю "
                    "рефлексию личности. "
                    "Верни только JSON."
                ),
                user=prompt,
                options=MODEL_OPTIONS,
                task="reflection",
            )
        except Exception:
            return []

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(result, list):
            return []

        return result
