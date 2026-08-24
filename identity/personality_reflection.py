import json

from ollama import chat


MODEL_NAME = "phi4-mini"

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

    def analyze(self, candidates):
        if not candidates:
            return []

        candidate_data = []

        for candidate in candidates:
            candidate_data.append({
                "field": candidate.field,
                "value": candidate.value,
                "category": candidate.category,
                "strength": candidate.strength,
                "weighted_score": candidate.weighted_score,
                "evidence_count": candidate.evidence_count,
                "source_types": candidate.source_types,
            })

        prompt = f"""
Ты выполняешь внутреннюю рефлексию личности.

Ниже находятся кандидаты на устойчивые свойства
твоей личности.

КАНДИДАТЫ:

{json.dumps(candidate_data, ensure_ascii=False, indent=2)}

Текущее состояние личности:

{json.dumps(
    self.agent.self_state.snapshot(),
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

        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты выполняешь внутреннюю "
                        "рефлексию личности. "
                        "Верни только JSON."
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

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(result, list):
            return []

        return result
