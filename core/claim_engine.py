from core.predicate_registry import PredicateRegistry
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Claim:
    owner: str
    predicate: str
    value: str | None
    polarity: str
    certainty: str
    temporal_scope: str
    text: str


@dataclass(frozen=True)
class ClaimSet:
    claims: list[Claim] = field(
        default_factory=list
    )

    def self_claims(self) -> list[Claim]:
        return [
            claim
            for claim in self.claims
            if claim.owner == "SELF"
        ]


@dataclass(frozen=True)
class ClaimEvaluation:
    status: str
    claim: Claim
    reason: str


class ClaimEngine:
    """
    Универсальный semantic claim layer.

    Он НЕ знает про:
        Naruto
        Dune
        astrophysics
        internet
        конкретные интересы

    Он работает только с абстрактной структурой:

        owner
        predicate
        value
        polarity
        certainty
        temporal_scope

    Семантическое извлечение пока предоставляется
    внешним extractor-слоем.
    """

    VALID_OWNERS = {
        "SELF",
        "USER",
        "EXTERNAL",
        "SHARED",
        "UNKNOWN",
    }

    VALID_POLARITIES = {
        "POSITIVE",
        "NEGATIVE",
        "UNKNOWN",
    }

    VALID_CERTAINTIES = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN",
    }

    VALID_TEMPORAL = {
        "PAST",
        "CURRENT",
        "FUTURE",
        "DURATIVE",
        "UNKNOWN",
    }

    def __init__(
        self,
        *,
        self_state_provider,
        evidence_provider=None,
        capability_provider=None,
        memory_provider=None,
    ):
        self.predicate_registry = PredicateRegistry(
            self_state_provider=self_state_provider,
            evidence_provider=evidence_provider,
            capability_provider=capability_provider,
            memory_provider=memory_provider,
        )

    def validate_claim(
        self,
        claim: Claim,
    ) -> ClaimEvaluation:

        if claim.owner != "SELF":
            return ClaimEvaluation(
                status="NOT_SELF_CLAIM",
                claim=claim,
                reason=(
                    "Утверждение не относится "
                    "непосредственно к EddieAI."
                ),
            )

        result = (
            self.predicate_registry.evaluate(
                predicate=claim.predicate,
                value=claim.value,
                polarity=claim.polarity,
                claim=claim,
            )
        )

        return ClaimEvaluation(
            status=result["status"],
            claim=claim,
            reason=result["reason"],
        )

    def validate_set(
        self,
        claim_set: ClaimSet,
    ) -> list[ClaimEvaluation]:

        return [
            self.validate_claim(claim)
            for claim in claim_set.claims
        ]

    def _evaluate_against_self_state(
        self,
        claim: Claim,
        self_state: dict[str, Any],
    ) -> ClaimEvaluation | None:

        # Canonical self-properties are checked through
        # their actual state fields.

        canonical_fields = {
            "has_interest": "interests",
            "has_preference": "preferences",
            "has_habit": "habits",
            "has_belief": "beliefs",
            "has_goal": "goals",
        }

        field_name = canonical_fields.get(
            claim.predicate
        )

        if field_name is None:
            return None

        values = self_state.get(
            field_name,
            [],
        )

        values = [
            self._extract_value_text(
                value
            ).casefold()
            for value in values
        ]

        value = (
            claim.value.casefold()
            if claim.value
            else None
        )

        if claim.polarity == "POSITIVE":

            if value is None:
                return None

            if self._semantic_value_match(
                value,
                values,
            ):
                return ClaimEvaluation(
                    status="SUPPORTED",
                    claim=claim,
                    reason=(
                        "Утверждение подтверждается "
                        "текущим self_state."
                    ),
                )

            return ClaimEvaluation(
                status="UNSUPPORTED",
                claim=claim,
                reason=(
                    "Утверждение не найдено "
                    "в текущем self_state."
                ),
            )

        if claim.polarity == "NEGATIVE":

            if value is None:
                return None

            if self._semantic_value_match(
                value,
                values,
            ):
                return ClaimEvaluation(
                    status="CONTRADICTED",
                    claim=claim,
                    reason=(
                        "Отрицательное утверждение "
                        "противоречит текущему self_state."
                    ),
                )

            return ClaimEvaluation(
                status="UNKNOWN",
                claim=claim,
                reason=(
                    "Отрицательное утверждение "
                    "не подтверждено и не опровергнуто."
                ),
            )

        return ClaimEvaluation(
            status="UNKNOWN",
            claim=claim,
            reason=(
                "Полярность утверждения неизвестна."
            ),
        )

    @staticmethod
    def _extract_value_text(value) -> str:
        if isinstance(value, dict):
            label = value.get("label")
            if isinstance(label, str) and label.strip():
                return label
            parts = []
            ctx = value.get("context")
            mtd = value.get("method")
            if ctx:
                parts.append(str(ctx))
            if mtd:
                parts.append(str(mtd))
            if parts:
                return " ".join(parts)
            return str(value)
        return str(value)

    @staticmethod
    def _semantic_value_match(
        value: str,
        known_values: list[str],
    ) -> bool:

        if value in known_values:
            return True

        # Пока только очень осторожная нормализация.
        # Никаких предметных правил.
        value_tokens = [
            token
            for token in value.split()
            if len(token) >= 5
        ]

        for token in value_tokens:
            stem = token[
                :max(
                    5,
                    len(token) - 2,
                )
            ]

            if any(
                stem in known
                for known in known_values
            ):
                return True

        return False
