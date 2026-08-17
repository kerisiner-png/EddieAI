from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Proposal:
    proposal_type: str
    value: Any
    reason: str
    confidence: float
    evidence: list[str]
    evidence_count: int | None = None

    def to_dict(self):
        return asdict(self)
