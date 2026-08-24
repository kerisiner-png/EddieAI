class EvidenceProvider:
    """
    Консервативный адаптер между ClaimEngine и EvidenceEngine.

    Отсутствие evidence -> None.

    Наличие достаточно сильного evidence:
        -> SUPPORTED

    Источники SELF_OUTPUT и SELF_OBSERVATION
    не считаются самостоятельным подтверждением.
    """

    STRONG_SOURCES = {
        "SELF_ACTION",
        "SELF_EXPERIENCE",
        "ACTION_CHOICE",
    }

    CATEGORY_BY_PREDICATE = {
        "has_interest": "interest",
        "has_preference": "preference",
        "has_habit": "habit",
        "has_belief": "belief",
        "has_goal": "goal",
        "has_value": "value",
    }

    def __init__(
        self,
        evidence_engine,
    ):
        self.evidence = evidence_engine

    def __call__(
        self,
        claim,
    ):
        category = (
            self.CATEGORY_BY_PREDICATE.get(
                claim.predicate
            )
        )

        if category is None:
            return None

        if not claim.value:
            return None

        try:
            record = self.evidence.get(
                category,
                claim.value,
            )
        except ValueError:
            return None

        strong_sources = (
            set(record.source_types)
            & self.STRONG_SOURCES
        )

        if not strong_sources:
            return None

        if record.confidence < 0.70:
            return None

        if claim.polarity == "NEGATIVE":
            return "CONTRADICTED"

        return "SUPPORTED"
