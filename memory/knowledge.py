from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Knowledge:
    content: str
    owner: str
    source_type: str
    source: str | None = None
    confidence: float = 1.0
    verified: bool = False
    personal_experience: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
