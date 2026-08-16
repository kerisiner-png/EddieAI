from memory.knowledge import Knowledge
from memory.knowledge_boundary import KnowledgeBoundary


class KnowledgeManager:
    def __init__(self, memory):
        self.memory = memory
        self.boundary = KnowledgeBoundary()

    def store(
        self,
        content: str,
        owner: str,
        source_type: str,
        source: str | None = None,
        confidence: float = 1.0,
        verified: bool = False,
        personal_experience: bool = False,
    ):
        knowledge = Knowledge(
            content=content,
            owner=owner,
            source_type=source_type,
            source=source,
            confidence=confidence,
            verified=verified,
            personal_experience=personal_experience,
        )

        knowledge = self.boundary.validate(
            knowledge
        )

        self.memory.remember_knowledge(
            knowledge
        )

        return knowledge

    def self_knowledge(self, limit: int = 20):
        return self.memory.get_knowledge(
            owner="SELF",
            limit=limit,
        )

    def user_knowledge(self, limit: int = 20):
        return self.memory.get_knowledge(
            owner="USER",
            limit=limit,
        )

    def external_knowledge(self, limit: int = 20):
        return self.memory.get_knowledge(
            owner="EXTERNAL",
            limit=limit,
        )

    def shared_knowledge(self, limit: int = 20):
        return self.memory.get_knowledge(
            owner="SHARED",
            limit=limit,
        )
