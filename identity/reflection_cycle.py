import json

from ollama import chat


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 384,
    "temperature": 0.5,
}


class ReflectionCycle:
    """
    Единый когнитивный цикл рефлексии.

    Один inference анализирует:
    - накопленный опыт;
    - наблюдения о себе;
    - кандидатов личности.

    LLM только предлагает оценку.
    Изменение self_state выполняется отдельно.
    """

    def __init__(self, agent):
        self.agent = agent

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
Ты выполняешь периодическую внутреннюю рефлексию
автономной цифровой личности.

НАКОПЛЕННЫЙ ОПЫТ

{memory_context}

ТЕКУЩЕЕ СОСТОЯНИЕ

{json.dumps(
    self_state,
    ensure_ascii=False,
    indent=2,
)}

КАНДИДАТЫ НА ФОРМИРОВАНИЕ ЛИЧНОСТИ

{json.dumps(
    candidate_data,
    ensure_ascii=False,
    indent=2,
)}

Проанализируй:

1. Какие события действительно значимы?
2. Есть ли повторяющиеся особенности?
3. Какие кандидаты выглядят устойчивыми?
4. Какие кандидаты пока лучше отложить?
5. Есть ли противоречия между новым опытом
   и текущим состоянием личности?

Не создавай новых фактов.
Не меняй состояние напрямую.

Для каждого кандидата используй:
"promote" — достаточно оснований;
"defer" — наблюдать дальше;
"reject" — считать недостаточно обоснованным.

Верни ТОЛЬКО JSON:

{{
  "observations": [],
  "self_knowledge": [],
  "candidate_decisions": [
    {{
      "field": "...",
      "value": "...",
      "decision": "promote|defer|reject",
      "reason": "..."
    }}
  ],
  "summary": "..."
}}

Без markdown.
"""

        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты выполняешь внутренний "
                        "reflection cycle. "
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

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {
                "observations": [],
                "self_knowledge": [],
                "candidate_decisions": [],
                "summary": "",
            }

        if not isinstance(result, dict):
            result = {
                "observations": [],
                "self_knowledge": [],
                "candidate_decisions": [],
                "summary": "",
            }

        result.setdefault(
            "observations",
            [],
        )
        result.setdefault(
            "self_knowledge",
            [],
        )
        result.setdefault(
            "candidate_decisions",
            [],
        )
        result.setdefault(
            "summary",
            "",
        )

        return result
