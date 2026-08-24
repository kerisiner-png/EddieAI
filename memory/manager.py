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

    def build_conversation_context(
        self,
        limit: int = 8,
    ) -> str:
        rows = self.memory.connection.execute(
            """
            SELECT
                id,
                source_type,
                content
            FROM events
            WHERE event_type = 'CONVERSATION'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        if not rows:
            return "??????? ?????? ???? ????."

        lines = []

        for row in reversed(rows):
            source_type = row["source_type"]
            content = str(
                row["content"] or ""
            ).strip()

            if not content:
                continue

            if source_type == "DIRECT_INTERACTION":
                lines.append(
                    f"????: {content}"
                )
                continue

            if source_type == "SELF_OUTPUT":
                lines.append(
                    f"EddieAI: {content}"
                )
                continue

        if not lines:
            return "??????? ?????? ???? ????."

        return "\n".join(lines)

    def build_reflection_context(
        self,
        limit: int = 20,
    ) -> str:
        memories = self.memory.recent(
            limit=limit
        )

        if not memories:
            return "Память пока пуста."

        self_lines = []
        user_lines = []
        other_lines = []

        for item in reversed(memories):
            source_type = item["source_type"]
            event_type = item["event_type"]
            content = item["content"]
            source = item["source"]
            personal = item["personal_experience"]

            if (
                source_type
                in {
                    "SELF_EXPERIENCE",
                    "SELF_OBSERVATION",
                    "SELF_OUTPUT",
                }
            ):
                self_lines.append(
                    f"[{event_type}] {content}"
                )
                continue

            if (
                event_type == "USER_FACT"
                or source_type == "DIRECT_INTERACTION"
                or source == "Eddie"
            ):
                user_lines.append(
                    f"[{event_type}] {content}"
                )
                continue

            if personal == 1:
                self_lines.append(
                    f"[{event_type}] {content}"
                )
                continue

            other_lines.append(
                f"[{event_type}] {content}"
            )

        return (
            "=== SELF-OWNED EXPERIENCE ===\n"
            + (
                "\n".join(self_lines)
                if self_lines
                else "Нет данных."
            )
            + "\n\n"
            + "=== USER-OWNED EXPERIENCE ===\n"
            + (
                "\n".join(user_lines)
                if user_lines
                else "Нет данных."
            )
            + "\n\n"
            + "=== OTHER / UNASSIGNED EXPERIENCE ===\n"
            + (
                "\n".join(other_lines)
                if other_lines
                else "Нет данных."
            )
        )
