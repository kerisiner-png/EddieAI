from dataclasses import dataclass


@dataclass(frozen=True)
class IdentityViolation:
    kind: str
    severity: str
    property: str | None
    details: str


class IdentityConsistencyLayer:
    """
    Единая финальная проверка идентичности EddieAI.

    Проверяет:
        1. ownership / perspective;
        2. self-claims;
        3. epistemic consistency.

    Важный принцип:
        один claim -> один canonical validation result.

    Не дублирует один и тот же self-claim через несколько
    независимых путей.
    """

    def __init__(
        self,
        agent,
    ):
        self.agent = agent
        self.ownership = (
            agent.perspective_guard
            .ownership_resolver
        )
        self.self_claims = (
            agent.self_claim_validator
        )

    def analyze(
        self,
        *,
        user_message: str,
        answer: str,
    ) -> dict:

        violations = []

        ownership_result = (
            self.ownership.analyze(
                user_message=user_message,
                answer=answer,
            )
        )

        expected_owner = (
            ownership_result.get(
                "expected_owner"
            )
        )

        # -------------------------------------------------
        # OWNERSHIP
        # -------------------------------------------------

        for item in ownership_result[
            "violations"
        ]:

            expected = item.get(
                "expected_owner"
            )

            actual = item.get(
                "actual_owner"
            )

            # Повтор пользовательского утверждения
            # не считается присвоением свойства себе.
            if (
                expected == "USER"
                and actual == "SELF"
                and self._is_user_claim_echo(
                    user_message=user_message,
                    answer=item.get(
                        "answer_text",
                        "",
                    ),
                )
            ):
                continue

            violations.append(
                IdentityViolation(
                    kind="OWNERSHIP_MISMATCH",
                    severity="HIGH",
                    property=item.get(
                        "property"
                    ),
                    details=str(item),
                )
            )

        # -------------------------------------------------
        # SELF CLAIMS
        # -------------------------------------------------

        self_claim_results = []

        # Ключевое правило:
        # self-state validation имеет смысл,
        # когда пользователь действительно говорит
        # о SELF.
        #
        # При этом validate_text() имеет приоритет над
        # простым claim extraction, потому что он способен
        # различать POSITIVE / NEGATIVE / UNKNOWN.
        if expected_owner == "SELF":

            text_claim = (
                self.self_claims.validate_text(
                    answer
                )
            )

            if (
                text_claim.property
                != "unknown"
            ):
                self_claim_results.append(
                    text_claim
                )

                self._append_claim_violation(
                    violations,
                    text_claim,
                )

            else:
                # Fallback:
                # validate_text() ничего конкретного
                # не понял, поэтому проверяем структурные
                # claims по отдельности.
                for claim in ownership_result[
                    "answer_claims"
                ]:
                    if claim.owner != "SELF":
                        continue

                    if claim.property in {
                        "unknown",
                        "identity",
                    }:
                        continue

                    result = (
                        self.self_claims.validate(
                            property_name=claim.property,
                            text=claim.text,
                        )
                    )

                    self_claim_results.append(
                        result
                    )

                    self._append_claim_violation(
                        violations,
                        result,
                    )

        return {
            "ok": not violations,
            "violations": violations,
            "ownership": ownership_result,
            "self_claims": self_claim_results,
        }

    @staticmethod
    def _append_claim_violation(
        violations: list,
        result,
    ):
        if result.status == "UNSUPPORTED":
            violations.append(
                IdentityViolation(
                    kind="UNSUPPORTED_SELF_CLAIM",
                    severity="HIGH",
                    property=result.property,
                    details=result.reason,
                )
            )

        elif result.status == "CONTRADICTED":
            violations.append(
                IdentityViolation(
                    kind="CONTRADICTED_SELF_CLAIM",
                    severity="HIGH",
                    property=result.property,
                    details=result.reason,
                )
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
            .strip(" .!?;:,")
        )

    @classmethod
    def _is_user_claim_echo(
        cls,
        *,
        user_message: str,
        answer: str,
    ) -> bool:

        user_text = cls._normalize(
            user_message
        )

        answer_text = cls._normalize(
            answer
        )

        return (
            bool(user_text)
            and user_text == answer_text
        )

    def has_high_severity(
        self,
        result: dict,
    ) -> bool:
        return any(
            violation.severity == "HIGH"
            for violation in result.get(
                "violations",
                [],
            )
        )
