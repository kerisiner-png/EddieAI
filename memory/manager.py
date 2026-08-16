from memory.database import Memory


class MemoryManager:
    """
    Decides what part of long-term memory should be shown to the model
    for the current interaction.

    The database remains the source of truth.
    This class only builds a useful context.
    """

    def __init__(self, memory: Memory):
        self.memory = memory

    def build_context(self, limit: int = 12) -> str:
        memories = self.memory.recent(limit=limit)

        if not memories:
            return "Нет доступных воспоминаний."

        lines = []

        for item in reversed(memories):
            source = item["source_type"]

            # Technical self-output is kept in the database,
            # but presented to the model as a previous reply,
            # not as an autobiographical fact.
            if source == "SELF_OUTPUT":
                lines.append(
                    f"Предыдущий мой ответ: {item['content']}"
                )
                continue

            if source == "DIRECT_INTERACTION":
                lines.append(
                    f"Эдди сказал: {item['content']}"
                )
                continue

            if source == "SYSTEM_EVENT":
                lines.append(
                    f"Событие системы: {item['content']}"
                )
                continue

            if source == "SELF_PROPOSAL":
                lines.append(
                    f"Моё прошлое предложение о себе: {item['content']}"
                )
                continue

            if source == "SELF_OBSERVATION":
                lines.append(
                    f"Моё наблюдение о себе: {item['content']}"
                )
                continue

            if source == "BELIEF":
                lines.append(
                    f"Моё убеждение: {item['content']}"
                )
                continue

            if source == "HYPOTHESIS":
                lines.append(
                    f"Моя гипотеза: {item['content']}"
                )
                continue

            if source == "EXTERNAL_KNOWLEDGE":
                lines.append(
                    f"Внешняя информация: {item['content']}"
                )
                continue

            # Fallback for future event types.
            lines.append(
                f"Событие [{source}]: {item['content']}"
            )

        return "\n".join(lines)

    def remember_proposal(
        self,
        content: str,
        proposal_type: str,
        confidence: float = 0.5,
    ):
        return self.memory.remember_proposal(
            content=content,
            proposal_type=proposal_type,
            confidence=confidence,
        )
