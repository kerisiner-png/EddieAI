from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


VALID_STATUSES = {
    "CANDIDATE",
    "EMERGING",
    "ACTIVE",
    "WEAKENING",
    "DORMANT",
    "REJECTED",
}


@dataclass
class TraitState:
    field: str
    value: str
    status: str
    strength: float
    confidence: float
    evidence_count: int
    first_confirmed: str
    last_confirmed: str
    last_used: str | None = None
    contradictions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PersonalityLifecycle:
    """
    Управляет жизненным циклом уже сформированных
    свойств личности.

    Lifecycle не создаёт черты из воздуха.
    Он только:
    - усиливает существующие;
    - ослабляет неиспользуемые;
    - переводит их между состояниями;
    - реактивирует dormant-черты.
    """

    ACTIVE_THRESHOLD = 0.80
    EMERGING_THRESHOLD = 0.55
    WEAKENING_THRESHOLD = 0.35

    EVIDENCE_STEP = 3
    MATURATION_STEP = 0.02
    MIN_ACTIVE_THRESHOLD = 0.72
    MAX_WEAKENING_THRESHOLD = 0.50
    DECAY_MATURITY_STEP = 0.05
    MIN_DECAY_FACTOR = 0.5

    def __init__(
        self,
        self_state,
        history=None,
    ):
        self.self_state = self_state
        self.history = history

        traits = self.self_state.get(
            "personality_traits"
        )

        if traits is None:
            self.self_state.set(
                "personality_traits",
                {}
            )

    def _traits(self) -> dict:
        return self.self_state.get(
            "personality_traits",
            {}
        )

    def _save_traits(
        self,
        traits: dict,
    ):
        self.self_state.set(
            "personality_traits",
            traits,
        )

    def _key(
        self,
        field: str,
        value: str,
    ) -> str:
        return (
            f"{field}:"
            f"{value.strip().lower()}"
        )

    def _maturity(
        self,
        evidence_count: int,
    ) -> int:
        """
        Зрелость черты по накопленному опыту.

        Каждые EVIDENCE_STEP подтверждений поднимают
        зрелость на одну ступень. Зрелая черта прочнее
        держится в ACTIVE и быстрее отпускает слабые.
        """
        return max(
            0,
            evidence_count // self.EVIDENCE_STEP,
        )

    def _effective_thresholds(
        self,
        evidence_count: int,
    ):
        maturity = self._maturity(
            evidence_count
        )

        active = max(
            self.MIN_ACTIVE_THRESHOLD,
            self.ACTIVE_THRESHOLD
            - self.MATURATION_STEP * maturity,
        )

        weakening = min(
            self.MAX_WEAKENING_THRESHOLD,
            self.WEAKENING_THRESHOLD
            + self.MATURATION_STEP * maturity,
        )

        return (
            active,
            self.EMERGING_THRESHOLD,
            weakening,
        )

    def _decay_maturity_factor(
        self,
        evidence_count: int,
    ) -> float:
        """
        Множитель затухания от зрелости.

        Зрелая черта (много подтверждений) затухает
        медленнее: фактор меньше 1.0 и стремится
        к MIN_DECAY_FACTOR с ростом опыта.
        """
        maturity = self._maturity(
            evidence_count
        )

        return max(
            self.MIN_DECAY_FACTOR,
            1.0 - self.DECAY_MATURITY_STEP * maturity,
        )

    def _status_from_strength_ev(
        self,
        strength: float,
        evidence_count: int,
    ) -> str:
        active, emerging, weakening = (
            self._effective_thresholds(
                evidence_count
            )
        )

        if strength >= active:
            return "ACTIVE"

        if strength >= emerging:
            return "EMERGING"

        if strength >= weakening:
            return "WEAKENING"

        if strength > 0:
            return "DORMANT"

        return "REJECTED"

    def _status_from_strength(
        self,
        strength: float,
    ) -> str:
        return self._status_from_strength_ev(
            strength,
            0,
        )

    def get(
        self,
        field: str,
        value: str,
    ) -> TraitState | None:
        data = self._traits().get(
            self._key(field, value)
        )

        if data is None:
            return None

        return TraitState(
            field=data["field"],
            value=data["value"],
            status=data["status"],
            strength=float(
                data["strength"]
            ),
            confidence=float(
                data["confidence"]
            ),
            evidence_count=int(
                data["evidence_count"]
            ),
            first_confirmed=data[
                "first_confirmed"
            ],
            last_confirmed=data[
                "last_confirmed"
            ],
            last_used=data.get(
                "last_used"
            ),
            contradictions=int(
                data.get(
                    "contradictions",
                    0,
                )
            ),
        )

    def promote(
        self,
        field: str,
        value: str,
        strength: float,
        confidence: float,
        evidence_count: int,
    ) -> TraitState:

        now = datetime.now(
            timezone.utc
        ).isoformat()

        existing = self.get(
            field,
            value,
        )

        previous = existing

        if existing is None:
            trait = TraitState(
                field=field,
                value=value,
                status=self._status_from_strength_ev(
                    strength,
                    evidence_count,
                ),
                strength=max(
                    0.0,
                    min(1.0, strength),
                ),
                confidence=max(
                    0.0,
                    min(1.0, confidence),
                ),
                evidence_count=evidence_count,
                first_confirmed=now,
                last_confirmed=now,
                last_used=now,
            )
        else:
            trait = existing

            trait.strength = max(
                trait.strength,
                strength,
            )

            trait.confidence = max(
                trait.confidence,
                confidence,
            )

            trait.evidence_count = max(
                trait.evidence_count,
                evidence_count,
            )

            trait.last_confirmed = now
            trait.last_used = now

            if trait.status != "REJECTED":
                trait.status = (
                    self._status_from_strength_ev(
                        trait.strength,
                        trait.evidence_count,
                    )
                )

        self._write_trait(
            trait,
            previous=previous,
            event_type=(
                "CREATED"
                if previous is None
                else "PROMOTED"
            ),
            reason=(
                "New personality trait accepted."
                if previous is None
                else "Personality trait promotion updated."
            ),
        )

        return trait

    def reinforce(
        self,
        field: str,
        value: str,
        amount: float = 0.05,
    ):
        """
        Подкрепляет уже существующую черту.

        Особенно важно для dormant-черты:
        новый подтверждающий опыт возвращает её
        из DORMANT в WEAKENING/EMERGING/ACTIVE.
        """

        trait = self.get(
            field,
            value,
        )

        if trait is None:
            return None

        previous = TraitState(
            field=trait.field,
            value=trait.value,
            status=trait.status,
            strength=trait.strength,
            confidence=trait.confidence,
            evidence_count=trait.evidence_count,
            first_confirmed=trait.first_confirmed,
            last_confirmed=trait.last_confirmed,
            last_used=trait.last_used,
            contradictions=trait.contradictions,
        )

        if trait.status == "REJECTED":
            return trait

        now = datetime.now(
            timezone.utc
        ).isoformat()

        trait.strength = min(
            1.0,
            trait.strength + amount,
        )

        trait.confidence = min(
            1.0,
            trait.confidence + amount * 0.5,
        )

        trait.evidence_count += 1
        trait.last_confirmed = now
        trait.last_used = now

        trait.status = (
            self._status_from_strength_ev(
                trait.strength,
                trait.evidence_count,
            )
        )

        self._write_trait(
            trait,
            previous=previous,
            event_type="REINFORCED",
            reason="Supporting evidence reinforced the trait.",
        )

        return trait

    def contradict(
        self,
        field: str,
        value: str,
        amount: float = 0.10,
    ):
        trait = self.get(
            field,
            value,
        )

        if trait is None:
            return None

        previous = TraitState(
            field=trait.field,
            value=trait.value,
            status=trait.status,
            strength=trait.strength,
            confidence=trait.confidence,
            evidence_count=trait.evidence_count,
            first_confirmed=trait.first_confirmed,
            last_confirmed=trait.last_confirmed,
            last_used=trait.last_used,
            contradictions=trait.contradictions,
        )

        if trait.status == "REJECTED":
            return trait

        trait.contradictions += 1

        trait.strength = max(
            0.0,
            trait.strength - amount,
        )

        trait.confidence = max(
            0.0,
            trait.confidence - amount * 0.5,
        )

        if trait.strength <= 0.10:
            trait.status = "DORMANT"
        else:
            trait.status = (
                self._status_from_strength_ev(
                    trait.strength,
                    trait.evidence_count,
                )
            )

        self._write_trait(
            trait,
            previous=previous,
            event_type="CONTRADICTED",
            reason="Contradictory experience weakened the trait.",
        )

        return trait

    def decay(
        self,
        amount: float = 0.02,
    ):
        """
        Один цикл естественного затухания.

        Это не означает, что интерес исчезает
        после одного дня. Каждый вызов лишь немного
        снижает силу.
        """

        traits = self._traits()

        for key, raw in traits.items():
            status_before = raw["status"]

            if status_before == "REJECTED":
                continue

            strength_before = float(
                raw["strength"]
            )
            confidence_before = float(
                raw["confidence"]
            )
            evidence_count = int(
                raw.get("evidence_count", 0)
            )

            if status_before == "ACTIVE":
                delta = amount * 0.5
            elif status_before == "EMERGING":
                delta = amount
            elif status_before == "WEAKENING":
                delta = amount * 1.5
            elif status_before == "DORMANT":
                delta = amount * 2.0
            else:
                delta = amount

            # зрелый характер затухает медленнее
            delta *= self._decay_maturity_factor(
                evidence_count
            )

            raw["strength"] = max(
                0.0,
                strength_before - delta,
            )

            raw["confidence"] = max(
                0.0,
                confidence_before
                - delta * 0.5,
            )

            raw["status"] = (
                self._status_from_strength_ev(
                    raw["strength"],
                    evidence_count,
                )
            )

            if self.history is not None:
                self.history.record(
                    field=raw["field"],
                    value=raw["value"],
                    event_type="DECAYED",
                    status_before=status_before,
                    status_after=raw["status"],
                    strength_before=strength_before,
                    strength_after=float(
                        raw["strength"]
                    ),
                    confidence_before=(
                        confidence_before
                    ),
                    confidence_after=float(
                        raw["confidence"]
                    ),
                    evidence_count=int(
                        raw["evidence_count"]
                    ),
                    contradictions=int(
                        raw.get(
                            "contradictions",
                            0,
                        )
                    ),
                    reason="Natural personality decay.",
                )

        self._save_traits(traits)

    def all_traits(self):
        result = []

        for raw in self._traits().values():
            result.append(
                TraitState(
                    field=raw["field"],
                    value=raw["value"],
                    status=raw["status"],
                    strength=float(
                        raw["strength"]
                    ),
                    confidence=float(
                        raw["confidence"]
                    ),
                    evidence_count=int(
                        raw["evidence_count"]
                    ),
                    first_confirmed=raw[
                        "first_confirmed"
                    ],
                    last_confirmed=raw[
                        "last_confirmed"
                    ],
                    last_used=raw.get(
                        "last_used"
                    ),
                    contradictions=int(
                        raw.get(
                            "contradictions",
                            0,
                        )
                    ),
                )
            )

        return result

    def active_traits(self):
        return [
            trait
            for trait in self.all_traits()
            if trait.status == "ACTIVE"
        ]

    def dormant_traits(self):
        return [
            trait
            for trait in self.all_traits()
            if trait.status == "DORMANT"
        ]

    def _write_trait(
        self,
        trait: TraitState,
        previous: TraitState | None = None,
        event_type: str = "UPDATED",
        reason: str | None = None,
    ):
        traits = self._traits()

        traits[
            self._key(
                trait.field,
                trait.value,
            )
        ] = trait.to_dict()

        self._save_traits(traits)

        if self.history is not None:
            self.history.record(
                field=trait.field,
                value=trait.value,
                event_type=event_type,
                status_before=(
                    previous.status
                    if previous is not None
                    else None
                ),
                status_after=trait.status,
                strength_before=(
                    previous.strength
                    if previous is not None
                    else None
                ),
                strength_after=trait.strength,
                confidence_before=(
                    previous.confidence
                    if previous is not None
                    else None
                ),
                confidence_after=trait.confidence,
                evidence_count=trait.evidence_count,
                contradictions=trait.contradictions,
                reason=reason,
            )
