import re


class EpistemicIntentDetector:
    """
    Определяет, является ли текущая реплика пользователя
    эпистемическим follow-up к собственному утверждению EddieAI.

    Ничего не изменяет в состоянии агента.
    """

    INTENT_PATTERNS = {
        "QUESTION_ORIGIN": (
            "откуда ты это узнал",
            "откуда ты это знаешь",
            "откуда у тебя эта информация",
            "откуда это взялось",
            "как ты это узнал",
            "как ты об этом узнал",
        ),

        "QUESTION_EVIDENCE": (
            "на чём основано",
            "на чем основано",
            "какие у тебя доказательства",
            "какие у тебя основания",
            "есть ли у тебя доказательства",
            "есть ли у тебя основания",
            "ты это проверял",
            "ты это проверил",
            "это проверено",
        ),

        "QUESTION_OWNERSHIP": (
            "это твоё мнение",
            "это твое мнение",
            "это твоё убеждение",
            "это твое убеждение",
            "это твоё собственное убеждение",
            "это твое собственное убеждение",
            "это твой собственный вывод",
            "это твой вывод",
            "это твоё собственное мнение",
            "это твое собственное мнение",
            "ты сам так решил",
            "ты сам к этому пришёл",
            "ты сам к этому пришел",
            "ты сам так считаешь",
            "ты сам так думаешь",
        ),

        "QUESTION_CONFIDENCE": (
            "ты уверен",
            "насколько ты уверен",
            "ты точно уверен",
            "ты действительно уверен",
            "почему ты уверен",
        ),

        "QUESTION_REASONING": (
            "почему ты так думаешь",
            "почему ты так считаешь",
            "почему ты думаешь",
            "почему ты считаешь",
            "как ты к этому пришёл",
            "как ты к этому пришел",
            "как ты это вывел",
            "почему ты сделал такой вывод",
        ),

        "CHALLENGE_CLAIM": (
            "ты уверен что",
            "ты правда считаешь что",
            "ты действительно считаешь что",
            "ты не ошибся",
            "может это ошибка",
            "а точно ли",
            "это точно",
        ),

        "QUESTION_CONTRADICTION": (
            "это не противоречит",
            "ты сам себе не противоречишь",
            "почему это не противоречит",
            "а разве это не противоречит",
            "у тебя тут противоречие",
        ),
    }

    @staticmethod
    def normalize(text: str) -> str:
        return " ".join(
            re.sub(
                r"[^\w\sёЁ?!-]",
                " ",
                str(text or "").casefold(),
            ).split()
        )

    @classmethod
    def detect(
        cls,
        message: str,
    ) -> dict:
        text = cls.normalize(
            message
        )

        for intent, patterns in (
            cls.INTENT_PATTERNS.items()
        ):
            for pattern in patterns:
                normalized_pattern = (
                    cls.normalize(pattern)
                )

                if (
                    normalized_pattern
                    in text
                ):
                    return {
                        "detected": True,
                        "intent": intent,
                        "pattern": pattern,
                    }

        # Общие короткие epistemic follow-ups.
        generic = (
            "почему",
            "зачем",
            "откуда",
            "на чём",
            "на чем",
            "как ты узнал",
            "как ты решил",
            "почему так",
        )

        if (
            len(text.split()) <= 8
            and any(
                marker in text
                for marker in generic
            )
        ):
            return {
                "detected": True,
                "intent": "GENERIC_EPISTEMIC_FOLLOWUP",
                "pattern": None,
            }

        return {
            "detected": False,
            "intent": None,
            "pattern": None,
        }
