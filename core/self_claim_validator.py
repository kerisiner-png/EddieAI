from dataclasses import dataclass


@dataclass(frozen=True)
class SelfClaimResult:
    status: str
    property: str
    value: str | None = None
    polarity: str = "UNKNOWN"
    reason: str = ""


class SelfClaimValidator:
    """
    Проверяет утверждения EddieAI о самом себе
    относительно текущего self_state.

    Возможные статусы:

        SUPPORTED
        UNSUPPORTED
        UNKNOWN
        NOT_SELF_CLAIM
    """

    def __init__(self, agent):
        self.agent = agent

    def validate(
        self,
        *,
        property_name: str,
        text: str,
    ) -> SelfClaimResult:

        self_state = self.agent.self_state

        if property_name == "interest":
            return self._validate_list(
                property_name,
                text,
                list(
                    self_state.get(
                        "interests",
                        [],
                    )
                ),
            )

        if property_name == "preference":
            return self._validate_list(
                property_name,
                text,
                list(
                    self_state.get(
                        "preferences",
                        [],
                    )
                ),
            )

        if property_name == "habit":
            return self._validate_list(
                property_name,
                text,
                list(
                    self_state.get(
                        "habits",
                        [],
                    )
                ),
            )

        if property_name == "belief":
            return self._validate_list(
                property_name,
                text,
                list(
                    self_state.get(
                        "beliefs",
                        [],
                    )
                ),
            )

        if property_name == "goal":
            return self._validate_list(
                property_name,
                text,
                list(
                    self_state.get(
                        "goals",
                        [],
                    )
                ),
            )

        if property_name == "experience":
            return SelfClaimResult(
                status="UNKNOWN",
                property="experience",
                value=None,
                polarity="POSITIVE",
                reason=(
                    "Текущее self_state не содержит "
                    "достаточных данных для проверки "
                    "данного личного опыта."
                ),
            )

        if property_name == "capability":
            return self._validate_capability(
                text
            )

        if property_name == "internet_access":
            return self._validate_internet_access(
                text
            )

        if property_name == "identity":
            return SelfClaimResult(
                status="SUPPORTED",
                property="identity",
                value="EddieAI",
                polarity="POSITIVE",
                reason=(
                    "Идентичность EddieAI "
                    "подтверждается self_state."
                ),
            )

        return SelfClaimResult(
            status="UNKNOWN",
            property=property_name,
            value=None,
            reason=(
                "Для этого типа self-утверждения "
                "пока нет детерминированного валидатора."
            ),
        )

    def validate_text(
        self,
        text: str,
    ) -> SelfClaimResult:

        normalized = self._normalize(
            text
        )

        # ---------------------------------------------
        # NEGATIVE EXISTENCE
        # ---------------------------------------------

        if any(
            marker in normalized
            for marker in (
                "нет любимых сериалов",
                "нет любимого сериала",
                "нет личного мнения",
                "нет предпочтений",
                "нет интересов",
                "никаких интересов",
            )
        ):
            return SelfClaimResult(
                status="UNKNOWN",
                property="self_state_existence",
                value=None,
                polarity="NEGATIVE_EXISTENCE",
                reason=(
                    "Отрицательное утверждение о наличии "
                    "личного свойства требует отдельной "
                    "проверки self-model."
                ),
            )

        # ---------------------------------------------
        # INTEREST
        # ---------------------------------------------

        if any(
            marker in normalized
            for marker in (
                "интерес к ",
                "интересна ",
                "интересно ",
                "интересует ",
                "люблю ",
                "мне нравится ",
            )
        ):
            result = self.validate(
                property_name="interest",
                text=normalized,
            )

            if self._is_negative_text(normalized):
                return self._invert_positive_result(
                    result
                )

            return result

        # ---------------------------------------------
        # PREFERENCE
        # ---------------------------------------------

        if any(
            marker in normalized
            for marker in (
                "предпочитаю ",
                "предпочтение",
                "любимый сериал",
                "любимые сериалы",
                "любимая ",
                "любимый ",
            )
        ):
            result = self.validate(
                property_name="preference",
                text=normalized,
            )

            if self._is_negative_text(normalized):
                return self._invert_positive_result(
                    result
                )

            return result

        return SelfClaimResult(
            status="UNKNOWN",
            property="unknown",
            value=None,
            polarity="UNKNOWN",
            reason=(
                "Тип self-утверждения не удалось "
                "детерминированно определить."
            ),
        )

    def _invert_positive_result(
        self,
        result: SelfClaimResult,
    ) -> SelfClaimResult:

        if result.status == "SUPPORTED":
            return SelfClaimResult(
                status="CONTRADICTED",
                property=result.property,
                value=result.value,
                polarity="NEGATIVE",
                reason=(
                    "Отрицательное утверждение "
                    "противоречит текущему self_state."
                ),
            )

        if result.status == "UNSUPPORTED":
            return SelfClaimResult(
                status="UNKNOWN",
                property=result.property,
                value=None,
                polarity="NEGATIVE",
                reason=(
                    "Отрицательное утверждение невозможно "
                    "подтвердить текущим self_state."
                ),
            )

        return SelfClaimResult(
            status="UNKNOWN",
            property=result.property,
            value=result.value,
            polarity="NEGATIVE",
            reason=result.reason,
        )

    @staticmethod
    def _is_negative_text(
        text: str,
    ) -> bool:
        import re

        return bool(
            re.search(
                r"(?<!\w)(?:не|нет)\s+",
                text,
            )
        ) or any(
            marker in text
            for marker in (
                "никаких ",
                "никогда ",
            )
        )

    def _validate_list(
        self,
        property_name: str,
        text: str,
        values: list,
    ) -> SelfClaimResult:

        normalized = self._normalize(text)

        if not values:
            return SelfClaimResult(
                status="UNSUPPORTED",
                property=property_name,
                value=None,
                polarity="POSITIVE",
                reason=(
                    "В self_state нет ни одного "
                    f"зафиксированного {property_name}."
                ),
            )

        for value in values:
            value_text = self._normalize(
                str(value)
            )

            if (
                value_text
                and self._value_matches(
                    value_text,
                    normalized,
                )
            ):
                return SelfClaimResult(
                    status="SUPPORTED",
                    property=property_name,
                    value=str(value),
                    polarity="POSITIVE",
                    reason=(
                        "Утверждение совпадает "
                        "с текущим self_state."
                    ),
                )

        return SelfClaimResult(
            status="UNSUPPORTED",
            property=property_name,
            value=None,
            reason=(
                "Утверждение о "
                f"{property_name} отсутствует "
                "в текущем self_state."
            ),
        )

    def _validate_capability(
        self,
        text: str,
    ) -> SelfClaimResult:

        normalized = self._normalize(text)

        capabilities = getattr(
            self.agent,
            "capabilities",
            [],
        )

        capability_text = " ".join(
            map(
                str,
                capabilities,
            )
        ).casefold()

        if (
            "умею" in normalized
            or "могу" in normalized
            or "способен" in normalized
        ):
            if capability_text:
                return SelfClaimResult(
                    status="UNKNOWN",
                    property="capability",
                    value=None,
                    polarity="UNKNOWN",
                    reason=(
                        "Возможность существует в runtime, "
                        "но конкретное утверждение ещё "
                        "не связано с capability registry."
                    ),
                )

            return SelfClaimResult(
                status="UNKNOWN",
                property="capability",
                value=None,
                polarity="UNKNOWN",
                reason=(
                    "Capability registry не содержит "
                    "достаточных данных для проверки."
                ),
            )

        return SelfClaimResult(
            status="UNKNOWN",
            property="capability",
            value=None,
            polarity="UNKNOWN",
            reason=(
                "Конкретное capability-утверждение "
                "не распознано."
            ),
        )

    def _validate_internet_access(
        self,
        text: str,
    ) -> SelfClaimResult:

        normalized = self._normalize(text)

        research_capable = False

        capabilities = getattr(
            self.agent,
            "capabilities",
            [],
        )

        for capability in capabilities:
            capability_text = str(
                capability
            ).casefold()

            if (
                "research" in capability_text
                or "internet" in capability_text
                or "web" in capability_text
            ):
                research_capable = True
                break

        if not research_capable:
            return SelfClaimResult(
                status="UNKNOWN",
                property="internet_access",
                value=None,
                reason=(
                    "У EddieAI пока нет "
                    "достаточно явной записи о текущем "
                    "internet capability/access."
                ),
            )

        if (
            "есть доступ" in normalized
            or "имею доступ" in normalized
            or "есть интернет" in normalized
        ):
            return SelfClaimResult(
                status="UNKNOWN",
                property="internet_access",
                value=None,
                reason=(
                    "Наличие research/web capability "
                    "не доказывает фактический текущий "
                    "доступ к интернету."
                ),
            )

        return SelfClaimResult(
            status="UNKNOWN",
            property="internet_access",
            value=None,
            polarity="UNKNOWN",
            reason=(
                "Текущее состояние интернет-доступа "
                "не установлено."
            ),
        )

    @staticmethod
    def _value_matches(
        value: str,
        text: str,
    ) -> bool:

        if value in text:
            return True

        value_tokens = value.split()

        if not value_tokens:
            return False

        for token in value_tokens:
            if len(token) < 5:
                continue

            stem = token[:max(5, len(token) - 2)]

            if stem in text:
                return True

        return False

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        return (
            str(text)
            .casefold()
            .replace("ё", "е")
            .strip()
        )
