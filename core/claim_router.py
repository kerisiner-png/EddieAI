from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimRoutingResult:
    source: str
    claims: tuple
    triage: object
    audit: dict | None


class ClaimRouter:
    """
    Выбирает extraction path для готового ответа.

    Приоритет:
        1. deterministic lexical extraction;
        2. semantic LLM audit, если lexical path
           ничего уверенного не нашёл и triage считает,
           что self-claim потенциально присутствует.
    """

    def __init__(
        self,
        *,
        triage,
        lexical_extractor,
        auditor,
        lexical_adapter,
        claim_adapter,
    ):
        self.triage = triage
        self.lexical_extractor = (
            lexical_extractor
        )
        self.auditor = auditor
        self.lexical_adapter = (
            lexical_adapter
        )
        self.claim_adapter = (
            claim_adapter
        )

    def extract(
        self,
        answer: str,
        *,
        user_name: str | None = None,
        route: str | None = None,
    ) -> ClaimRoutingResult:

        triage_result = (
            self.triage.analyze(
                answer
            )
        )

        lexical_claims = (
            self.lexical_extractor.extract(
                answer,
                implicit_self=(
                    route == "SELF_QUERY"
                ),
            )
        )

        if lexical_claims:
            claims = (
                self.lexical_adapter.to_claims(
                    lexical_claims
                )
            )

            claim_names = {
                claim.predicate
                for claim in claims
            }

            self_concept_predicates = {
                "subjective_consciousness",
                "subjective_feelings",
                "autonomous_agency",
            }

            # Для SELF_QUERY не считаем lexical extraction
            # достаточным, если semantic self-concept слой
            # потенциально нужен, но lexical extractor
            # извлёк только более общий predicate.
            needs_semantic_self_audit = (
                route == "SELF_QUERY"
                and triage_result.potential_self_claim
                and not (
                    claim_names
                    & self_concept_predicates
                )
            )

            if not needs_semantic_self_audit:
                return ClaimRoutingResult(
                    source="LEXICAL",
                    claims=tuple(
                        self._deduplicate(
                            claims
                        )
                    ),
                    triage=triage_result,
                    audit=None,
                )

            audit_result = (
                self.auditor.audit(
                    answer
                )
            )

            semantic_claims = (
                self.claim_adapter.from_response(
                    {
                        "answer": answer,
                        "claims": audit_result.get(
                            "claims",
                            [],
                        ),
                    },
                    speaker="SELF",
                    user_name=user_name,
                )
            )

            semantic_claims = [
                claim
                for claim in semantic_claims
                if self._audit_claim_is_text_supported(
                    answer,
                    claim.predicate,
                )
            ]

            merged = self._deduplicate(
                list(claims)
                + list(semantic_claims)
            )

            return ClaimRoutingResult(
                source="LEXICAL+AUDIT",
                claims=tuple(
                    merged
                ),
                triage=triage_result,
                audit=audit_result,
            )

        if not triage_result.potential_self_claim:
            return ClaimRoutingResult(
                source="NONE",
                claims=(),
                triage=triage_result,
                audit=None,
            )

        audit_result = (
            self.auditor.audit(
                answer
            )
        )

        claims = (
            self.claim_adapter.from_response(
                {
                    "answer": answer,
                    "claims": audit_result.get(
                        "claims",
                        [],
                    ),
                },
                speaker="SELF",
                user_name=user_name,
            )
        )

        claims = [
            claim
            for claim in claims
            if self._audit_claim_is_text_supported(
                answer,
                claim.predicate,
            )
        ]

        return ClaimRoutingResult(
            source="AUDIT",
            claims=tuple(
                self._deduplicate(
                    claims
                )
            ),
            triage=triage_result,
            audit=audit_result,
        )

    def _audit_claim_is_text_supported(
        self,
        answer: str,
        predicate: str,
    ) -> bool:

        spec = (
            self.lexical_extractor.registry.get(
                predicate
            )
        )

        if spec is None:
            return False

        text = (
            str(answer)
            .casefold()
            .replace("ё", "е")
        )

        patterns = (
            tuple(spec.surface_patterns)
            + tuple(spec.negative_patterns)
        )

        return any(
            pattern in text
            for pattern in patterns
        )

    @staticmethod
    def _deduplicate(
        claims,
    ):

        seen = set()
        result = []

        for claim in claims:
            key = (
                claim.owner,
                claim.predicate,
                (
                    str(
                        claim.value
                    )
                    .casefold()
                    .strip()
                    if claim.value is not None
                    else None
                ),
                claim.polarity,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(claim)

        return result
