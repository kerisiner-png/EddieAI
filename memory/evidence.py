from dataclasses import dataclass
from datetime import datetime, timezone
import math

from memory.provenance import (
    source_weight,
    validate_source,
)


@dataclass
class EvidenceRecord:
    category: str
    value: str
    count: int
    weighted_score: float
    confidence: float
    source_types: list[str]
    first_seen: str
    last_seen: str


class EvidenceEngine:
    """
    Хранит отдельные свидетельства.

    Ключевой принцип:
    повторение одной и той же фразы не равно независимому
    доказательству.

    Каждое evidence имеет источник и вес.
    """

    def __init__(self, memory):
        self.memory = memory
        self._ensure_table()

    def _ensure_table(self):
        self.memory.connection.execute("""
            CREATE TABLE IF NOT EXISTS evidence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                weight REAL NOT NULL,
                event_id INTEGER,
                independence_key TEXT,
                created_at TEXT NOT NULL
            )
        """)

        columns = {
            row["name"]
            for row in self.memory.connection.execute(
                "PRAGMA table_info(evidence_events)"
            ).fetchall()
        }

        if "independence_key" not in columns:
            self.memory.connection.execute(
                """
                ALTER TABLE evidence_events
                ADD COLUMN independence_key TEXT
                """
            )

        self.memory.connection.commit()

    def add(
        self,
        category: str,
        value: str,
        source: str = "SELF_OBSERVATION",
        event_id: int | None = None,
        independence_key: str | None = None,
    ) -> EvidenceRecord:

        validate_source(source)

        now = datetime.now(
            timezone.utc
        ).isoformat()

        weight = source_weight(source)

        self.memory.connection.execute("""
            INSERT INTO evidence_events (
                category,
                value,
                source,
                weight,
                event_id,
                independence_key,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
            value,
            source,
            weight,
            event_id,
            independence_key,
            now,
        ))

        self.memory.connection.commit()

        return self.get(
            category,
            value,
        )

    def get(
        self,
        category: str,
        value: str,
    ) -> EvidenceRecord:

        rows = self.memory.connection.execute("""
            SELECT *
            FROM evidence_events
            WHERE category = ?
              AND value = ?
            ORDER BY id ASC
        """, (
            category,
            value,
        )).fetchall()

        if not rows:
            raise ValueError(
                "Evidence record does not exist."
            )

        count = len(rows)

        weighted_score = sum(
            row["weight"]
            for row in rows
        )

        source_types = sorted(
            {
                row["source"]
                for row in rows
                if row["weight"] > 0
            }
        )

        independence_keys = {
            (
                row["independence_key"]
                if row["independence_key"]
                else row["source"]
            )
            for row in rows
            if row["weight"] > 0
        }

        # ????????????? ????????? ??????
        # ???????? ????? ????????.
        diversity_bonus = min(
            1.0,
            len(independence_keys) / 3.0,
        )

        repetition_signal = (
            1.0 - math.exp(
                -weighted_score / 3.0
            )
        )

        confidence = round(
            (
                repetition_signal * 0.7
                + diversity_bonus * 0.3
            ),
            3,
        )

        return EvidenceRecord(
            category=category,
            value=value,
            count=count,
            weighted_score=round(
                weighted_score,
                3,
            ),
            confidence=confidence,
            source_types=source_types,
            first_seen=rows[0]["created_at"],
            last_seen=rows[-1]["created_at"],
        )

    def all_records(self):
        rows = self.memory.connection.execute("""
            SELECT DISTINCT
                category,
                value
            FROM evidence_events
            WHERE weight > 0
        """).fetchall()

        return [
            self.get(
                row["category"],
                row["value"],
            )
            for row in rows
        ]

    def strong_candidates(
        self,
        minimum_confidence: float = 0.70,
        minimum_weighted_score: float = 2.5,
    ):
        return [
            record
            for record in self.all_records()
            if (
                record.confidence
                >= minimum_confidence
                and record.weighted_score
                >= minimum_weighted_score
            )
        ]

