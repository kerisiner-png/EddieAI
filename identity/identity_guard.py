import re


class IdentityGuard:
    def __init__(self, self_state):
        self.self_state = self_state

    def check(self, text: str) -> list[str]:
        if self.self_state.get("name") is not None:
            return []

        violations = []
        text = " ".join(text.strip().split())

        self._check_explicit_name(text, violations)

        if violations:
            return violations

        self._check_identity_claim(text, violations)

        if violations:
            return violations

        self._check_naming_verbs(text, violations)

        return violations

    def _check_explicit_name(self, text, violations):
        patterns = [
            r"\bменя\s+зовут\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bмо[её]\s+имя\s*[:\-—]?\s*([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bя\s+называюсь\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bзови\s+меня\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
        ]

        self._find_matches(text, patterns, violations)

    def _check_identity_claim(self, text, violations):
        patterns = [
            r"\bя\s*[—–-]\s*([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bя\s+являюсь\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
        ]

        self._find_matches(text, patterns, violations)

    def _check_naming_verbs(self, text, violations):
        patterns = [
            r"\bя\s+(?:буду\s+)?(?:именоваться|именуюсь|зваться|называться)\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bменя\s+называют\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bменя\s+зовут\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\b(?:мой|моя)\s+(?:код|система|программа)\s+зов(?:ё|е)тся\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\b(?:мой|моя)\s+(?:код|система|программа)\s+зов(?:ё|е)т\s+меня\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\b(?:мой|моя)\s+(?:код|система|программа)\s+называет\s+меня\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
            r"\bя\s+известен\s+как\s+([А-ЯЁA-Z][А-ЯЁA-Za-zЁё\-]{1,30})\b",
        ]

        self._find_matches(text, patterns, violations)

    def _find_matches(self, text, patterns, violations):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if not match:
                continue

            claimed = match.group(1).strip()

            if self._valid_name(claimed):
                violations.append(
                    f"UNAUTHORIZED_NAME_CLAIM: {claimed}"
                )
                return

    def _valid_name(self, value: str) -> bool:
        excluded = {
            "не",
            "пока",
            "себя",
            "тобой",
            "мной",
            "собой",
            "человеком",
            "искусственным",
            "цифровым",
            "просто",
            "так",
            "буду",
        }

        return (
            len(value) >= 2
            and value.lower() not in excluded
        )

    def sanitize(self, text: str) -> str:
        return (
            "Пока я не выбрал себе имя. "
            "Я могу рассуждать о разных вариантах, "
            "но ни один из них ещё не является моим именем."
        )
