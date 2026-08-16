from memory.knowledge import Knowledge


VALID_OWNERS = {
    "SELF",
    "USER",
    "EXTERNAL",
    "SHARED",
    "SYSTEM",
    "UNKNOWN",
}


class KnowledgeBoundary:
    """
    Проверяет принадлежность информации.

    Главный принцип:
    знание о USER никогда автоматически не становится
    знанием о SELF и наоборот.
    """

    def validate(self, knowledge: Knowledge) -> Knowledge:
        if knowledge.owner not in VALID_OWNERS:
            raise ValueError(
                f"Unknown knowledge owner: {knowledge.owner}"
            )

        confidence = max(
            0.0,
            min(1.0, float(knowledge.confidence)),
        )

        return Knowledge(
            content=knowledge.content,
            owner=knowledge.owner,
            source_type=knowledge.source_type,
            source=knowledge.source,
            confidence=confidence,
            verified=knowledge.verified,
            personal_experience=knowledge.personal_experience,
        )

    def belongs_to_self(self, knowledge: Knowledge) -> bool:
        return knowledge.owner == "SELF"

    def belongs_to_user(self, knowledge: Knowledge) -> bool:
        return knowledge.owner == "USER"

    def belongs_to_external(self, knowledge: Knowledge) -> bool:
        return knowledge.owner == "EXTERNAL"

    def belongs_to_shared_experience(
        self,
        knowledge: Knowledge,
    ) -> bool:
        return knowledge.owner == "SHARED"
