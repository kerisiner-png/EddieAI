from pathlib import Path
import os
import sqlite3
import threading

from memory.events import Event
from memory.knowledge import Knowledge


_DATA_DIR = Path(
    os.environ.get("EDDIE_DATA_DIR")
    or (
        Path(__file__).resolve().parent.parent
        / "data"
    )
)

DB_PATH = _DATA_DIR / "memory.db"


def _synchronized(method):
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(
                self,
                *args,
                **kwargs,
            )

    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__

    return wrapper


class Memory:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        self.connection.execute(
            "PRAGMA busy_timeout=5000"
        )

        self._initialize()

    @_synchronized
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
                origin TEXT,
                created_at TEXT NOT NULL
            )
        """)

        proposal_columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(self_proposals)"
            ).fetchall()
        }

        if "origin" not in proposal_columns:
            self.connection.execute(
                """
                ALTER TABLE self_proposals
                ADD COLUMN origin TEXT
                """
            )

        self.connection.execute("""
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

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                owner TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source TEXT,
                confidence REAL NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                personal_experience INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS personality_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status_before TEXT,
                status_after TEXT,
                strength_before REAL,
                strength_after REAL,
                confidence_before REAL,
                confidence_after REAL,
                evidence_count INTEGER,
                contradictions INTEGER,
                reason TEXT,
                created_at TEXT NOT NULL
            )
        """)

        self.connection.commit()

    @_synchronized
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

    @_synchronized
    def remember_knowledge(
        self,
        knowledge: Knowledge,
    ):
        self.connection.execute("""
            INSERT INTO knowledge (
                content,
                owner,
                source_type,
                source,
                confidence,
                verified,
                personal_experience,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            knowledge.content,
            knowledge.owner,
            knowledge.source_type,
            knowledge.source,
            knowledge.confidence,
            int(knowledge.verified),
            int(knowledge.personal_experience),
        ))

        self.connection.commit()

    @_synchronized
    def get_knowledge(
        self,
        owner: str | None = None,
        limit: int = 20,
    ):
        if owner is None:
            cursor = self.connection.execute("""
                SELECT *
                FROM knowledge
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
        else:
            cursor = self.connection.execute("""
                SELECT *
                FROM knowledge
                WHERE owner = ?
                ORDER BY id DESC
                LIMIT ?
            """, (owner, limit))

        return cursor.fetchall()

    @_synchronized
    def remember_proposal(
        self,
        content: str,
        proposal_type: str,
        confidence: float = 0.5,
        origin: str | None = None,
    ):
        from datetime import datetime, timezone

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        cursor = self.connection.execute("""
            INSERT INTO self_proposals (
                content,
                proposal_type,
                confidence,
                status,
                origin,
                created_at
            )
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (
            content,
            proposal_type,
            confidence,
            origin,
            timestamp,
        ))

        self.connection.commit()

        return cursor.lastrowid

    @_synchronized
    def pending_proposals(self, limit: int = 20):
        cursor = self.connection.execute("""
            SELECT *
            FROM self_proposals
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    @_synchronized
    def set_proposal_status(
        self,
        proposal_id: int,
        status: str,
    ):
        allowed = {
            "pending",
            "accepted",
            "rejected",
            "deferred",
        }

        if status not in allowed:
            raise ValueError(
                f"Invalid proposal status: {status}"
            )

        self.connection.execute("""
            UPDATE self_proposals
            SET status = ?
            WHERE id = ?
        """, (
            status,
            proposal_id,
        ))

        self.connection.commit()

    @_synchronized
    def recent(self, limit: int = 10):
        cursor = self.connection.execute("""
            SELECT *
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    @_synchronized
    def close(self):
        self.connection.close()
