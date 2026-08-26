import json


from memory.knowledge import Knowledge


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 384,
    "temperature": 0.3,
}


class SelfInterpretation:
    def __init__(
        self,
        memory,
        model_orchestrator=None,
    ):
        from identity.llm_access import (
            CloudFirstLlm,
        )

        self.memory = memory
        self.llm = CloudFirstLlm(
            model_orchestrator
        )

    def interpret(
        self,
        query: str,
        limit: int = 5,
    ):
        sources = self._get_external_sources(
            query,
            limit,
        )

        if not sources:
            return {
                "status": "NO_SOURCES",
                "sources": [],
                "interpretation": None,
            }

        source_text = "\n\n".join(
            (
                f"SOURCE {index + 1}\n"
                f"{source['content']}\n"
                f"URL: {source['source']}"
            )
            for index, source in enumerate(
                sources
            )
        )

        prompt = f"""
Ты выполняешь внутренний анализ внешних источников.

Запрос:
{query}

Внешние источники:

{source_text}

Определи:
1. Что подтверждается несколькими источниками.
2. Что недостаточно подтверждено.
3. Есть ли противоречия.
4. Какой осторожный вывод можно сделать.

Не придумывай факты.
Не выдавай собственный вывод за подтверждённый факт.

Верни только JSON-объект:

{{
  "conclusion": "...",
  "confidence": 0.0,
  "supported_by": ["url1"],
  "contradictions": [],
  "limitations": []
}}
"""

        raw = self.llm.chat(
            system=(
                "Сравнивай источники строго "
                "по предоставленным данным. "
                "Верни только JSON."
            ),
            user=prompt,
            options=MODEL_OPTIONS,
            task="deep",
        )

        parsed = self._parse(raw)

        if parsed is None:
            return {
                "status": "INVALID_MODEL_OUTPUT",
                "sources": sources,
                "interpretation": None,
            }

        conclusion = str(
            parsed.get(
                "conclusion",
                "",
            )
        ).strip()

        if not conclusion:
            return {
                "status": "EMPTY_CONCLUSION",
                "sources": sources,
                "interpretation": None,
            }

        confidence = self._confidence(
            parsed.get(
                "confidence",
                0.0,
            )
        )

        supported_by = [
            str(item)
            for item in parsed.get(
                "supported_by",
                [],
            )
        ]

        contradictions = [
            str(item)
            for item in parsed.get(
                "contradictions",
                [],
            )
        ]

        limitations = [
            str(item)
            for item in parsed.get(
                "limitations",
                [],
            )
        ]

        content = (
            f"Мой вывод по запросу "
            f"'{query}': {conclusion}"
        )

        if contradictions:
            content += (
                " Противоречия: "
                + "; ".join(
                    contradictions
                )
            )

        if limitations:
            content += (
                " Ограничения: "
                + "; ".join(
                    limitations
                )
            )

        knowledge = Knowledge(
            content=content,
            owner="SELF",
            source_type="SELF_INTERPRETATION",
            source=(
                ", ".join(supported_by)
                if supported_by
                else "external_sources"
            ),
            confidence=confidence,
            verified=False,
            personal_experience=False,
        )

        self.memory.remember_knowledge(
            knowledge
        )

        return {
            "status": "OK",
            "sources": sources,
            "interpretation": {
                "content": content,
                "confidence": confidence,
                "supported_by": supported_by,
                "contradictions": contradictions,
                "limitations": limitations,
            },
        }

    def _get_external_sources(
        self,
        query: str,
        limit: int,
    ):
        rows = self.memory.connection.execute("""
            SELECT
                content,
                source,
                confidence,
                verified
            FROM knowledge
            WHERE owner = 'EXTERNAL'
              AND source_type = 'WEB_SEARCH'
              AND content LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (
            f"%{query}%",
            limit,
        )).fetchall()

        return [
            {
                "content": row["content"],
                "source": row["source"],
                "confidence": row["confidence"],
                "verified": bool(
                    row["verified"]
                ),
            }
            for row in rows
        ]

    def _parse(self, raw: str):
        text = raw.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if (
                lines
                and lines[0]
                .strip()
                .lower()
                in {
                    "```json",
                    "```",
                }
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip()
                == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)

            if isinstance(data, dict):
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

                if isinstance(data, dict):
                    return data

            except json.JSONDecodeError:
                pass

        return None

    def _confidence(self, value):
        try:
            value = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0.2

        return max(
            0.0,
            min(1.0, value),
        )
