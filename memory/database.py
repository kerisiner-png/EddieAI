import sqlite3
from pathlib import Path
from typing import Optional


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
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source TEXT,
                timestamp TEXT NOT NULL,
                confidence REAL,
                personal_experience INTEGER NOT NULL DEFAULT 0,
                verified INTEGER NOT NULL DEFAULT 0
            )
        """)
        self.connection.commit()

    def add(
        self,
        content: str,
        source_type: str,
        source: Optional[str] = None,
        timestamp: Optional[str] = None,
        confidence: Optional[float] = None,
        personal_experience: bool = False,
        verified: bool = False,
    ):
        from datetime import datetime, timezone

        timestamp = timestamp or datetime.now(timezone.utc).isoformat()

        self.connection.execute("""
            INSERT INTO memories (
                content,
                source_type,
                source,
                timestamp,
                confidence,
                personal_experience,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            content,
            source_type,
            source,
            timestamp,
            confidence,
            int(personal_experience),
            int(verified),
        ))

        self.connection.commit()

    def recent(self, limit: int = 10):
        cursor = self.connection.execute("""
            SELECT *
            FROM memories
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def close(self):
        self.connection.close()
