from core.ownership_resolver import OwnershipResolver
import re


class PerspectiveGuard:
    def __init__(self):
        self.ownership_resolver = OwnershipResolver()

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

    def check_ownership(
        self,
        text: str,
        user_message: str,
    ) -> list[str]:

        result = (
            self.ownership_resolver.analyze(
                user_message=user_message,
                answer=text,
            )
        )

        return [
            item["type"]
            for item in result["violations"]
        ]

    def check_self_reference(
        self,
        text: str,
        user_message: str,
    ) -> list[str]:

        violations = []

        message = str(
            user_message
        ).casefold()

        answer = str(
            text
        ).casefold()

        # ---------------------------------------------
        # INTERNET / TOOL ACCESS
        # ---------------------------------------------

        internet_context = (
            "интернет" in message
            or "доступ к интернету" in message
            or "доступ в интернет" in message
        )

        if internet_context:
            user_ownership_claim = any(
                phrase in message
                for phrase in (
                    "у тебя уже есть доступ",
                    "у тебя есть доступ",
                    "у тебя появился доступ",
                    "ты уже имеешь доступ",
                    "ты имеешь доступ",
                )
            )

            if user_ownership_claim:
                answer_inverts_to_user = any(
                    phrase in answer
                    for phrase in (
                        "у тебя уже есть доступ",
                        "у тебя есть доступ",
                        "у тебя появился доступ",
                        "ты уже имеешь доступ",
                        "ты имеешь доступ",
                        "ты не умеешь использовать интернет",
                        "ты пока не умеешь использовать интернет",
                        "тебе нужно научиться пользоваться интернетом",
                    )
                )

                answer_self_owned = any(
                    phrase in answer
                    for phrase in (
                        "у меня уже есть доступ",
                        "у меня есть доступ",
                        "у меня появился доступ",
                        "я уже имею доступ",
                        "я имею доступ",
                        "я пока не умею использовать интернет",
                    )
                )

                if (
                    answer_inverts_to_user
                    and not answer_self_owned
                ):
                    violations.append(
                        "SELF_REFERENCE_INVERTED_TO_USER"
                    )

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
