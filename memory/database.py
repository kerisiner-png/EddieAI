from pathlib import Path
import sqlite3

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
