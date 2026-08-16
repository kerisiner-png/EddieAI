from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass
class EvidenceRecord:
    category: str
    value: str
    count: int
    first_seen: str
    last_seen: str
    confidence: float


class EvidenceEngine:
    """
    Собирает повторяющиеся свидетельства возможных
    черт личности.

    Одно утверждение ничего не меняет.
    Повторяемость увеличивает уверенность.
    """

    def __init__(self, memory):
        self.memory = memory
        self._ensure_table()

    def _ensure_table(self):
        self.memory.connection.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.0,
                UNIQUE(category, value)
            )
        """)
        self.memory.connection.commit()

    def add(
        self,
        category: str,
        value: str,
    ) -> EvidenceRecord:
        now = datetime.now(timezone.utc).isoformat()

        row = self.memory.connection.execute("""
            SELECT *
            FROM evidence
            WHERE category = ? AND value = ?
        """, (category, value)).fetchone()

        if row is None:
            count = 1

            self.memory.connection.execute("""
                INSERT INTO evidence (
                    category,
                    value,
                    count,
                    first_seen,
                    last_seen,
                    confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                category,
                value,
                count,
                now,
                now,
                self._confidence(count),
            ))
        else:
            count = row["count"] + 1

            self.memory.connection.execute("""
                UPDATE evidence
                SET count = ?,
                    last_seen = ?,
                    confidence = ?
                WHERE id = ?
            """, (
                count,
                now,
                self._confidence(count),
                row["id"],
            ))

        self.memory.connection.commit()

        updated = self.memory.connection.execute("""
            SELECT *
            FROM evidence
            WHERE category = ? AND value = ?
        """, (category, value)).fetchone()

        return EvidenceRecord(
            category=updated["category"],
            value=updated["value"],
            count=updated["count"],
            first_seen=updated["first_seen"],
            last_seen=updated["last_seen"],
            confidence=updated["confidence"],
        )

    def _confidence(self, count: int) -> float:
        # 1 повторение — слабое свидетельство.
        # Рост постепенно замедляется.
        return round(
            1.0 - math.exp(-count / 3.0),
            3,
        )

    def get(
        self,
        category: str,
        value: str,
    ):
        row = self.memory.connection.execute("""
            SELECT *
            FROM evidence
            WHERE category = ? AND value = ?
        """, (category, value)).fetchone()

        if row is None:
            return None

        return EvidenceRecord(
            category=row["category"],
            value=row["value"],
            count=row["count"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            confidence=row["confidence"],
        )

    def strong_candidates(
        self,
        minimum_confidence: float = 0.75,
    ):
        rows = self.memory.connection.execute("""
            SELECT *
            FROM evidence
            WHERE confidence >= ?
            ORDER BY confidence DESC, count DESC
        """, (minimum_confidence,)).fetchall()

        return [
            EvidenceRecord(
                category=row["category"],
                value=row["value"],
                count=row["count"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                confidence=row["confidence"],
            )
            for row in rows
        ]
