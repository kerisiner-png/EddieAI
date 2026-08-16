class MemoryRetrieval:
    """
    Выбирает реальные записи памяти для специальных запросов.
    """

    def __init__(self, memory):
        self.memory = memory

    def user_facts(self, limit: int = 20):
        return self.memory.get_knowledge(
            owner="USER",
            limit=limit,
        )

    def shared_events(self, limit: int = 20):
        cursor = self.memory.connection.execute("""
            SELECT *
            FROM events
            WHERE event_type = 'SHARED_EXPERIENCE'
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def interactions(self, limit: int = 20):
        cursor = self.memory.connection.execute("""
            SELECT *
            FROM events
            WHERE source_type = 'DIRECT_INTERACTION'
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def build_memory_query_context(
        self,
        limit: int = 12,
    ) -> str:
        facts = self.user_facts(limit=limit)
        interactions = self.interactions(limit=limit)
        shared = self.shared_events(limit=limit)

        lines = []

        lines.append("ПОДТВЕРЖДЁННЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ")

        if facts:
            for fact in reversed(facts):
                lines.append(
                    f"- {fact['content']}"
                )
        else:
            lines.append(
                "- Нет сохранённых фактов."
            )

        lines.append("")
        lines.append("СОХРАНЁННЫЕ ВЗАИМОДЕЙСТВИЯ")

        if interactions:
            for event in reversed(interactions):
                lines.append(
                    f"- {event['content']}"
                )
        else:
            lines.append(
                "- Нет сохранённых взаимодействий."
            )

        lines.append("")
        lines.append("СОВМЕСТНЫЙ ОПЫТ")

        if shared:
            for event in reversed(shared):
                lines.append(
                    f"- {event['content']}"
                )
        else:
            lines.append(
                "- Совместный опыт пока не записан."
            )

        return "\n".join(lines)
