from dataclasses import dataclass


@dataclass
class MotivationCandidate:
    goal: str
    motivation: float
    priority: float
    confidence: float
    source_traits: list[str]
    reason: str


class MotivationEngine:
    """
    Выявляет потенциальные цели из устойчивых
    интересов, предпочтений, привычек и текущих целей.

    Он НЕ создаёт активную цель напрямую.
    """

    MIN_MOTIVATION = 0.60
    MIN_PRIORITY = 0.40

    def __init__(
        self,
        self_state,
        personality_lifecycle=None,
    ):
        self.self_state = self_state
        self.personality_lifecycle = (
            personality_lifecycle
        )

    def candidates(self):
        candidates = []

        traits = []

        if self.personality_lifecycle is not None:
            traits = (
                self.personality_lifecycle
                .active_traits()
            )

        # ---------------------------------------------
        # Интересы → потенциальное исследование
        # ---------------------------------------------

        for trait in traits:
            if trait.field != "interest":
                continue

            motivation = min(
                1.0,
                trait.strength * 0.9,
            )

            priority = min(
                1.0,
                0.4
                + trait.strength * 0.4,
            )

            if (
                motivation < self.MIN_MOTIVATION
                or priority < self.MIN_PRIORITY
            ):
                continue

            goal = (
                f"изучить тему: "
                f"{trait.value}"
            )

            candidates.append(
                MotivationCandidate(
                    goal=goal,
                    motivation=round(
                        motivation,
                        3,
                    ),
                    priority=round(
                        priority,
                        3,
                    ),
                    confidence=round(
                        trait.confidence,
                        3,
                    ),
                    source_traits=[
                        f"{trait.field}:{trait.value}"
                    ],
                    reason=(
                        "Устойчивый интерес "
                        "может естественно породить "
                        "исследовательскую цель."
                    ),
                )
            )

        # ---------------------------------------------
        # Уже существующие цели
        # ---------------------------------------------

        existing_goals = self.self_state.get(
            "goals",
            [],
        )

        for goal in existing_goals:
            candidates.append(
                MotivationCandidate(
                    goal=str(goal),
                    motivation=0.80,
                    priority=0.80,
                    confidence=0.80,
                    source_traits=[
                        "self_state:goal"
                    ],
                    reason=(
                        "Цель уже существует "
                        "в текущем состоянии личности."
                    ),
                )
            )

        return self._deduplicate(
            candidates
        )

    def _deduplicate(
        self,
        candidates,
    ):
        result = {}
        
        for candidate in candidates:
            key = candidate.goal.lower().strip()

            existing = result.get(key)

            if existing is None:
                result[key] = candidate
                continue

            if (
                candidate.motivation
                > existing.motivation
            ):
                result[key] = candidate

        return list(result.values())
