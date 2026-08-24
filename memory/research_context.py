class ResearchContext:
    """
    Формирует компактный контекст из ранее найденных
    внешних источников и собственных интерпретаций.

    Ничего нового не утверждает и не изменяет память.
    """

    def __init__(
        self,
        memory,
        limit: int = 8,
    ):
        self.memory = memory
        self.limit = max(
            1,
            int(limit),
        )

    def build(
        self,
        query: str | None = None,
    ) -> str:
        params = []
        where = [
            "owner IN ('EXTERNAL', 'SELF')",
            (
                "source_type IN "
                "('WEB_SEARCH', 'SELF_INTERPRETATION')"
            ),
        ]

        if query:
            where.append(
                "content LIKE ?"
            )
            params.append(
                f"%{query}%"
            )

        params.append(self.limit)

        sql = f"""
            SELECT
                owner,
                source_type,
                source,
                confidence,
                verified,
                content
            FROM knowledge
            WHERE {' AND '.join(where)}
            ORDER BY id DESC
            LIMIT ?
        """

        rows = self.memory.connection.execute(
            sql,
            tuple(params),
        ).fetchall()

        if not rows:
            return "Нет ранее сохранённого исследовательского контекста."

        chunks = []

        for index, row in enumerate(rows, start=1):
            chunks.append(
                f"""ITEM {index}
OWNER: {row["owner"]}
TYPE: {row["source_type"]}
SOURCE: {row["source"]}
CONFIDENCE: {row["confidence"]}
VERIFIED: {bool(row["verified"])}
CONTENT:
{row["content"]}"""
            )

        return "\n\n".join(chunks)
