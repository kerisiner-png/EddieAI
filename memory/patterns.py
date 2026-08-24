from dataclasses import dataclass
from datetime import datetime, timezone

from memory.evidence import EvidenceEngine


@dataclass
class Pattern:
    category: str
    value: str
    count: int
    weighted_score: float
    confidence: float
    source_types: list[str]
    age_days: float
    strength: float


class PatternDetector:
    """
    Превращает evidence в устойчивые паттерны.
    """

    DECAY_RATE = 0.015

    def __init__(self, memory):
        self.memory = memory
        self.evidence = EvidenceEngine(
            memory
        )

    def detect(self):
        records = self.evidence.all_records()

        patterns = []

        for record in records:
            try:
                last_seen = datetime.fromisoformat(
                    record.last_seen
                )

                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(
                        tzinfo=timezone.utc
                    )

                now = datetime.now(
                    timezone.utc
                )

                age_days = max(
                    0.0,
                    (
                        now - last_seen
                    ).total_seconds()
                    / 86400.0,
                )

            except (TypeError, ValueError):
                age_days = 0.0

            decay = max(
                0.0,
                1.0 - (
                    age_days
                    * self.DECAY_RATE
                ),
            )

            strength = round(
                record.confidence * decay,
                3,
            )

            patterns.append(
                Pattern(
                    category=record.category,
                    value=record.value,
                    count=record.count,
                    weighted_score=record.weighted_score,
                    confidence=record.confidence,
                    source_types=record.source_types,
                    age_days=round(
                        age_days,
                        2,
                    ),
                    strength=strength,
                )
            )

        return patterns

    def strong_patterns(
        self,
        minimum_strength: float = 0.75,
        minimum_weighted_score: float = 2.5,
    ):
        return [
            pattern
            for pattern in self.detect()
            if (
                pattern.strength
                >= minimum_strength
                and pattern.weighted_score
                >= minimum_weighted_score
            )
        ]
