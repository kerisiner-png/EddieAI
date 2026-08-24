from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SelfClaimTriageResult:
    potential_self_claim: bool
    reasons: tuple[str, ...]


class SelfClaimTriage:
    """
    Дешёвый предварительный фильтр.

    НЕ определяет:
        - истинность;
        - predicate;
        - value;
        - ownership окончательно.

    Только отвечает:
        "Есть ли в ответе признаки утверждения
         о самом EddieAI?"
    """

    EXPLICIT_SELF_PATTERNS = (
        r"(?<!\w)я(?!\w)",
        r"(?<!\w)мне(?!\w)",
        r"(?<!\w)меня(?!\w)",
        r"(?<!\w)мой(?!\w)",
        r"(?<!\w)моя(?!\w)",
        r"(?<!\w)мои(?!\w)",
        r"у меня",
        r"для меня",
        r"со мной",
    )

    SELF_CAPABILITY_PATTERNS = (
        r"\bя\s+(?:могу|умею|способен|способна)\b",
        r"\bя\s+(?:не\s+могу|не\s+умею)\b",
    )

    SELF_EXPERIENCE_PATTERNS = (
        r"\bя\s+(?:смотрел|смотрела|читал|читала)\b",
        r"\bя\s+(?:использовал|использовала)\b",
        r"\bя\s+(?:делал|делала|пробовал|пробовала)\b",
        r"\bя\s+(?:видел|видела)\b",
    )

    SELF_STATE_PATTERNS = (
        r"\bмне\s+(?:интересно|нравится|важно)\b",
        r"\bя\s+(?:интересуюсь|люблю|предпочитаю)\b",
        r"\bу меня\s+есть\b",
        r"\bу меня\s+нет\b",
        r"\bя\s+(?:хочу|стремлюсь|считаю|верю)\b",
    )

    def analyze(
        self,
        text: str,
    ) -> SelfClaimTriageResult:

        normalized = self._normalize(text)

        if not normalized:
            return SelfClaimTriageResult(
                potential_self_claim=False,
                reasons=(),
            )

        reasons = []

        if self._matches_any(
            normalized,
            self.EXPLICIT_SELF_PATTERNS,
        ):
            reasons.append(
                "EXPLICIT_SELF_REFERENCE"
            )

        if self._matches_any(
            normalized,
            self.SELF_CAPABILITY_PATTERNS,
        ):
            reasons.append(
                "SELF_CAPABILITY"
            )

        if self._matches_any(
            normalized,
            self.SELF_EXPERIENCE_PATTERNS,
        ):
            reasons.append(
                "SELF_EXPERIENCE"
            )

        if self._matches_any(
            normalized,
            self.SELF_STATE_PATTERNS,
        ):
            reasons.append(
                "SELF_STATE"
            )

        return SelfClaimTriageResult(
            potential_self_claim=bool(reasons),
            reasons=tuple(
                dict.fromkeys(reasons)
            ),
        )

    @staticmethod
    def _matches_any(
        text: str,
        patterns: tuple[str, ...],
    ) -> bool:

        return any(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        return (
            " ".join(
                str(text)
                .casefold()
                .replace("ё", "е")
                .split()
            )
        )
