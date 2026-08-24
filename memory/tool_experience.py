from memory.events import Event
from memory.knowledge import Knowledge


class ToolExperienceRecorder:
    """
    Превращает результаты реальных инструментов
    в события и знания памяти.

    Инструмент ничего не решает о личности сам:
    он только фиксирует полученный опыт.
    """

    def __init__(self, memory):
        self.memory = memory

    def record(
        self,
        action,
        result: dict,
        owner: str = "EXTERNAL",
        personal_experience: bool = True,
    ):
        status = result.get(
            "status",
            "UNKNOWN",
        )

        tool = result.get(
            "tool",
            action.action_type,
        )

        content = self._build_content(
            action,
            result,
        )

        event = Event.create(
            content=content,
            event_type="TOOL_RESULT",
            source_type="TOOL",
            source=tool,
            personal_experience=personal_experience,
            confidence=(
                1.0
                if status == "OK"
                else 0.3
            ),
            verified=(
                status == "OK"
            ),
        )

        self.memory.remember(
            event
        )

        knowledge = Knowledge(
            content=content,
            owner=owner,
            source_type="TOOL",
            source=tool,
            confidence=(
                1.0
                if status == "OK"
                else 0.3
            ),
            verified=(
                status == "OK"
            ),
            personal_experience=(
                personal_experience
            ),
        )

        return {
            "event": event,
            "knowledge": knowledge,
        }

    def _build_content(
        self,
        action,
        result,
    ) -> str:
        status = result.get(
            "status",
            "UNKNOWN",
        )

        tool = result.get(
            "tool",
            action.action_type,
        )

        payload = result.get(
            "result",
            {},
        )

        if isinstance(
            payload,
            dict,
        ):
            summary = payload.get(
                "content"
            )

            if summary:
                return (
                    f"Инструмент {tool} "
                    f"выполнил действие "
                    f"'{action.target}'. "
                    f"Результат: "
                    f"{summary}"
                )

        return (
            f"Инструмент {tool} "
            f"выполнил действие "
            f"'{action.target}'. "
            f"Статус: {status}."
        )
