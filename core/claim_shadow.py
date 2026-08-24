from dataclasses import dataclass


@dataclass(frozen=True)
class ShadowComparison:
    old_ok: bool
    new_action: str
    new_severity: str
    new_claim_count: int
    new_evaluations: tuple
    mismatch: bool


class ClaimShadowRunner:
    """
    Запускает новый claim pipeline параллельно старому
    identity pipeline.

    Ничего не исправляет и не меняет пользовательский ответ.
    """

    def __init__(
        self,
        *,
        claim_engine,
        claim_policy,
        claim_adapter,
    ):
        self.claim_engine = claim_engine
        self.claim_policy = claim_policy
        self.claim_adapter = claim_adapter

    def analyze(
        self,
        *,
        answer: str,
        structured_response: dict,
        old_ok: bool,
        user_name: str | None = None,
    ) -> ShadowComparison:

        claims = self.claim_adapter.from_response(
            structured_response,
            speaker="SELF",
            user_name=user_name,
        )

        evaluations = tuple(
            self.claim_engine.validate_claim(
                claim
            )
            for claim in claims
        )

        decision = (
            self.claim_policy.evaluate(
                evaluations
            )
        )

        new_problem = (
            decision.action
            == "REPAIR_REQUIRED"
        )

        mismatch = (
            old_ok != (not new_problem)
        )

        return ShadowComparison(
            old_ok=old_ok,
            new_action=decision.action,
            new_severity=decision.severity,
            new_claim_count=len(claims),
            new_evaluations=evaluations,
            mismatch=mismatch,
        )
