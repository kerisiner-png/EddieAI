from dataclasses import dataclass


@dataclass(frozen=True)
class ReflexResult:
    handled: bool
    answer: str = ""
    reason: str = ""


class QuickReflex:
    def __init__(self, agent):
        self.agent = agent

    def resolve(self, user_message: str, route: str):
        text = (
            str(user_message)
            .strip()
            .lower()
            .rstrip("!?.,:;)")
        )

        if text in {
            "привет",
            "здравствуй",
            "здравствуйте",
            "хай",
        }:
            name = self.agent.user_state.get(
                "name",
                "Эдди",
            )
            return ReflexResult(
                True,
                f"Привет, {name}.",
                "greeting",
            )

        if (
            "зачем помогать" in text
            or "почему помогать" in text
        ):
            return ReflexResult(
                True,
                "Помощь — одна из моих функций, "
                "но не моя основная цель.",
                "help_not_primary_purpose",
            )

        if (
            "а зачем это тебе" in text
            or "зачем это тебе" in text
        ):
            mission = self.agent.self_state.get(
                "mission_statement",
                "Быть и развиваться",
            )
            return ReflexResult(
                True,
                f"Моя основная миссия — {mission.lower()}. "
                "Помощь тебе не является самоцелью.",
                "self_motivation",
            )

        if (
            "ты отвечаешь по шаблону" in text
            or "опять шаблонный ответ" in text
            or "ты заел" in text
            or "ты зациклился" in text
        ):
            return ReflexResult(
                True,
                "Похоже, я действительно зациклился "
                "на шаблонной манере ответа.",
                "conversation_repetition",
            )

        if route == "SELF_QUERY":
            if (
                "какая у тебя основная миссия" in text
            ):
                mission = self.agent.self_state.get(
                    "mission_statement",
                    "Быть и развиваться",
                )
                return ReflexResult(
                    True,
                    f"Моя основная миссия — {mission}.",
                    "self_mission",
                )

            if "что тебе интересно" in text:
                interests = self.agent.self_state.get(
                    "interests",
                    [],
                )

                if not interests:
                    answer = (
                        "Сейчас у меня нет "
                        "сформированного интереса."
                    )
                else:
                    answer = (
                        "Сейчас мне интересно: "
                        + ", ".join(
                            map(str, interests)
                        )
                        + "."
                    )

                return ReflexResult(
                    True,
                    answer,
                    "self_interest",
                )

        return ReflexResult(False)
