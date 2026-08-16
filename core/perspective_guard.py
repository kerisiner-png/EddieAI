import re


class PerspectiveGuard:
    """
    Проверяет, не перепутала ли модель пользователя с собой.

    Сейчас работает на наиболее очевидных конструкциях.
    Позже станет частью общего self-consistency слоя.
    """

    def check_user_query(
        self,
        text: str,
        user_state,
    ) -> list[str]:

        violations = []

        user_name = user_state.get("name")
        user_age = user_state.get("age")

        if user_name:
            patterns = [
                rf"\bя\s*,?\s*{re.escape(user_name)}\b",
                rf"\bя\s+{re.escape(user_name)}\b",
                rf"\bменя\s+зовут\s+{re.escape(user_name)}\b",
            ]

            for pattern in patterns:
                if re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                ):
                    violations.append(
                        "USER_IDENTITY_ASSIGNED_TO_SELF"
                    )
                    break

        if user_age is not None:
            age_patterns = [
                rf"\bмне\s+{user_age}\s+лет\b",
                rf"\bмне\s+{user_age}\b",
                rf"\bмой\s+возраст\s+{user_age}\b",
            ]

            for pattern in age_patterns:
                if re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                ):
                    violations.append(
                        "USER_AGE_ASSIGNED_TO_SELF"
                    )
                    break

        return violations

    def has_violation(
        self,
        text: str,
        user_state,
    ) -> bool:
        return bool(
            self.check_user_query(
                text,
                user_state,
            )
        )
