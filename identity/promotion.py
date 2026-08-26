from dataclasses import dataclass


@dataclass
class PromotionDecision:
    action: str
    field: str
    value: str
    confidence: float
    reason: str


class PromotionEngine:
    """
    Определяет, достаточно ли evidence,
    чтобы личностный кандидат мог быть предложен
    к принятию.

    Не изменяет self_state.
    """

    MIN_STRENGTH = 0.80
    MIN_WEIGHTED_SCORE = 2.8
    MIN_SOURCE_TYPES = 2
    MIN_INDEPENDENT_KEYS = 2

    def __init__(
        self,
        evidence=None,
    ):
        self.evidence = evidence

    def _independent_count(
        self,
        candidate,
    ) -> int:
        # Для обычных evidence сохраняем
        # старую семантику.
        if self.evidence is None:
            return len(
                candidate.source_types
            )

        if not hasattr(self.evidence, "memory") or not hasattr(
            self.evidence.memory, "connection"
        ):
            return len(candidate.source_types)

        rows = self.evidence.memory.connection.execute(
            """
            SELECT
                source,
                independence_key,
                weight
            FROM evidence_events
            WHERE category = ?
              AND value = ?
              AND weight > 0
            """,
            (
                candidate.category,
                candidate.value,
            ),
        ).fetchall()

        if not rows:
            return len(
                candidate.source_types
            )

        keys = {
            (
                row["independence_key"]
                if row["independence_key"]
                else row["source"]
            )
            for row in rows
        }

        return len(keys)

    def evaluate(
        self,
        candidate,
    ) -> PromotionDecision:

        if (
            candidate.strength
            < self.MIN_STRENGTH
        ):
            return PromotionDecision(
                action="DEFER",
                field=candidate.field,
                value=candidate.value,
                confidence=candidate.strength,
                reason=(
                    "Недостаточная устойчивость."
                ),
            )

        if (
            candidate.weighted_score
            < self.MIN_WEIGHTED_SCORE
        ):
            return PromotionDecision(
                action="DEFER",
                field=candidate.field,
                value=candidate.value,
                confidence=candidate.strength,
                reason=(
                    "Недостаточно взвешенных "
                    "свидетельств."
                ),
            )

        independent_sources = (
            self._independent_count(
                candidate
            )
        )

        if (
            independent_sources
            < self.MIN_INDEPENDENT_KEYS
        ):
            return PromotionDecision(
                action="DEFER",
                field=candidate.field,
                value=candidate.value,
                confidence=candidate.strength,
                reason=(
                    "Свидетельства пока происходят "
                    "из слишком малого числа "
                    "независимых оснований."
                ),
            )

        return PromotionDecision(
            action="PROMOTE",
            field=candidate.field,
            value=candidate.value,
            confidence=candidate.strength,
            reason=(
                "Кандидат имеет достаточную "
                "устойчивость и независимые "
                "основания."
            ),
        )
