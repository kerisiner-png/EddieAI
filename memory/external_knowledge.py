from dataclasses import dataclass

from memory.knowledge import Knowledge


@dataclass
class ExternalKnowledgeRecord:
    query: str
    title: str
    url: str
    source: str
    verified: bool = False


class ExternalKnowledgeRecorder:
    """
    Сохраняет результаты WEB_SEARCH как EXTERNAL knowledge.

    Внешний источник никогда автоматически
    не становится SELF knowledge.
    """

    def __init__(self, memory):
        self.memory = memory

    def record(
        self,
        result: dict,
    ):
        if result.get("status") != "OK":
            return []

        query = result.get(
            "query",
            "",
        )

        items = result.get(
            "results",
            [],
        )

        records = []

        for item in items:
            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip()

            url = str(
                item.get(
                    "url",
                    "",
                )
            ).strip()

            if not url:
                continue

            content = (
                f"Внешний источник по запросу "
                f"'{query}': {title} — {url}"
            )

            knowledge = Knowledge(
                content=content,
                owner="EXTERNAL",
                source_type="WEB_SEARCH",
                source=url,
                confidence=0.5,
                verified=False,
                personal_experience=False,
            )

            self.memory.remember_knowledge(
                knowledge
            )

            records.append(
                ExternalKnowledgeRecord(
                    query=query,
                    title=title,
                    url=url,
                    source=url,
                    verified=False,
                )
            )

        return records
