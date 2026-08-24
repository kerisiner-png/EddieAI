import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedClaim:
    owner: str
    predicate: str
    value: str | None
    polarity: str
    certainty: str
    temporal_scope: str
    text: str


class SemanticClaimExtractor:
    """
    Преобразует естественный язык в универсальные claims.

    ВАЖНО:
        этот слой НЕ проверяет истинность утверждений.

    Его задача:
        text
        ↓
        structured claims

    Проверка выполняется отдельно через ClaimEngine.
    """

    SYSTEM_PROMPT = """
Ты — semantic claim extractor для автономного цифрового агента EddieAI.

Твоя задача — НЕ отвечать пользователю и НЕ оценивать истинность.

Только извлеки утверждения из текста.

Для каждого claim определи:

owner:
    SELF
    USER
    EXTERNAL
    SHARED
    UNKNOWN

predicate:
    краткий универсальный предикат в snake_case.
    Не используй конкретные названия свойств системы.
    Примеры:
        has_interest
        has_preference
        has_goal
        believes
        watched
        used
        has_capability
        has_access
        experienced
        knows
        relationship_with
        emotional_state

value:
    конкретный объект/значение утверждения.
    null, если его невозможно определить.

polarity:
    POSITIVE
    NEGATIVE
    UNKNOWN

certainty:
    HIGH
    MEDIUM
    LOW
    UNKNOWN

temporal_scope:
    PAST
    CURRENT
    FUTURE
    DURATIVE
    UNKNOWN

text:
    исходное предложение claim.

Особенно важно:
- «кажется», «вроде», «не уверен», «может быть» → LOW;
- прямое утверждение → HIGH;
- вопрос не является claim;
- просьба не является claim;
- не добавляй фактов, которых нет в исходном тексте;
- не делай выводов о сознании или чувствах, которых нет явно;
- один ответ может содержать несколько claims.

Верни ТОЛЬКО JSON-массив.
Без markdown.
Без объяснений.
"""

    def __init__(
        self,
        *,
        model,
        chat_function,
    ):
        self.model = model
        self.chat = chat_function

    def extract(
        self,
        text: str,
    ) -> list[ExtractedClaim]:

        normalized = str(text).strip()

        if not normalized:
            return []

        response = self.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": normalized,
                },
            ],
            options={
                "temperature": 0.0,
                "num_ctx": 2048,
                "num_predict": 512,
            },
            think=False,
        )

        raw = (
            response["message"]["content"]
            .strip()
        )

        data = self._parse_json(raw)

        claims = []

        for item in data:
            if not isinstance(item, dict):
                continue

            claims.append(
                ExtractedClaim(
                    owner=self._normalize_enum(
                        item.get("owner"),
                        {
                            "SELF",
                            "USER",
                            "EXTERNAL",
                            "SHARED",
                            "UNKNOWN",
                        },
                        "UNKNOWN",
                    ),
                    predicate=self._normalize_predicate(
                        item.get("predicate")
                    ),
                    value=self._normalize_value(
                        item.get("value")
                    ),
                    polarity=self._normalize_enum(
                        item.get("polarity"),
                        {
                            "POSITIVE",
                            "NEGATIVE",
                            "UNKNOWN",
                        },
                        "UNKNOWN",
                    ),
                    certainty=self._normalize_enum(
                        item.get("certainty"),
                        {
                            "HIGH",
                            "MEDIUM",
                            "LOW",
                            "UNKNOWN",
                        },
                        "UNKNOWN",
                    ),
                    temporal_scope=self._normalize_enum(
                        item.get("temporal_scope"),
                        {
                            "PAST",
                            "CURRENT",
                            "FUTURE",
                            "DURATIVE",
                            "UNKNOWN",
                        },
                        "UNKNOWN",
                    ),
                    text=str(
                        item.get("text")
                        or normalized
                    ).strip(),
                )
            )

        return claims

    @staticmethod
    def _parse_json(
        raw: str,
    ) -> list:

        cleaned = raw.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            if isinstance(
                data.get("claims"),
                list,
            ):
                return data["claims"]

        return []

    @staticmethod
    def _normalize_enum(
        value,
        allowed: set[str],
        fallback: str,
    ) -> str:

        value = str(
            value or ""
        ).strip().upper()

        return (
            value
            if value in allowed
            else fallback
        )

    @staticmethod
    def _normalize_predicate(
        value,
    ) -> str:

        value = str(
            value or "unknown"
        ).strip().casefold()

        value = re.sub(
            r"[^a-zа-я0-9_]+",
            "_",
            value,
        )

        value = re.sub(
            r"_+",
            "_",
            value,
        )

        return value.strip("_") or "unknown"

    @staticmethod
    def _normalize_value(
        value,
    ) -> str | None:

        if value is None:
            return None

        value = str(
            value
        ).strip()

        return value or None
