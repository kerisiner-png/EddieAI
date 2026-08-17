from dataclasses import dataclass


@dataclass
class EvidenceCandidate:
    field: str
    value: str
    strength: float
    weighted_score: float
    evidence_count: int
    source_types: list[str]
    confidence: float
    reason: str


class EvidenceConsolidator:
    """
    Converts aggregated evidence into personality candidates.
    Does not modify personality state.
    """

    MIN_CONFIDENCE = 0.70
    MIN_WEIGHTED_SCORE = 2.5
    MIN_SOURCE_TYPES = 3

    def __init__(self, evidence):
        self.evidence = evidence

    def consolidate(self):
        records = self.evidence.strong_candidates(
            minimum_confidence=self.MIN_CONFIDENCE,
            minimum_weighted_score=self.MIN_WEIGHTED_SCORE,
        )

        results = []

        for record in records:
            source_types = [
                source
                for source in record.source_types
                if source
            ]

            strength = min(
                1.0,
                0.5 + record.weighted_score * 0.1,
            )

            if len(source_types) < self.MIN_SOURCE_TYPES:
                results.append({
                    "status": "WAITING",
                    "field": record.category,
                    "value": record.value,
                    "evidence_count": record.count,
                    "source_types": source_types,
                    "weighted_score": record.weighted_score,
                    "confidence": record.confidence,
                    "strength": strength,
                    "reason": "Insufficient source diversity.",
                })
                continue

            results.append({
                "status": "PROMOTABLE",
                "field": record.category,
                "value": record.value,
                "evidence_count": record.count,
                "source_types": source_types,
                "weighted_score": record.weighted_score,
                "confidence": record.confidence,
                "strength": strength,
                "reason": "Evidence passed promotion thresholds.",
            })

        return results
