from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ActionChoice:
    task: str
    task_type: str
    options: list[str]
    selected: str
    reason: str
    context_type: str = "unknown"
    created_at: str | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

    def to_dict(self):
        return {
            "task": self.task,
            "task_type": self.task_type,
            "context_type": self.context_type,
            "options": list(self.options),
            "selected": self.selected,
            "reason": self.reason,
            "created_at": self.created_at,
        }
