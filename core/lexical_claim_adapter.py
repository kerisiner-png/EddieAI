from core.claim_engine import Claim


class LexicalClaimAdapter:

    @staticmethod
    def to_claim(
        lexical_claim,
    ) -> Claim:

        return Claim(
            owner="SELF",
            predicate=lexical_claim.predicate,
            value=lexical_claim.value,
            polarity=lexical_claim.polarity,
            certainty=lexical_claim.certainty,
            temporal_scope=lexical_claim.temporal_scope,
            text=lexical_claim.text,
        )

    @classmethod
    def to_claims(
        cls,
        lexical_claims,
    ) -> list[Claim]:

        return [
            cls.to_claim(
                item
            )
            for item in lexical_claims
        ]
