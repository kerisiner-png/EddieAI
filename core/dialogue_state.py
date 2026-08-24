from collections import deque


class DialogueState:
    """
    Краткосрочная рабочая память текущего разговора.
    """

    def __init__(
        self,
        max_turns: int = 12,
    ):
        self.turns = deque(
            maxlen=max_turns
        )

    def add_turn(
        self,
        *,
        user: str,
        assistant: str,
    ):
        self.turns.append(
            {
                "user": user,
                "assistant": assistant,
            }
        )

    def clear(self):
        self.turns.clear()

    def render(
        self,
        limit: int = 3,
    ) -> str:

        recent = list(
            self.turns
        )[-limit:]

        if not recent:
            return (
                "RECENT CONVERSATION MEMORY\n"
                "No previous conversation."
            )

        lines = [
            "RECENT CONVERSATION MEMORY",
            "",
        ]

        for turn in recent:
            lines.append(
                "Эдди: " + turn["user"]
            )
            lines.append(
                "EddieAI: " + turn["assistant"]
            )
            lines.append("")

        return "\n".join(
            lines
        ).strip()

    def followup_context(
        self,
        current_message: str,
    ) -> str:

        text = (
            current_message
            .strip()
            .lower()
        )

        words = text.split()

        if not self.turns:
            return ""

        if len(words) > 5:
            return ""

        if not text.endswith(
            ("?", "?!", "!?")
        ):
            return ""

        markers = (
            "почему",
            "зачем",
            "как",
            "а почему",
            "а зачем",
            "а как",
            "а ты уверен",
            "уверен",
            "и что",
            "а что",
        )

        if not any(
            text.startswith(marker)
            for marker in markers
        ):
            return ""

        turns = list(
            self.turns
        )

        # Если текущая реплика уже была сохранена,
        # не используем её как "предыдущую".
        if turns[-1]["user"].strip().lower() == text:
            turns = turns[:-1]

        if not turns:
            return ""

        previous = turns[-1]

        previous_user = previous["user"]
        previous_answer = previous["assistant"]

        return (
            "FOLLOW-UP CONTEXT\n\n"
            "Previous user message:\n"
            + previous_user
            + "\n\n"
            "Previous EddieAI answer:\n"
            + previous_answer
            + "\n\n"
            "The current user message continues the previous topic. "
            "Answer the current message directly in that context."
        )
