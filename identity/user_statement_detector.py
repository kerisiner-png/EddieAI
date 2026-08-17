import re


class UserStatementDetector:
    INTEREST_PATTERNS = [
        r"\bмне (?:очень )?нравится (?P<value>.+)",
        r"\bя люблю (?P<value>.+)",
        r"\bмне интересен (?P<value>.+)",
        r"\bмне интересна (?P<value>.+)",
        r"\bмне интересны (?P<value>.+)",
        r"\bмне интересно (?P<value>.+)",
        r"\bя интересуюсь (?P<value>.+)",
        r"\bя увлекаюсь (?P<value>.+)",
        r"\bя часто читаю про (?P<value>.+)",
        r"\bя часто изучаю (?P<value>.+)",
        r"\bмне нравится изучать (?P<value>.+)",
    ]

    PREFERENCE_PATTERNS = [
        r"\bя предпочитаю (?P<value>.+)",
        r"\bмне больше нравится (?P<value>.+)",
        r"\bя больше люблю (?P<value>.+)",
    ]

    HABIT_PATTERNS = [
        r"\bя обычно (?P<value>.+)",
        r"\bя часто (?P<value>.+)",
        r"\bя регулярно (?P<value>.+)",
        r"\bя всегда (?P<value>.+)",
    ]

    EXPLICIT_HABIT_PREFIXES = (
        "я часто ",
        "я обычно ",
        "я регулярно ",
        "я всегда ",
    )

    def detect(
        self,
        message: str,
    ):
        text = self._clean(message)

        if not text:
            return []

        results = []

        self._match_patterns(
            text,
            self.INTEREST_PATTERNS,
            "interest",
            results,
        )

        self._match_patterns(
            text,
            self.PREFERENCE_PATTERNS,
            "preference",
            results,
        )

        self._match_patterns(
            text,
            self.HABIT_PATTERNS,
            "habit",
            results,
        )

        lowered = text.lower()

        if lowered.startswith(
            self.EXPLICIT_HABIT_PREFIXES
        ):
            results = [
                item
                for item in results
                if item["category"] != "interest"
            ]

        return self._deduplicate(results)

    def _match_patterns(
        self,
        text,
        patterns,
        category,
        results,
    ):
        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            value = self._normalize(
                match.group("value")
            )

            if not value:
                continue

            results.append({
                "category": category,
                "value": value,
                "confidence": self._confidence(
                    category
                ),
                "source": "USER_STATEMENT",
                "text": text,
            })

    def _confidence(
        self,
        category: str,
    ):
        if category == "interest":
            return 0.95

        if category == "preference":
            return 0.90

        if category == "habit":
            return 0.85

        return 0.75

    def _normalize(
        self,
        value: str,
    ):
        value = value.strip()

        value = re.sub(
            r"[.!?,;:]+$",
            "",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip(
            " \"'«»"
        )

    def _clean(
        self,
        message: str,
    ):
        if not isinstance(
            message,
            str,
        ):
            return ""

        return re.sub(
            r"\s+",
            " ",
            message,
        ).strip()

    def _deduplicate(
        self,
        results,
    ):
        output = []
        seen = set()

        for item in results:
            key = (
                item["category"],
                item["value"].lower(),
            )

            if key in seen:
                continue

            seen.add(key)
            output.append(item)

        return output
