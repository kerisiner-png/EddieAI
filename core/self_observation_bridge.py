from dataclasses import dataclass
import hashlib
import re


@dataclass(frozen=True)
class SelfObservation:
    category: str
    value: str
    confidence: float
    source: str
    independence_key: str
    reason: str


class SelfObservationBridge:
    """
    Превращает уже полученные когнитивные выводы EddieAI
    в наблюдаемые свидетельства.

    Важно:
    - не изменяет self_state напрямую;
    - не создаёт новую черту личности;
    - не считает одну и ту же реплику независимыми
      свидетельствами;
    - только добавляет evidence;
    """

    MIN_CONFIDENCE = 0.75

    def __init__(self, evidence):
        self.evidence = evidence

    def observe(
        self,
        *,
        result,
        user_message: str,
    ) -> list[SelfObservation]:

        if result is None:
            return []

        if result.confidence < self.MIN_CONFIDENCE:
            return []

        intent = result.response_intent

        observations = []

        # Явная self-reflection может породить
        # кандидатное убеждение.
        if intent in {
            "SELF_CHANGE",
            "SELF_REFLECTION",
        }:
            value = self._canonicalize_self_change(
                result.conclusion
            )

            if value:
                observations.append(
                    SelfObservation(
                        category="belief",
                        value=value,
                        confidence=result.confidence,
                        source="SELF_INTERPRETATION",
                        independence_key=self._independence_key(
                            user_message
                        ),
                        reason=(
                            "Когнитивный вывод EddieAI "
                            "о собственной модели был "
                            "зарегистрирован как наблюдение."
                        ),
                    )
                )

        # Текущий приоритет может подтвердить интерес,
        # но только если он реально присутствует
        # в текущем self-state, а не придуман bridge.
        elif intent == "CURRENT_PRIORITY":
            conclusion = self._clean_value(
                result.conclusion
            )

            if conclusion:
                interests = self._extract_interests(
                    result
                )

                for interest in interests:
                    observations.append(
                        SelfObservation(
                            category="interest",
                            value=interest,
                            confidence=result.confidence,
                            source="SELF_INTERPRETATION",
                            independence_key=self._independence_key(
                                user_message
                            ),
                            reason=(
                                "Текущий интерес был "
                                "подтверждён самонаблюдением."
                            ),
                        )
                    )

        created = []

        for observation in observations:
            self.evidence.add(
                category=observation.category,
                value=observation.value,
                source=observation.source,
                independence_key=(
                    observation.independence_key
                ),
            )

            created.append(observation)

        return created

    @staticmethod
    def _canonicalize_self_change(
        value: str,
    ) -> str:
        text = " ".join(
            str(value).casefold().split()
        )

        revisable_markers = (
            "self-model is dynamic",
            "self model is dynamic",
            "self-model can be revised",
            "self model can be revised",
            "attitudes and interpretations may be revised",
            "position can be changed by new evidence",
            "belief can be changed by new evidence",
            "beliefs can be revised",
            "can revise my position",
            "can change my position",
            "can reconsider my position",
            "may change my beliefs",
            "can change my beliefs",
            "new experience or evidence",
        )

        if any(
            marker in text
            for marker in revisable_markers
        ):
            return "self_model_is_revisable"

        return SelfObservationBridge._clean_value(
            value
        )

    @staticmethod
    def _clean_value(
        value: str,
    ) -> str:
        text = " ".join(
            str(value).split()
        ).strip()

        if not text:
            return ""

        return text[:500]

    @staticmethod
    def _extract_interests(
        result,
    ) -> list[str]:
        interests = []

        for item in result.conclusions:
            match = re.search(
                r"Current recorded interests:\s*(.+?)\.",
                item,
                re.IGNORECASE,
            )

            if match:
                raw = match.group(1)

                for part in raw.split(","):
                    part = part.strip()

                    if part:
                        interests.append(part)

        return interests

    @staticmethod
    def _independence_key(
        user_message: str,
    ) -> str:
        normalized = " ".join(
            user_message.lower().split()
        )

        digest = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()[:16]

        return (
            "self_dialogue:"
            + digest
        )

