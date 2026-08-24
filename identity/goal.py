from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


VALID_STATUSES = {
    "CANDIDATE",
    "ACTIVE",
    "PAUSED",
    "COMPLETED",
    "ABANDONED",
}


@dataclass
class Goal:
    value: str
    status: str = "CANDIDATE"
    priority: float = 0.5
    motivation: float = 0.5
    confidence: float = 0.5
    created_at: str | None = None
    updated_at: str | None = None
    progress: float = 0.0
    source: str = "self"

    def __post_init__(self):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        if self.created_at is None:
            self.created_at = now

        if self.updated_at is None:
            self.updated_at = now

        self.priority = max(
            0.0,
            min(1.0, self.priority),
        )

        self.motivation = max(
            0.0,
            min(1.0, self.motivation),
        )

        self.confidence = max(
            0.0,
            min(1.0, self.confidence),
        )

        self.progress = max(
            0.0,
            min(1.0, self.progress),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
