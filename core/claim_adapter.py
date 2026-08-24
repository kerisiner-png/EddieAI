from core.claim_engine import Claim


class ClaimAdapter:

    @staticmethod
    def from_dict(
        data: dict,
        *,
        fallback_text: str = "",
        speaker: str = "SELF",
        user_name: str | None = None,
    ) -> Claim:

        subject = data.get(
            "subject"
        )

        owner = (
            ClaimAdapter.resolve_owner(
                subject=subject,
                speaker=speaker,
                user_name=user_name,
            )
        )

        return Claim(
            owner=owner,
            predicate=str(
                data.get(
                    "predicate",
                    "unknown",
                )
            ).strip(),
            value=(
                None
                if data.get("value") is None
                else str(
                    data.get("value")
                ).strip()
            ),
            polarity=str(
                data.get(
                    "polarity",
                    "UNKNOWN",
                )
            ).upper(),
            certainty=str(
                data.get(
                    "certainty",
                    "UNKNOWN",
                )
            ).upper(),
            temporal_scope=str(
                data.get(
                    "temporal_scope",
                    "UNKNOWN",
                )
            ).upper(),
            text=str(
                data.get(
                    "text",
                    fallback_text,
                )
            ).strip(),
        )

    @classmethod
    def from_response(
        cls,
        response: dict,
        *,
        speaker: str = "SELF",
        user_name: str | None = None,
    ) -> list[Claim]:

        answer = str(
            response.get(
                "answer",
                "",
            )
        )

        claims = response.get(
            "claims",
            [],
        )

        if not isinstance(
            claims,
            list,
        ):
            return []

        result = []

        for item in claims:
            if not isinstance(
                item,
                dict,
            ):
                continue

            result.append(
                cls.from_dict(
                    item,
                    fallback_text=answer,
                    speaker=speaker,
                    user_name=user_name,
                )
            )

        return result

    @staticmethod
    def resolve_owner(
        *,
        subject,
        speaker: str,
        user_name: str | None,
    ) -> str:

        subject_text = (
            ""
            if subject is None
            else str(
                subject
            )
            .casefold()
            .replace("ё", "е")
            .strip()
        )

        user_name_normalized = (
            ""
            if user_name is None
            else str(
                user_name
            )
            .casefold()
            .replace("ё", "е")
            .strip()
        )

        self_markers = (
            "я",
            "мне",
            "меня",
            "мой",
            "моя",
            "мои",
            "у меня",
        )

        user_markers = (
            "ты",
            "тебе",
            "тебя",
            "твой",
            "твоя",
            "твои",
            "у тебя",
        )

        if subject_text in self_markers:
            return speaker

        if subject_text in user_markers:
            if speaker == "SELF":
                return "USER"

            return "SELF"

        if (
            user_name_normalized
            and subject_text
            == user_name_normalized
        ):
            return "USER"

        # В ответе EddieAI явно названный сторонний
        # субъект не должен автоматически становиться SELF.
        if subject_text:
            if speaker == "SELF":
                return "EXTERNAL"

        # Если субъект не был указан явно,
        # используем говорящего как fallback.
        if speaker in {
            "SELF",
            "USER",
        }:
            return speaker

        return "UNKNOWN"
