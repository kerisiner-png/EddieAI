import re


class SelfConsistency:
    """
    Детерминированная проверка утверждений модели о самой себе.

    На этом этапе система работает с распространёнными
    конструкциями русского языка. Позже сюда можно подключить
    отдельный semantic claim extractor.
    """

    def __init__(self, self_state):
        self.self_state = self_state

    def analyze(self, text: str) -> dict:
        claims = []

        claims.extend(self._age_claims(text))
        claims.extend(self._interest_claims(text))
        claims.extend(self._preference_claims(text))
        claims.extend(self._habit_claims(text))
        claims.extend(self._belief_claims(text))
        claims.extend(self._goal_claims(text))

        contradictions = []
        proposals = []

        for claim in claims:
            result = self._compare(claim)

            if result["status"] == "contradiction":
                contradictions.append(result)
            elif result["status"] == "new":
                proposals.append(result)

        return {
            "claims": claims,
            "contradictions": contradictions,
            "proposals": proposals,
        }

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    def _age_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bмне\s+(\d{1,3})\s+лет\b",
            r"\bмой\s+возраст\s*[:\-—]?\s*(\d{1,3})\b",
            r"\bя\s+(\d{1,3})[- ]летн",
        ]

        claims = []

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                age = int(match.group(1))

                claims.append({
                    "type": "age",
                    "value": age,
                    "text": match.group(0),
                })

        return claims

    # -----------------------------------------------------
    # INTERESTS
    # -----------------------------------------------------

    def _interest_claims(self, text: str) -> list[dict]:
        claims = []

        patterns = [
            r"\bмне\s+интересн(?:о|а|ы)\s+([^.!?\n]{2,80})",
            r"\bя\s+интересуюсь\s+([^.!?\n]{2,80})",
            r"\bменя\s+интересует\s+([^.!?\n]{2,80})",
            r"\bмне\s+нравится\s+изучать\s+([^.!?\n]{2,80})",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                value = match.group(1).strip(" ,:;")

                if value:
                    claims.append({
                        "type": "interest",
                        "value": value,
                        "text": match.group(0),
                    })

        return claims

    # -----------------------------------------------------
    # PREFERENCES
    # -----------------------------------------------------

    def _preference_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        patterns = [
            r"\bмне\s+нравится\s+([^.!?\n]{2,80})",
            r"\bя\s+предпочитаю\s+([^.!?\n]{2,80})",
            r"\bмне\s+больше\s+нравится\s+([^.!?\n]{2,80})",
            r"\bя\s+люблю\s+([^.!?\n]{2,80})",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                value = match.group(1).strip(" ,:;")

                if value:
                    claims.append({
                        "type": "preference",
                        "value": value,
                        "text": match.group(0),
                    })

        return claims

    # -----------------------------------------------------
    # HABITS
    # -----------------------------------------------------

    def _habit_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        patterns = [
            r"\bя\s+обычно\s+([^.!?\n]{2,80})",
            r"\bя\s+часто\s+([^.!?\n]{2,80})",
            r"\bя\s+всегда\s+([^.!?\n]{2,80})",
            r"\bя\s+привык\s+([^.!?\n]{2,80})",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                value = match.group(1).strip(" ,:;")

                if value:
                    claims.append({
                        "type": "habit",
                        "value": value,
                        "text": match.group(0),
                    })

        return claims

    # -----------------------------------------------------
    # BELIEFS
    # -----------------------------------------------------

    def _belief_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        patterns = [
            r"\bя\s+считаю,\s+что\s+([^.!?\n]{2,120})",
            r"\bя\s+думаю,\s+что\s+([^.!?\n]{2,120})",
            r"\bя\s+верю,\s+что\s+([^.!?\n]{2,120})",
            r"\bмне\s+кажется,\s+что\s+([^.!?\n]{2,120})",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                value = match.group(1).strip(" ,:;")

                if value:
                    claims.append({
                        "type": "belief",
                        "value": value,
                        "text": match.group(0),
                    })

        return claims

    # -----------------------------------------------------
    # GOALS
    # -----------------------------------------------------

    def _goal_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        patterns = [
            r"\bя\s+хочу\s+([^.!?\n]{2,100})",
            r"\bмоя\s+цель\s*[:\-—]?\s*([^.!?\n]{2,100})",
            r"\bя\s+стремлюсь\s+к\s+([^.!?\n]{2,100})",
        ]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            ):
                value = match.group(1).strip(" ,:;")

                if value:
                    claims.append({
                        "type": "goal",
                        "value": value,
                        "text": match.group(0),
                    })

        return claims

    # -----------------------------------------------------
    # COMPARISON
    # -----------------------------------------------------

    def _compare(self, claim: dict) -> dict:
        claim_type = claim["type"]
        value = claim["value"]

        if claim_type == "age":
            current_age = self.self_state.get("age")

            if value != current_age:
                return {
                    **claim,
                    "status": "contradiction",
                    "reason": (
                        f"Текущее состояние указывает возраст "
                        f"{current_age}, а ответ утверждает {value}."
                    ),
                }

            return {
                **claim,
                "status": "consistent",
            }

        if claim_type in {
            "interest",
            "preference",
            "habit",
            "belief",
            "goal",
        }:
            field = {
                "interest": "interests",
                "preference": "preferences",
                "habit": "habits",
                "belief": "beliefs",
                "goal": "goals",
            }[claim_type]

            current_values = self.self_state.get(
                field,
                [],
            )

            normalized = self._normalize(value)

            for existing in current_values:
                if self._normalize(str(existing)) == normalized:
                    return {
                        **claim,
                        "status": "consistent",
                    }

            return {
                **claim,
                "status": "new",
                "reason": (
                    f"Это новое утверждение типа "
                    f"{claim_type}, которого пока нет "
                    f"в self-state."
                ),
            }

        return {
            **claim,
            "status": "unknown",
        }

    def _normalize(self, value: str) -> str:
        value = value.lower().strip()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        value = value.strip(".,!?;: ")

        return value
