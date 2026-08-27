from dataclasses import dataclass
import re


@dataclass(frozen=True)
class OwnershipClaim:
    owner: str
    property: str
    polarity: str
    text: str


class OwnershipResolver:
    """
    Определяет владельца утверждений в разговоре.

    OWNER:
        SELF
        USER
        EXTERNAL
        UNKNOWN

    Слой не генерирует ответы и не исправляет текст.
    Он только извлекает вероятного владельца свойства
    и обнаруживает смену субъекта между user message
    и generated answer.
    """

    SELF_MARKERS = (
        "ты ",
        "ты,",
        "ты.",
        "ты?",
        "у тебя",
        "тебе",
        "тебя",
        "твой",
        "твоя",
        "твои",
    )

    USER_MARKERS = (
        "я ",
        "я,",
        "я.",
        "я?",
        "у меня",
        "мне",
        "меня",
        "мой",
        "моя",
        "мои",
    )

    PROPERTY_PATTERNS = {
        "internet_access": (
            "доступ к интернету",
            "доступ в интернет",
            "интернет",
        ),
        "interest": (
            "интерес",
            "интересно",
            "нравится",
            "люблю",
        ),
        "preference": (
            "предпочитаешь",
            "предпочитаю",
            "предпочтение",
        ),
        "goal": (
            "хочешь",
            "хочу",
            "цель",
            "цели",
            "стремишься",
            "стремлюсь",
        ),
        "belief": (
            "считаешь",
            "считаю",
            "веришь",
            "верю",
            "убеждение",
            "убеждения",
            "мнение",
        ),
        "capability": (
            "умеешь",
            "умею",
            "можешь",
            "могу",
            "способен",
            "способна",
            "возможность",
            "возможности",
        ),
        "memory": (
            "помнишь",
            "помню",
            "память",
            "вспоминаешь",
            "вспоминаю",
        ),
        "experience": (
            "делал",
            "делала",
            "делал ранее",
            "делала ранее",
            "переживал",
            "переживала",
            "опыт",
            "видел",
            "видела",
        ),
        "identity": (
            "кто ты",
            "кто я",
            "твой возраст",
            "мой возраст",
            "твоя личность",
            "моя личность",
        ),
        "emotional_state": (
            "чувствуешь",
            "чувствую",
            "тебе грустно",
            "мне грустно",
            "тебе интересно",
            "мне интересно",
            "тебе нравится",
            "мне нравится",
        ),
        "relationship": (
            "твой друг",
            "твоя сестра",
            "твой создатель",
            "мой друг",
            "моя сестра",
            "мой создатель",
            "отношение",
            "отношения",
        ),
        "experience": (
            "пробовал смотреть",
            "смотрел",
            "смотрела",
            "смотрел ранее",
            "видел",
            "видела",
            "смотрю",
            "читал",
            "читала",
            "слушал",
            "слушала",
            "играл",
            "играла",
            "пользовался",
            "пользовалась",
            "посещал",
            "посещала",
        ),
    }

    EXTERNAL_MARKERS = (
        "nasa",
        "google",
        "википедия",
        "сайт",
        "статья",
        "источник",
        "учёные",
        "ученые",
        "компания",
        "организация",
        "сериал",
        "фильм",
    )

    def analyze(
        self,
        *,
        user_message: str,
        answer: str,
    ) -> dict:
        user_claims = self.extract_claims(
            user_message,
            speaker="USER",
        )
        answer_claims = self.extract_claims(
            answer,
            speaker="SELF",
        )

        violations = []

        expected_owner = (
            self._expected_owner_from_message(
                user_message
            )
        )

        if expected_owner is not None:
            for claim in answer_claims:
                if claim.property == "unknown":
                    continue

                if (
                    claim.owner != expected_owner
                    and claim.owner != "UNKNOWN"
                ):
                    violations.append({
                        "type": "OWNERSHIP_MISMATCH",
                        "expected_owner": expected_owner,
                        "actual_owner": claim.owner,
                        "property": claim.property,
                        "answer_text": claim.text,
                        "user_message": user_message,
                    })

        return {
            "user_claims": user_claims,
            "answer_claims": answer_claims,
            "violations": violations,
            "expected_owner": expected_owner,
        }

    def extract_claims(
        self,
        text: str,
        speaker: str = "UNKNOWN",
    ) -> list[OwnershipClaim]:

        normalized = self._normalize(
            text
        )

        if not normalized:
            return []

        # Разделяем длинный ответ на отдельные
        # предложения. Это позволяет обнаруживать
        # несколько независимых claims.
        sentences = [
            part.strip()
            for part in re.split(
                r"(?<=[.!?])\s+",
                normalized,
            )
            if part.strip()
        ]

        if not sentences:
            sentences = [normalized]

        claims = []

        for sentence in sentences:

            if sentence.endswith("?"):
                continue

            owner = self._infer_owner(
                sentence,
                speaker=speaker,
            )

            properties_found = []

            for property_name, markers in (
                self.PROPERTY_PATTERNS.items()
            ):
                for marker in markers:
                    if marker in sentence:
                        properties_found.append(
                            property_name
                        )
                        break

            if not properties_found:
                claims.append(
                    OwnershipClaim(
                        owner=owner,
                        property="unknown",
                        polarity="UNKNOWN",
                        text=sentence,
                    )
                )
                continue

            polarity = (
                "NEGATIVE"
                if self._is_negative(
                    sentence,
                    "",
                )
                else "POSITIVE"
            )

            for property_name in properties_found:
                claims.append(
                    OwnershipClaim(
                        owner=owner,
                        property=property_name,
                        polarity=polarity,
                        text=sentence,
                    )
                )

        return claims

    def _expected_owner_from_message(
        self,
        text: str,
    ) -> str | None:
        normalized = self._normalize(
            text
        )

        self_hits = sum(
            marker in normalized
            for marker in self.SELF_MARKERS
        )

        user_hits = sum(
            marker in normalized
            for marker in self.USER_MARKERS
        )

        is_question = "?" in normalized

        if (
            is_question
            and self_hits > 0
        ):
            return "SELF"

        if self_hits > user_hits and self_hits > 0:
            return "SELF"

        if user_hits > self_hits and user_hits > 0:
            return "USER"

        return None

    def _infer_owner(
        self,
        text: str,
        speaker: str = "UNKNOWN",
    ) -> str:

        normalized = self._normalize(
            text
        )

        # ---------------------------------------------
        # SPEAKER CONTEXT
        # ---------------------------------------------
        #
        # В сгенерированном ответе "я / у меня / мой"
        # принадлежит EddieAI, потому что speaker=SELF.
        #
        # В пользовательской реплике "я / у меня / мой"
        # принадлежит USER, потому что speaker=USER.
        #

        if speaker == "SELF":
            if any(
                marker in normalized
                for marker in (
                    "я ",
                    "я,",
                    "я.",
                    "я?",
                    "у меня",
                    "мне ",
                    "меня ",
                    "мой ",
                    "моя ",
                    "мои ",
                )
            ):
                return "SELF"

            if any(
                marker in normalized
                for marker in (
                    "ты ",
                    "ты,",
                    "ты.",
                    "ты?",
                    "у тебя",
                    "тебе ",
                    "тебя ",
                    "твой ",
                    "твоя ",
                    "твои ",
                )
            ):
                return "SELF"

        if speaker == "USER":
            if any(
                marker in normalized
                for marker in (
                    "я ",
                    "я,",
                    "я.",
                    "я?",
                    "у меня",
                    "мне ",
                    "меня ",
                    "мой ",
                    "моя ",
                    "мои ",
                )
            ):
                return "USER"

            if any(
                marker in normalized
                for marker in (
                    "ты ",
                    "ты,",
                    "ты.",
                    "ты?",
                    "у тебя",
                    "тебе ",
                    "тебя ",
                    "твой ",
                    "твоя ",
                    "твои ",
                )
            ):
                return "SELF"

        # ---------------------------------------------
        # GENERIC FALLBACK
        # ---------------------------------------------

        self_hits = sum(
            marker in normalized
            for marker in self.SELF_MARKERS
        )

        user_hits = sum(
            marker in normalized
            for marker in self.USER_MARKERS
        )

        if self_hits > user_hits and self_hits > 0:
            return "SELF"

        if user_hits > self_hits and user_hits > 0:
            return "USER"

        if any(
            marker in normalized
            for marker in self.EXTERNAL_MARKERS
        ):
            return "EXTERNAL"

        if speaker in {
            "SELF",
            "USER",
        }:
            return speaker

        return "UNKNOWN"

    @staticmethod
    def _is_negative(
        text: str,
        marker: str,
    ) -> bool:
        index = text.find(marker)

        if index < 0:
            return False

        prefix = text[
            max(0, index - 30):
            index
        ]

        return any(
            negation in prefix
            for negation in (
                "не ",
                "нет ",
                "никак ",
                "никогда ",
            )
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        normalized = (
            str(text)
            .casefold()
            .replace("ё", "е")
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized.strip()
