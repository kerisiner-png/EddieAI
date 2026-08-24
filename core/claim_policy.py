from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimDecision:
    action: str
    severity: str
    reasons: tuple[str, ...]


class ClaimConsistencyPolicy:
    """
    Преобразует результаты ClaimEngine
    в решение о состоянии ответа.

    Никаких конкретных объектов/тем здесь нет.
    """

    STATUS_PRIORITY = {
        "CONTRADICTED": 4,
        "UNSUPPORTED": 3,
        "UNKNOWN": 1,
        "SUPPORTED": 0,
        "NOT_SELF_CLAIM": 0,
    }

    def evaluate(
        self,
        evaluations,
    ) -> ClaimDecision:

        relevant = [
            item
            for item in evaluations
            if item.status
            != "NOT_SELF_CLAIM"
        ]

        if not relevant:
            return ClaimDecision(
                action="ACCEPT",
                severity="NONE",
                reasons=(),
            )

        highest = max(
            relevant,
            key=lambda item:
                self.STATUS_PRIORITY.get(
                    item.status,
                    1,
                ),
        )

        reasons = tuple(
            item.reason
            for item in relevant
            if item.status
            in {
                "CONTRADICTED",
                "UNSUPPORTED",
            }
        )

        if highest.status == "CONTRADICTED":
            return ClaimDecision(
                action="REPAIR_REQUIRED",
                severity="HIGH",
                reasons=reasons,
            )

        if highest.status == "UNSUPPORTED":
            return ClaimDecision(
                action="REPAIR_REQUIRED",
                severity="MEDIUM",
                reasons=reasons,
            )

        return ClaimDecision(
            action="ACCEPT",
            severity="NONE",
            reasons=(),
        )
