from dataclasses import dataclass


@dataclass
class PersonalityCandidate:
    field: str
    value: str
    category: str
    strength: float
    weighted_score: float
    evidence_count: int
    source_types: list[str]
    reason: str


class PersonalityEngine:
    CANONICAL_FIELDS = {
        "interest",
        "preference",
        "habit",
        "belief",
        "goal",
    }

    SELF_STATE_COLLECTIONS = {
        "interest": "interests",
        "preference": "preferences",
        "habit": "habits",
        "belief": "beliefs",
        "goal": "goals",
    }

    MIN_STRENGTH = 0.75
    MIN_WEIGHTED_SCORE = 2.5

    def __init__(
        self,
        pattern_detector,
    ):
        self.pattern_detector = pattern_detector

    def candidates(
        self,
        self_state=None,
    ):
        patterns = (
            self.pattern_detector.strong_patterns(
                minimum_strength=self.MIN_STRENGTH,
                minimum_weighted_score=(
                    self.MIN_WEIGHTED_SCORE
                ),
            )
        )

        candidates = []

        for pattern in patterns:
            field = pattern.category

            if field not in self.CANONICAL_FIELDS:
                continue

            if self_state is not None:
                collection = (
                    self.SELF_STATE_COLLECTIONS[
                        field
                    ]
                )

                current_values = (
                    self_state.get(
                        collection,
                        [],
                    )
                )

                normalized_current = {
                    str(value).lower().strip()
                    for value in current_values
                }

                if (
                    pattern.value.lower().strip()
                    in normalized_current
                ):
                    continue

            candidates.append(
                PersonalityCandidate(
                    field=field,
                    value=pattern.value,
                    category=pattern.category,
                    strength=pattern.strength,
                    weighted_score=(
                        pattern.weighted_score
                    ),
                    evidence_count=pattern.count,
                    source_types=(
                        pattern.source_types
                    ),
                    reason=(
                        "Сформирован устойчивый "
                        "паттерн: "
                        f"{pattern.count} свидетельств, "
                        f"взвешенный балл "
                        f"{pattern.weighted_score}, "
                        f"источники: "
                        f"{pattern.source_types}."
                    ),
                )
            )

        return candidates
