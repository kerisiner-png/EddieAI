from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Event:
    content: str
    event_type: str
    source_type: str
    timestamp: str
    source: Optional[str] = None
    personal_experience: bool = False
    confidence: Optional[float] = None
    interpretation: Optional[str] = None
    verified: bool = False

    @classmethod
    def create(
        cls,
        content: str,
        event_type: str,
        source_type: str,
        source: Optional[str] = None,
        personal_experience: bool = False,
        confidence: Optional[float] = None,
        interpretation: Optional[str] = None,
        verified: bool = False,
    ):
        return cls(
            content=content,
            event_type=event_type,
            source_type=source_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            personal_experience=personal_experience,
            confidence=confidence,
            interpretation=interpretation,
            verified=verified,
        )

    def to_dict(self):
        return asdict(self)
