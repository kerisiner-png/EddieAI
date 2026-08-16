from memory.database import Memory


class MemoryManager:
    """
    Формирует короткий и понятный контекст для LLM.

    База памяти хранит всё.
    Но обычный диалог получает только то,
    что действительно полезно для текущего ответа.
    """

    def __init__(self, memory: Memory):
        self.memory = memory

    def build_context(
        self,
        limit: int = 6,
    ) -> str:
        memories = self.memory.recent(
            limit=limit
        )

        if not memories:
            return "Память пока пуста."

        lines = []

        for item in reversed(memories):
            source = item["source_type"]

            # Собственные старые ответы не передаём
            # обратно в обычный prompt.
            if source == "SELF_OUTPUT":
                continue

            if source == "DIRECT_INTERACTION":
                lines.append(
                    f"Эдди сказал: {item['content']}"
                )
                continue

            if source == "SYSTEM_EVENT":
                lines.append(
                    f"Системное событие: {item['content']}"
                )
                continue

            if source == "SELF_OBSERVATION":
                lines.append(
                    f"Наблюдение о себе: {item['content']}"
                )
                continue

            if source == "EXTERNAL_KNOWLEDGE":
                lines.append(
                    f"Внешнее знание: {item['content']}"
                )
                continue

            if source == "SHARED_EXPERIENCE":
                lines.append(
                    f"Совместный опыт: {item['content']}"
                )
                continue

            if source == "BELIEF":
                lines.append(
                    f"Убеждение: {item['content']}"
                )
                continue

            if source == "HYPOTHESIS":
                lines.append(
                    f"Гипотеза: {item['content']}"
                )
                continue

        if not lines:
            return "Нет релевантных воспоминаний."

        return "\n".join(lines)
