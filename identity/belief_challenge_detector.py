from dataclasses import dataclass


@dataclass(frozen=True)
class BeliefChallenge:
    belief: str
    evidence: str
    strength: float
    confidence: float
    reason: str


class BeliefChallengeDetector:
    """
    Определяет, бросает ли новое evidence вызов
    уже существующему SELF belief.

    Detector не меняет beliefs.
    Detector не продвигает и не отклоняет beliefs.

    На текущем этапе принимает только явный
    структурированный сигнал belief_challenges.
    """

    def __init__(
        self,
        self_state,
    ):
        self.self_state = self_state

    def detect(
        self,
        *,
        result: dict,
    ) -> list[BeliefChallenge]:

        payload = result.get(
            "result",
            {},
        )

        if not isinstance(
            payload,
            dict,
        ):
            return []

        challenges = (
            payload.get(
                "belief_challenges",
                [],
            )
        )

        if not isinstance(
            challenges,
            list,
        ):
            return []

        beliefs = self.self_state.get(
            "beliefs",
            [],
        )

        if not isinstance(
            beliefs,
            list,
        ):
            beliefs = []

        known_beliefs = {
            str(belief).strip().casefold()
            for belief in beliefs
            if str(belief).strip()
        }

        detected = []

        for item in challenges:
            if not isinstance(
                item,
                dict,
            ):
                continue

            belief = str(
                item.get(
                    "belief",
                    "",
                )
            ).strip()

            evidence = str(
                item.get(
                    "evidence",
                    "",
                )
            ).strip()

            if not belief or not evidence:
                continue

            # Не принимаем challenge к тому,
            # чего нет среди собственных beliefs.
            if (
                belief.casefold()
                not in known_beliefs
            ):
                continue

            try:
                strength = float(
                    item.get(
                        "strength",
                        0.0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                strength = 0.0

            try:
                confidence = float(
                    item.get(
                        "confidence",
                        0.0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            strength = max(
                0.0,
                min(1.0, strength),
            )

            confidence = max(
                0.0,
                min(1.0, confidence),
            )

            if (
                strength < 0.5
                or confidence < 0.5
            ):
                continue

            detected.append(
                BeliefChallenge(
                    belief=belief,
                    evidence=evidence,
                    strength=strength,
                    confidence=confidence,
                    reason=str(
                        item.get(
                            "reason",
                            "Новое evidence "
                            "противоречит существующему "
                            "убеждению.",
                        )
                    ),
                )
            )

        return detected

    def to_appraisal_input(
        self,
        challenges: list[BeliefChallenge],
    ) -> list[dict]:

        return [
            {
                "belief": challenge.belief,
                "evidence": challenge.evidence,
                "strength": challenge.strength,
                "confidence": challenge.confidence,
                "reason": challenge.reason,
            }
            for challenge in challenges
        ]
