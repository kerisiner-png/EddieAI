import re


class ResponsePacketSanitizer:

    PROTOCOL_PATTERNS = (
        r"\s*claims\s*=\s*\[\s*\]\s*\}\s*$",
        r"\s*claims\s*:\s*\[\s*\]\s*\}\s*$",
        r"\s*```(?:json)?\s*$",
        r"\s*```\s*$",
    )

    @classmethod
    def clean(
        cls,
        packet: dict,
    ) -> dict:

        cleaned = dict(packet)

        answer = str(
            cleaned.get(
                "answer",
                "",
            )
        ).strip()

        answer = cls.clean_answer(
            answer
        )

        cleaned["answer"] = answer

        return cleaned

    @classmethod
    def clean_answer(
        cls,
        answer: str,
    ) -> str:

        text = str(
            answer or ""
        ).strip()

        for pattern in cls.PROTOCOL_PATTERNS:
            text = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()

        return text
