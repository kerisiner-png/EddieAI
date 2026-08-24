from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LexicalClaim:
    subject: str
    predicate: str
    value: str | None
    polarity: str
    certainty: str
    temporal_scope: str
    text: str


class ClaimLexicalExtractor:
    """
    Детерминированный extractor очевидных SELF-claim-конструкций.

    Не определяет истинность.
    Не вызывает LLM.
    Не извлекает утверждения о сторонних субъектах.

    Vocabulary predicates берётся из PredicateRegistry.
    """

    SELF_MARKERS = (
        "я ",
        "мне ",
        "у меня ",
        "мой ",
        "моя ",
        "мои ",
    )

    def __init__(
        self,
        predicate_registry,
    ):
        self.registry = predicate_registry

    def extract(
        self,
        text: str,
        *,
        implicit_self: bool = False,
    ) -> list[LexicalClaim]:

        normalized = self._normalize(
            text
        )

        if not normalized:
            return []

        claims = []

        for sentence in self._split_sentences(
            normalized
        ):

            if (
                not implicit_self
                and not self._is_explicit_self(
                    sentence
                )
            ):
                continue

            for spec in self.registry.all():

                negative_pattern = (
                    self._first_match(
                        sentence,
                        spec.negative_patterns,
                    )
                )

                if negative_pattern is not None:
                    value = self._extract_value(
                        sentence,
                        negative_pattern,
                        spec.name,
                    )

                    claims.append(
                        LexicalClaim(
                            subject="я",
                            predicate=spec.name,
                            value=value,
                            polarity="NEGATIVE",
                            certainty="HIGH",
                            temporal_scope=(
                                self._infer_temporal_scope(
                                    sentence,
                                    spec.name,
                                )
                            ),
                            text=sentence,
                        )
                    )

                    continue

                positive_pattern = (
                    self._first_match(
                        sentence,
                        spec.surface_patterns,
                    )
                )

                if positive_pattern is None:
                    continue

                value = self._extract_value(
                    sentence,
                    positive_pattern,
                    spec.name,
                )

                claims.append(
                    LexicalClaim(
                        subject="я",
                        predicate=spec.name,
                        value=value,
                        polarity="POSITIVE",
                        certainty="HIGH",
                        temporal_scope=(
                            self._infer_temporal_scope(
                                sentence,
                                spec.name,
                            )
                        ),
                        text=sentence,
                    )
                )

        return claims

    @staticmethod
    def _is_explicit_self(
        sentence: str,
    ) -> bool:

        markers = (
            "я ",
            "мне ",
            "у меня ",
            "мой ",
            "моя ",
            "мои ",
        )

        normalized = (
            " "
            + sentence
        )

        return any(
            (
                f" {marker}" in normalized
                or normalized.startswith(
                    marker
                )
            )
            for marker in markers
        )

    @staticmethod
    def _first_match(
        sentence: str,
        patterns: tuple[str, ...],
    ) -> str | None:

        for pattern in patterns:
            index = sentence.find(
                pattern
            )

            if index < 0:
                continue

            if index > 0:
                previous = sentence[
                    index - 1
                ]

                if previous.isalnum():
                    continue

            return pattern

        return None

    @staticmethod
    def _extract_value(
        sentence: str,
        pattern: str,
        predicate: str,
    ) -> str | None:

        index = sentence.find(
            pattern
        )

        if index < 0:
            return None

        value = sentence[
            index + len(pattern):
        ].strip(
            " .,!?:;—-"
        )

        if not value:
            return None

        # Останавливаемся на явной границе
        # следующего утверждения.
        boundaries = (
            ", но ",
            ", но,",
            " но ",
            ", однако ",
            ", однако,",
            " однако ",
            ", зато ",
            " зато ",
            ";",
        )

        lower_value = value.casefold()

        boundary_positions = [
            lower_value.find(
                boundary
            )
            for boundary in boundaries
            if lower_value.find(
                boundary
            ) >= 0
        ]

        if boundary_positions:
            value = value[
                :min(
                    boundary_positions
                )
            ].strip(
                " .,!?:;—-"
            )

        value = value.removeprefix(
            "напрямую "
        ).strip()

        if predicate == "has_interest":
            value = value.removeprefix(
                "к "
            ).strip()

        return value or None


    @staticmethod
    def _infer_temporal_scope(
        sentence: str,
        predicate: str,
    ) -> str:

        if any(
            marker in sentence
            for marker in (
                "когда-то ",
                "раньше ",
                "ранее ",
                "в прошлом ",
                "прежде ",
            )
        ):
            return "PAST"

        if any(
            marker in sentence
            for marker in (
                "буду ",
                "будущее ",
                "планирую ",
            )
        ):
            return "FUTURE"

        return "CURRENT"

    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:

        parts = re.split(
            r"(?<=[.!?])\s+",
            text,
        )

        return [
            item.strip()
            for item in parts
            if item.strip()
        ]

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
