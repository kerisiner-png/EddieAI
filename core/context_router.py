import re
from dataclasses import dataclass


@dataclass
class ContextRoute:
    route: str
    confidence: float


class ContextRouter:
    """
    Определяет базовый контекст запроса до обращения к LLM.

    SELF_QUERY   -> пользователь спрашивает о EddieAI
    USER_QUERY   -> пользователь спрашивает о себе
    GENERAL_QUERY -> обычный разговор
    """

    SELF_PATTERNS = [
        r"\bрасскажи\s+о\s+себе\b",
        r"\bчто\s+ты\s+знаешь\s+о\s+себе\b",
        r"\bчто\s+ты\s+думаешь\s+о\s+себе\b",
        r"\bкто\s+ты\b",
        r"\bкакой\s+ты\b",
        r"\bчто\s+ты\s+любишь\b",
        r"\bчто\s+тебе\s+нравится\b",
        r"\bкакие\s+у\s+тебя\s+интересы\b",
        r"\bкакие\s+у\s+тебя\s+цели\b",
        r"\bчто\s+ты\s+чувствуешь\b",
    ]

    USER_PATTERNS = [
        r"\bрасскажи\s+обо\s+мне\b",
        r"\bчто\s+ты\s+знаешь\s+обо\s+мне\b",
        r"\bчто\s+ты\s+думаешь\s+обо\s+мне\b",
        r"\bкакой\s+я\b",
        r"\bчто\s+ты\s+знаешь\s+про\s+меня\b",
        r"\bчто\s+ты\s+помнишь\s+обо\s+мне\b",
    ]

    def route(self, text: str) -> ContextRoute:
        normalized = self._normalize(text)

        if self._matches(
            normalized,
            self.SELF_PATTERNS,
        ):
            return ContextRoute(
                route="SELF_QUERY",
                confidence=1.0,
            )

        if self._matches(
            normalized,
            self.USER_PATTERNS,
        ):
            return ContextRoute(
                route="USER_QUERY",
                confidence=1.0,
            )

        return ContextRoute(
            route="GENERAL_QUERY",
            confidence=1.0,
        )

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _matches(
        self,
        text: str,
        patterns: list[str],
    ) -> bool:
        return any(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
            for pattern in patterns
        )
