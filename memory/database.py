from pathlib import Path
import sqlite3
from typing import Optional

from memory.events import Event


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"


class Memory:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        self._initialize()

    def _initialize(self):
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source TEXT,
                timestamp TEXT NOT NULL,
                personal_experience INTEGER NOT NULL DEFAULT 0,
                confidence REAL,
                interpretation TEXT,
                verified INTEGER NOT NULL DEFAULT 0
            )
        """)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS self_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                proposal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)

        self.connection.commit()

    def remember(self, event: Event):
        self.connection.execute("""
            INSERT INTO events (
                content,
                event_type,
                source_type,
                source,
                timestamp,
                personal_experience,
                confidence,
                interpretation,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.content,
            event.event_type,
            event.source_type,
            event.source,
            event.timestamp,
            int(event.personal_experience),
            event.confidence,
            event.interpretation,
            int(event.verified),
        ))

        self.connection.commit()

    def remember_proposal(
        self,
        content: str,
        proposal_type: str,
        confidence: float = 0.5,
    ):
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()

        cursor = self.connection.execute("""
            INSERT INTO self_proposals (
                content,
                proposal_type,
                confidence,
                status,
                created_at
            )
            VALUES (?, ?, ?, 'pending', ?)
        """, (
            content,
            proposal_type,
            confidence,
            timestamp,
        ))

        self.connection.commit()

        return cursor.lastrowid

    def pending_proposals(self, limit: int = 20):
        cursor = self.connection.execute("""
            SELECT *
            FROM self_proposals
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def set_proposal_status(self, proposal_id: int, status: str):
        allowed = {
            "pending",
            "accepted",
            "rejected",
            "deferred",
        }

        if status not in allowed:
            raise ValueError(f"Invalid proposal status: {status}")

        self.connection.execute("""
            UPDATE self_proposals
            SET status = ?
            WHERE id = ?
        """, (status, proposal_id))

        self.connection.commit()

    def recent(self, limit: int = 10):
        cursor = self.connection.execute("""
            SELECT *
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def close(self):
        self.connection.close()
