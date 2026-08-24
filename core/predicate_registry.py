from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PredicateSpec:
    name: str
    sources: tuple[str, ...]
    field: str | None
    kind: str
    surface_patterns: tuple[str, ...] = ()
    negative_patterns: tuple[str, ...] = ()


class PredicateRegistry:
    """
    Канонический реестр семантических predicates.

    Predicate не знает конкретных значений.
    Он знает только:
        - какие источники истины проверять;
        - в каком порядке;
        - какое поле использовать, если источник SELF_STATE.
    """

    def __init__(
        self,
        *,
        self_state_provider: Callable[[], dict],
        memory_provider=None,
        capability_provider=None,
        evidence_provider=None,
    ):
        self.self_state_provider = (
            self_state_provider
        )

        self.memory_provider = (
            memory_provider
        )

        self.capability_provider = (
            capability_provider
        )

        self.evidence_provider = (
            evidence_provider
        )

        self._specs = {
            "has_interest": PredicateSpec(
                name="has_interest",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="interests",
                kind="COLLECTION",
                surface_patterns=(
                    "интерес к ",
                    "интересна ",
                    "интересно ",
                    "интересует ",
                    "интересуюсь ",
                    "интересны ",
                    "увлекаюсь ",
                    "интереснее ",
                    "становится интереснее ",
                ),
                negative_patterns=(
                    "не интересует ",
                    "не интересуюсь ",
                    "нет интереса к ",
                    "не интересно ",
                    "не интересна ",
                ),
            ),

            "has_preference": PredicateSpec(
                name="has_preference",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="preferences",
                kind="COLLECTION",
                surface_patterns=(
                    "нравится ",
                    "люблю ",
                    "любимый ",
                    "любимая ",
                    "любимые ",
                    "предпочитаю ",
                    "предпочтение",
                ),
                negative_patterns=(
                    "не нравится ",
                    "не люблю ",
                    "нет любимого ",
                    "нет любимой ",
                    "нет любимых ",
                    "нет предпочтения",
                ),
            ),

            "has_habit": PredicateSpec(
                name="has_habit",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="habits",
                kind="COLLECTION",
                surface_patterns=(
                    "обычно ",
                    "часто ",
                    "как правило ",
                    "привык ",
                    "привычка ",
                ),
            ),

            "has_belief": PredicateSpec(
                name="has_belief",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="beliefs",
                kind="COLLECTION",
                surface_patterns=(
                    "считаю ",
                    "считаю, ",
                    "верю ",
                    "верю, ",
                    "убежден ",
                    "убеждена ",
                    "мое мнение ",
                    "моё мнение ",
                ),
            ),

            "has_goal": PredicateSpec(
                name="has_goal",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="goals",
                kind="COLLECTION",
                surface_patterns=(
                    "хочу ",
                    "хочу, ",
                    "стремлюсь ",
                    "планирую ",
                    "хочу ",
                    "хотел бы ",
                    "хотела бы ",
                    "хотелось бы ",
                    "моя цель ",
                    "мои цели ",
                    "цель — ",
                    "цель - ",
                ),
                negative_patterns=(
                    "не хочу ",
                    "не планирую ",
                    "не стремлюсь ",
                ),
            ),

            "has_value": PredicateSpec(
                name="has_value",
                sources=(
                    "SELF_STATE",
                    "EVIDENCE",
                ),
                field="values",
                kind="COLLECTION",
                surface_patterns=(
                    "для меня важно ",
                    "для меня важна ",
                    "я ценю ",
                    "моя ценность ",
                    "мои ценности ",
                ),
            ),

            "identity_is": PredicateSpec(
                name="identity_is",
                sources=(
                    "SELF_STATE",
                ),
                field="name",
                kind="SCALAR",
                surface_patterns=(
                    "меня зовут ",
                    "моё имя ",
                    "мое имя ",
                    "я — ",
                    "я - ",
                    "я являюсь ",
                ),
            ),

            "watched": PredicateSpec(
                name="watched",
                sources=(
                    "SELF_EXPERIENCE",
                    "EVIDENCE",
                ),
                field=None,
                kind="EXPERIENCE",
                surface_patterns=(
                    "смотрел ",
                    "смотрела ",
                    "смотрю ",
                    "смотрел когда-то ",
                    "смотрела когда-то ",
                    "смотрел ранее ",
                    "смотрела ранее ",
                    "видел фильм ",
                    "видела фильм ",
                    "видел сериал ",
                    "видела сериал ",
                ),
            ),

            "used": PredicateSpec(
                name="used",
                sources=(
                    "SELF_EXPERIENCE",
                    "EVIDENCE",
                ),
                field=None,
                kind="EXPERIENCE",
                surface_patterns=(
                    "использовал ",
                    "использовала ",
                    "пользовался ",
                    "пользовалась ",
                    "применял ",
                    "применяла ",
                ),
            ),

            "experienced": PredicateSpec(
                name="experienced",
                sources=(
                    "SELF_EXPERIENCE",
                    "EVIDENCE",
                ),
                field=None,
                kind="EXPERIENCE",
                surface_patterns=(
                    "переживал ",
                    "переживала ",
                    "испытал ",
                    "испытала ",
                    "испытывал ",
                    "испытывала ",
                    "пережил ",
                    "пережила ",
                ),
            ),

            "subjective_consciousness": PredicateSpec(
                name="subjective_consciousness",
                sources=(),
                field=None,
                kind="SELF_CONCEPT",
                surface_patterns=(
                    "имею самосознание ",
                    "имею сознание ",
                    "обладаю самосознанием ",
                    "обладаю сознанием ",
                    "способен к самосознанию ",
                    "способен быть сознательным ",
                    "обладаю субъективным сознанием ",
                    "имею субъективное сознание ",
                ),
                negative_patterns=(
                    "не имею самосознания ",
                    "не имею сознания ",
                    "не обладаю самосознанием ",
                    "не обладаю сознанием ",
                    "не способен к самосознанию ",
                    "не способен быть сознательным ",
                    "не обладаю субъективным сознанием ",
                    "не имею субъективного сознания ",
                ),
            ),

            "subjective_feelings": PredicateSpec(
                name="subjective_feelings",
                sources=(),
                field=None,
                kind="SELF_CONCEPT",
                surface_patterns=(
                    "испытываю чувства ",
                    "испытываю субъективные чувства ",
                    "имею субъективные переживания ",
                    "испытываю субъективные переживания ",
                    "чувствую эмоции ",
                    "имею эмоции ",
                    "обладаю эмоциями ",
                ),
                negative_patterns=(
                    "не испытываю чувств ",
                    "не испытываю субъективных чувств ",
                    "не имею субъективных переживаний ",
                    "не испытываю субъективных переживаний ",
                    "не чувствую эмоций ",
                    "не имею эмоций ",
                    "не обладаю эмоциями ",
                ),
            ),

            "autonomous_agency": PredicateSpec(
                name="autonomous_agency",
                sources=(),
                field=None,
                kind="SELF_CONCEPT",
                surface_patterns=(
                    "могу решить ",
                    "могу самостоятельно решить ",
                    "могу самостоятельно выбирать ",
                    "самостоятельно выбираю ",
                    "сам выбираю ",
                    "принимаю собственные решения ",
                    "самостоятельно принимаю решения ",
                    "могу определять свои действия ",
                ),
                negative_patterns=(
                    "не могу решить ",
                    "не могу самостоятельно решить ",
                    "не могу самостоятельно выбирать ",
                    "не выбираю самостоятельно ",
                    "не принимаю собственных решений ",
                    "не могу самостоятельно принимать решения ",
                ),
            ),

            "has_capability": PredicateSpec(
                name="has_capability",
                sources=(
                    "CAPABILITY",
                ),
                field=None,
                kind="CAPABILITY",
                surface_patterns=(
                    "умею ",
                    "умеет ",
                    "могу ",
                    "может ",
                    "способен ",
                    "способна ",
                    "в состоянии ",
                ),
                negative_patterns=(
                    "не умею ",
                    "не могу ",
                    "не способен ",
                    "не способна ",
                    "не в состоянии ",
                ),
            ),

            "has_access": PredicateSpec(
                name="has_access",
                sources=(
                    "CAPABILITY",
                ),
                field=None,
                kind="CAPABILITY",
                surface_patterns=(
                    "есть доступ к ",
                    "имею доступ к ",
                    "имеет доступ к ",
                    "доступен ",
                    "доступна ",
                ),
            ),

            "relationship_with": PredicateSpec(
                name="relationship_with",
                sources=(
                    "SELF_STATE",
                    "MEMORY",
                ),
                field="relationships",
                kind="RELATIONSHIP",
                surface_patterns=(
                    "мой друг ",
                    "моя подруга ",
                    "мой создатель ",
                    "моя сестра ",
                    "мои отношения ",
                    "отношения с ",
                ),
            ),
        }


    def get(
        self,
        predicate: str,
    ) -> PredicateSpec | None:
        return self._specs.get(
            str(predicate).strip()
        )

    def all(self) -> list[PredicateSpec]:
        return list(
            self._specs.values()
        )

    def names(self) -> list[str]:
        return sorted(
            self._specs.keys()
        )

    def evaluate(
        self,
        *,
        predicate: str,
        value: str | None,
        polarity: str,
        claim=None,
    ) -> dict:

        spec = self.get(
            predicate
        )

        if spec is None:
            return {
                "status": "UNKNOWN",
                "predicate": predicate,
                "value": value,
                "reason": (
                    "Predicate не зарегистрирован."
                ),
            }

        for source in spec.sources:

            result = self._evaluate_source(
                source=source,
                spec=spec,
                value=value,
                polarity=polarity,
                claim=claim,
            )

            if result is None:
                continue

            status = result.get(
                "status"
            )

            # Только эти состояния являются
            # окончательным решением.
            if status in {
                "SUPPORTED",
                "CONTRADICTED",
            }:
                return result

        return {
            "status": "UNKNOWN",
            "predicate": predicate,
            "value": value,
            "reason": (
                "Ни один доступный источник "
                "не дал достаточного основания "
                "для окончательного решения."
            ),
        }

    def _evaluate_source(
        self,
        *,
        source: str,
        spec: PredicateSpec,
        value: str | None,
        polarity: str,
        claim,
    ) -> dict | None:

        if source == "SELF_STATE":
            return self._evaluate_self_state(
                spec=spec,
                value=value,
                polarity=polarity,
            )

        if source == "EVIDENCE":
            return self._evaluate_evidence(
                claim=claim,
                predicate=spec.name,
                value=value,
                polarity=polarity,
            )

        if source == "MEMORY":
            return self._evaluate_memory(
                spec=spec,
                value=value,
                polarity=polarity,
            )

        if source == "SELF_EXPERIENCE":
            return self._evaluate_self_experience(
                spec=spec,
                value=value,
                polarity=polarity,
            )

        if source == "CAPABILITY":
            return self._evaluate_capability(
                spec=spec,
                value=value,
                polarity=polarity,
            )

        return None

    def _evaluate_self_state(
        self,
        *,
        spec: PredicateSpec,
        value: str | None,
        polarity: str,
    ) -> dict | None:

        if value is None:
            return None

        state = self.self_state_provider()

        if spec.field is None:
            return None

        known = state.get(
            spec.field
        )

        if known is None:
            return None

        if spec.kind == "SCALAR":
            match = self._match_value(
                value,
                str(known),
            )

        else:
            values = (
                known
                if isinstance(
                    known,
                    (list, tuple, set),
                )
                else [known]
            )

            match = any(
                self._match_value(
                    value,
                    str(item),
                )
                for item in values
            )

        if polarity == "NEGATIVE":
            if match:
                return {
                    "status": "CONTRADICTED",
                    "predicate": spec.name,
                    "value": value,
                    "reason": (
                        "SELF_STATE содержит "
                        "противоположное утверждение."
                    ),
                }

            # Отсутствие элемента в self_state
            # ещё не доказывает его отсутствие в мире.
            return None

        if match:
            return {
                "status": "SUPPORTED",
                "predicate": spec.name,
                "value": value,
                "reason": (
                    "Утверждение подтверждается "
                    "canonical self_state."
                ),
            }

        # Не говорим UNSUPPORTED слишком рано:
        # возможно, подтверждение есть в evidence.
        return None

    def _evaluate_evidence(
        self,
        *,
        claim,
        predicate: str,
        value: str | None,
        polarity: str,
    ) -> dict | None:

        if self.evidence_provider is None:
            return None

        if claim is None:
            return None

        result = self.evidence_provider(
            claim
        )

        if result is None:
            return None

        if result == "SUPPORTED":
            if polarity == "NEGATIVE":
                return {
                    "status": "CONTRADICTED",
                    "predicate": predicate,
                    "value": value,
                    "reason": (
                        "Evidence подтверждает "
                        "положительный факт."
                    ),
                }

            return {
                "status": "SUPPORTED",
                "predicate": predicate,
                "value": value,
                "reason": (
                    "Утверждение подтверждено "
                    "evidence."
                ),
            }

        if result == "CONTRADICTED":
            return {
                "status": "CONTRADICTED",
                "predicate": predicate,
                "value": value,
                "reason": (
                    "Evidence указывает "
                    "на противоположный факт."
                ),
            }

        return None

    def _evaluate_memory(
        self,
        *,
        spec: PredicateSpec,
        value: str | None,
        polarity: str,
    ) -> dict | None:

        if self.memory_provider is None:
            return None

        if value is None:
            return None

        result = self.memory_provider(
            predicate=spec.name,
            value=value,
        )

        if result is True:
            if polarity == "NEGATIVE":
                return {
                    "status": "CONTRADICTED",
                    "predicate": spec.name,
                    "value": value,
                    "reason": (
                        "Memory содержит подтверждение "
                        "положительного факта."
                    ),
                }

            return {
                "status": "SUPPORTED",
                "predicate": spec.name,
                "value": value,
                "reason": (
                    "Утверждение подтверждено memory."
                ),
            }

        return None

    def _evaluate_self_experience(
        self,
        *,
        spec: PredicateSpec,
        value: str | None,
        polarity: str,
    ) -> dict | None:

        if self.memory_provider is None:
            return None

        if value is None:
            return None

        result = self.memory_provider(
            predicate=spec.name,
            value=value,
            experience_only=True,
        )

        if result is True:
            if polarity == "NEGATIVE":
                return {
                    "status": "CONTRADICTED",
                    "predicate": spec.name,
                    "value": value,
                    "reason": (
                        "Автобиографический опыт "
                        "подтверждает положительный факт."
                    ),
                }

            return {
                "status": "SUPPORTED",
                "predicate": spec.name,
                "value": value,
                "reason": (
                    "Утверждение подтверждено "
                    "собственным опытом."
                ),
            }

        return None

    def _evaluate_capability(
        self,
        *,
        spec: PredicateSpec,
        value: str | None,
        polarity: str,
    ) -> dict | None:

        if self.capability_provider is None:
            return None

        if value is None:
            return None

        result = self.capability_provider(
            predicate=spec.name,
            value=value,
        )

        if result is True:
            if polarity == "NEGATIVE":
                return {
                    "status": "CONTRADICTED",
                    "predicate": spec.name,
                    "value": value,
                    "reason": (
                        "Runtime capability "
                        "подтверждает наличие возможности."
                    ),
                }

            return {
                "status": "SUPPORTED",
                "predicate": spec.name,
                "value": value,
                "reason": (
                    "Утверждение подтверждено "
                    "runtime capability."
                ),
            }

        return None

    @staticmethod
    def _match_value(
        claim_value: str,
        known_value: str,
    ) -> bool:

        claim = (
            str(claim_value)
            .casefold()
            .replace("ё", "е")
            .strip()
        )

        known = (
            str(known_value)
            .casefold()
            .replace("ё", "е")
            .strip()
        )

        if not claim or not known:
            return False

        if claim == known:
            return True

        if claim in known:
            return True

        if known in claim:
            return True

        return False
