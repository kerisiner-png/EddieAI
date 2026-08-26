import re

from memory.events import Event


RAM_REFUSAL_MARKERS = (
    "не могу думать",
    "не хватает памяти",
    "память не хватает",
    "закройте тяжёлые",
    "закрыть тяжёлые программы",
    "добавьте ключ облака",
    "добавить ключ облака",
    "противоречит моей текущей self-model",
    "не могу подтвердить такое утверждение",
    "согласно внутреннему рассуждению",
)


def is_degradation_answer(
    answer: str,
) -> bool:
    text = answer.lower()

    return any(
        marker in text
        for marker in RAM_REFUSAL_MARKERS
    )


class DialogueMemory:
    """
    Запись диалога в память личности.

    Реплики пользователя сохраняются всегда.
    Ответы EddieAI не записываются, если являются
    деградационными (отказы из-за ресурсов и т.п.) —
    служебные состояния системы не должны становиться
    воспоминаниями личности.
    """

    MIN_LEARNED = 2

    def __init__(self, memory):
        self.memory = memory

    def is_degradation(self, answer: str) -> bool:
        text = str(answer or "").lower()

        markers = set(RAM_REFUSAL_MARKERS)

        if self.memory is not None:
            for row in self.memory.learned_get(
                "degradation",
                self.MIN_LEARNED,
            ):
                markers.add(row["marker"])

        return any(
            marker in text
            for marker in markers
        )

    def _learn_degradation(
        self,
        answer: str,
    ):
        if self.memory is None:
            return

        static = set(RAM_REFUSAL_MARKERS)

        tokens = re.findall(
            r"[\u0430-\u044f\u0451a-z0-9]+",
            str(answer or "").lower(),
        )

        candidates = set()

        for token in tokens:
            if (
                len(token) >= 3
                and token not in static
            ):
                candidates.add(token)

        for index in range(len(tokens) - 1):
            bigram = (
                tokens[index]
                + " "
                + tokens[index + 1]
            )

            if bigram not in static:
                candidates.add(bigram)

        for marker in candidates:
            self.memory.learned_bump(
                marker,
                "degradation",
            )

    def record_user_message(
        self,
        text: str,
    ):
        self.memory.remember(
            Event.create(
                content=text,
                event_type="CONVERSATION",
                source_type="DIRECT_INTERACTION",
                source="Eddie",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

    def record_agent_answer(
        self,
        text: str,
    ) -> bool:
        if self.is_degradation(text):
            self._learn_degradation(text)
            return False

        self.memory.remember(
            Event.create(
                content=text,
                event_type="CONVERSATION",
                source_type="SELF_OUTPUT",
                source="self",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

        return True
