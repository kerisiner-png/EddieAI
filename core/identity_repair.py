from dataclasses import dataclass


@dataclass(frozen=True)
class RepairResult:
    repaired: bool
    answer: str
    strategy: str
    reason: str


class IdentityRepairStrategy:
    """
    Детерминированный repair для нарушений self-consistency.

    Не использует LLM.

    Стратегии:
        OWNERSHIP_MISMATCH
        UNSUPPORTED_SELF_CLAIM
        CONTRADICTED_SELF_CLAIM

    UNKNOWN не исправляется автоматически.
    """

    def __init__(self, agent):
        self.agent = agent

    def repair(
        self,
        *,
        answer: str,
        user_message: str,
        violations: list,
    ) -> RepairResult:

        if not violations:
            return RepairResult(
                repaired=False,
                answer=answer,
                strategy="NONE",
                reason="Нарушений нет.",
            )

        kinds = {
            violation.kind
            for violation in violations
        }

        # ---------------------------------------------
        # OWNERSHIP
        # ---------------------------------------------

        if "OWNERSHIP_MISMATCH" in kinds:
            repaired = self._repair_ownership(
                answer
            )

            if repaired != answer:
                return RepairResult(
                    repaired=True,
                    answer=repaired,
                    strategy="OWNERSHIP_DETERMINISTIC",
                    reason=(
                        "Субъект утверждения был "
                        "скорректирован детерминированно."
                    ),
                )

        # ---------------------------------------------
        # UNSUPPORTED SELF CLAIM
        # ---------------------------------------------

        if "UNSUPPORTED_SELF_CLAIM" in kinds:
            repaired = self._repair_unsupported_self_claim(
                answer
            )

            if repaired != answer:
                return RepairResult(
                    repaired=True,
                    answer=repaired,
                    strategy="UNSUPPORTED_SELF_CLAIM",
                    reason=(
                        "Неподтверждённое утверждение "
                        "о личности заменено на "
                        "эпистемически безопасную формулировку."
                    ),
                )

        # ---------------------------------------------
        # CONTRADICTED SELF CLAIM
        # ---------------------------------------------

        if "CONTRADICTED_SELF_CLAIM" in kinds:
            repaired = self._repair_contradiction(
                answer
            )

            if repaired != answer:
                return RepairResult(
                    repaired=True,
                    answer=repaired,
                    strategy="CONTRADICTION",
                    reason=(
                        "Утверждение приведено "
                        "в соответствие с текущей self-model."
                    ),
                )

        # ---------------------------------------------
        # NO SAFE DETERMINISTIC REPAIR
        # ---------------------------------------------

        return RepairResult(
            repaired=False,
            answer=answer,
            strategy="NO_SAFE_REPAIR",
            reason=(
                "Для данного нарушения нет "
                "безопасного детерминированного repair."
            ),
        )

    def _repair_ownership(
        self,
        answer: str,
    ) -> str:

        text = answer

        replacements = (
            ("у вас есть", "у меня есть"),
            ("у вас уже есть", "у меня уже есть"),
            ("у тебя есть", "у меня есть"),
            ("у тебя уже есть", "у меня уже есть"),
            ("вам нужно", "мне нужно"),
            ("тебе нужно", "мне нужно"),
            ("ты не умеешь", "я пока не умею"),
            ("ты пока не умеешь", "я пока не умею"),
            ("ты можешь", "я могу"),
            ("ты умеешь", "я умею"),
            ("тебе нравится", "мне нравится"),
            ("тебе интересно", "мне интересно"),
            ("у тебя нет", "у меня нет"),
        )

        lowered = text.casefold()

        for old, new in replacements:
            index = lowered.find(old)

            if index < 0:
                continue

            text = (
                text[:index]
                + new
                + text[
                    index + len(old):
                ]
            )

            lowered = text.casefold()

        return text

    def _repair_unsupported_self_claim(
        self,
        answer: str,
    ) -> str:

        lowered = answer.casefold()

# Прямое утверждение о несуществующем
        # preference/interest.
        if (
            "люблю сериал" in lowered
            or "любимый сериал" in lowered
            or "любимые сериалы" in lowered
        ):
            return (
                "У меня пока нет "
                "зафиксированного любимого сериала."
            )

        return answer

    def _repair_contradiction(
        self,
        answer: str,
    ) -> str:

        lowered = answer.casefold()

        if (
            "не интересна астрофизика" in lowered
            or "не интересна астрофизике" in lowered
            or "не интересуюсь астрофизикой" in lowered
        ):
            return (
                "Это не совпадает с моей текущей "
                "self-model: астрофизика сейчас "
                "зафиксирована у меня как интерес."
            )

        return (
            "Это противоречит моей текущей self-model. "
            "Сейчас я не могу подтвердить такое "
            "утверждение о себе."
        )
