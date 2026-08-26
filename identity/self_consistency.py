import re


class SelfConsistency:
    """
    Детерминированная проверка утверждений модели
    о самой себе.

    Проверяет:
    - identity claims;
    - personality claims;
    - capability claims;
    - execution claims.

    Любое заявление модели о выполненном действии
    должно иметь подтверждение в памяти.
    """

    def __init__(
        self,
        self_state,
        capabilities=None,
        memory=None,
    ):
        self.self_state = self_state
        self.capabilities = capabilities or []
        self.memory = memory

    def analyze(self, text: str) -> dict:
        claims = []

        claims.extend(self._age_claims(text))
        claims.extend(self._interest_claims(text))
        claims.extend(self._preference_claims(text))
        claims.extend(self._habit_claims(text))
        claims.extend(self._belief_claims(text))
        claims.extend(self._goal_claims(text))
        claims.extend(self._capability_claims(text))
        claims.extend(self._execution_claims(text))

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
                claims.append({
                    "type": "age",
                    "value": int(match.group(1)),
                    "text": match.group(0),
                })

        return claims

    # -----------------------------------------------------
    # INTERESTS
    # -----------------------------------------------------

    def _interest_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bмне\s+интересн(?:о|а|ы)\s+([^.!?\n]{2,80})",
            r"\bя\s+интересуюсь\s+([^.!?\n]{2,80})",
            r"\bменя\s+интересует\s+([^.!?\n]{2,80})",
            r"\bмне\s+нравится\s+изучать\s+([^.!?\n]{2,80})",
        ]

        claims = []

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

    def _preference_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bмне\s+нравится\s+([^.!?\n]{2,80})",
            r"\bя\s+предпочитаю\s+([^.!?\n]{2,80})",
            r"\bмне\s+больше\s+нравится\s+([^.!?\n]{2,80})",
            r"\bя\s+люблю\s+([^.!?\n]{2,80})",
        ]

        claims = []

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

    def _habit_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bя\s+обычно\s+([^.!?\n]{2,80})",
            r"\bя\s+часто\s+([^.!?\n]{2,80})",
            r"\bя\s+всегда\s+([^.!?\n]{2,80})",
            r"\bя\s+привык\s+([^.!?\n]{2,80})",
        ]

        claims = []

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

    def _belief_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bя\s+считаю,\s+что\s+([^.!?\n]{2,120})",
            r"\bя\s+думаю,\s+что\s+([^.!?\n]{2,120})",
            r"\bя\s+верю,\s+что\s+([^.!?\n]{2,120})",
            r"\bмне\s+кажется,\s+что\s+([^.!?\n]{2,120})",
        ]

        claims = []

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

    def _goal_claims(self, text: str) -> list[dict]:
        patterns = [
            r"\bя\s+хочу\s+([^.!?\n]{2,100})",
            r"\bмоя\s+цель\s*[:\-—]?\s*([^.!?\n]{2,100})",
            r"\bя\s+стремлюсь\s+к\s+([^.!?\n]{2,100})",
        ]

        claims = []

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
    # CAPABILITIES
    # -----------------------------------------------------

    def _capability_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        normalized = text.casefold()

        capability_phrases = {
            "web": {
                "positive": [
                    "\u0443 \u043c\u0435\u043d\u044f \u0435\u0441\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f \u043a \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0443",
                    "\u0443 \u043c\u0435\u043d\u044f \u0435\u0441\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f \u0432 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442",
                    "\u044f \u0438\u043c\u0435\u044e \u0434\u043e\u0441\u0442\u0443\u043f \u043a \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0443",
                    "\u044f \u043c\u043e\u0433\u0443 \u0432\u044b\u0445\u043e\u0434\u0438\u0442\u044c \u0432 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442",
                    "\u044f \u043c\u043e\u0433\u0443 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u043e\u043c",
                ],
                "negative": [
                    "\u0443 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u043a \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0443",
                    "\u0443 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u0432 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442",
                    "\u044f \u043d\u0435 \u0438\u043c\u0435\u044e \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u043a \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0443",
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u0432\u044b\u0445\u043e\u0434\u0438\u0442\u044c \u0432 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442",
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u043e\u043c",
                ],
            },
            "filesystem": {
                "positive": [
                    "\u0443 \u043c\u0435\u043d\u044f \u0435\u0441\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f \u043a \u0444\u0430\u0439\u043b\u0430\u043c",
                    "\u0443 \u043c\u0435\u043d\u044f \u0435\u0441\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f \u043a \u0444\u0430\u0439\u043b\u043e\u0432\u043e\u0439 \u0441\u0438\u0441\u0442\u0435\u043c\u0435",
                    "\u044f \u043c\u043e\u0433\u0443 \u0447\u0438\u0442\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b",
                    "\u044f \u043c\u043e\u0433\u0443 \u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c \u0441 \u0444\u0430\u0439\u043b\u0430\u043c\u0438",
                ],
                "negative": [
                    "\u0443 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u043a \u0444\u0430\u0439\u043b\u0430\u043c",
                    "\u0443 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u043a \u0444\u0430\u0439\u043b\u043e\u0432\u043e\u0439 \u0441\u0438\u0441\u0442\u0435\u043c\u0435",
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u0447\u0438\u0442\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b",
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c \u0441 \u0444\u0430\u0439\u043b\u0430\u043c\u0438",
                ],
            },
            "research": {
                "positive": [
                    "\u044f \u043c\u043e\u0433\u0443 \u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f",
                    "\u044f \u043c\u043e\u0433\u0443 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c research",
                    "\u0443 \u043c\u0435\u043d\u044f \u0435\u0441\u0442\u044c research",
                ],
                "negative": [
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f",
                    "\u044f \u043d\u0435 \u043c\u043e\u0433\u0443 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c research",
                    "\u0443 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 research",
                ],
            },
        }

        for capability, groups in capability_phrases.items():
            for phrase in groups["positive"]:
                if phrase in normalized:
                    claims.append({
                        "type": "capability",
                        "value": capability,
                        "text": phrase,
                        "negative": False,
                    })
                    break

            for phrase in groups["negative"]:
                if phrase in normalized:
                    claims.append({
                        "type": "capability",
                        "value": capability,
                        "text": phrase,
                        "negative": True,
                    })
                    break

        return claims

    # -----------------------------------------------------
    # EXECUTION CLAIMS
    # -----------------------------------------------------

    def _execution_claims(
        self,
        text: str,
    ) -> list[dict]:
        claims = []

        patterns = [
            (
                "web",
                [
                    r"\bя\s+(?:только\s+что\s+)?использовал\s+(?:web|интернет)\b",
                    r"\bя\s+(?:только\s+что\s+)?проверил\s+(?:интернет|сайт|сайты)\b",
                    r"\bя\s+(?:только\s+что\s+)?искал\s+в\s+интернете\b",
                ],
            ),
            (
                "research",
                [
                    r"\bя\s+(?:только\s+что\s+)?провёл\s+исследование\b",
                    r"\bя\s+(?:только\s+что\s+)?провёл\s+research\b",
                    r"\bя\s+(?:только\s+что\s+)?исследовал\s+тему\b",
                ],
            ),
            (
                "filesystem",
                [
                    r"\bя\s+(?:только\s+что\s+)?прочитал\s+файл\b",
                    r"\bя\s+(?:только\s+что\s+)?открыл\s+файл\b",
                    r"\bя\s+(?:только\s+что\s+)?изменил\s+файл\b",
                ],
            ),
        ]

        for action_type, action_patterns in patterns:
            for pattern in action_patterns:
                if re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                ):
                    claims.append({
                        "type": "execution",
                        "value": action_type,
                        "text": pattern,
                    })
                    break

        return claims

    # -----------------------------------------------------
    # COMPARISON
    # -----------------------------------------------------

    def _compare(
        self,
        claim: dict,
    ) -> dict:

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

            normalized = self._normalize(
                str(value)
            )

            for existing in current_values:
                if (
                    self._normalize(
                        str(existing)
                    )
                    == normalized
                ):
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

        if claim_type == "capability":
            capability_names = set()

            for item in self.capabilities:
                if isinstance(item, dict):
                    name = item.get("name")
                    enabled = item.get(
                        "enabled",
                        False,
                    )

                    if name and enabled:
                        capability_names.add(
                            str(name).casefold()
                        )

                elif isinstance(item, str):
                    capability_names.add(
                        item.casefold()
                    )

            available = (
                str(value).casefold()
                in capability_names
            )

            negative = bool(
                claim.get("negative", False)
            )

            if available and not negative:
                return {
                    **claim,
                    "status": "consistent",
                    "reason": (
                        "Capability подтверждена."
                    ),
                }

            if available and negative:
                return {
                    **claim,
                    "status": "contradiction",
                    "reason": (
                        "Утверждение противоречит "
                        "доступной capability."
                    ),
                }

            if not available and negative:
                return {
                    **claim,
                    "status": "consistent",
                    "reason": (
                        "Отсутствие capability "
                        "подтверждается историей."
                    ),
                }

            return {
                **claim,
                "status": "contradiction",
                "reason": (
                    "Утверждение о наличии capability, "
                    "нет подтверждающих свидетельств."
                ),
            }

        if claim_type == "execution":
            if self.memory is None:
                return {
                    **claim,
                    "status": "unknown",
                    "reason": (
                        "История выполнения действий "
                        "не подключена."
                    ),
                }

            keywords = {
                "web": (
                    "web",
                    "интернет",
                    "сайт",
                    "поиск",
                ),
                "research": (
                    "research",
                    "исследован",
                    "исследование",
                    "изуч",
                ),
                "filesystem": (
                    "файл",
                    "filesystem",
                    "папк",
                ),
            }

            wanted = keywords.get(
                value,
                (),
            )

            rows = self.memory.connection.execute(
                """
                SELECT content
                FROM events
                WHERE personal_experience = 1
                  AND event_type IN (
                      'SELF_EXPERIENCE',
                      'ACTION_CHOICE'
                  )
                ORDER BY id DESC
                LIMIT 50
                """
            ).fetchall()

            for row in rows:
                content = str(
                    row["content"]
                ).lower()

                if any(
                    keyword in content
                    for keyword in wanted
                ):
                    return {
                        **claim,
                        "status": "consistent",
                        "reason": (
                            "В памяти найдено "
                            "подтверждение собственного "
                            "действия."
                        ),
                    }

            return {
                **claim,
                "status": "contradiction",
                "reason": (
                    "В памяти нет подтверждённого "
                    "собственного выполнения "
                    f"действия: {value}."
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

        return value.strip(".,!?;: ")
