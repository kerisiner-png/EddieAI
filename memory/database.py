from pathlib import Path
import os
import sqlite3
import threading
from datetime import datetime, timezone

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

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                ts TEXT NOT NULL,
                read_by_recipient INTEGER NOT NULL DEFAULT 0,
                read_ts TEXT
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
            CREATE TABLE IF NOT EXISTS situation_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation_key TEXT NOT NULL UNIQUE,
                action TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5,
                times_used INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS speech_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marker TEXT NOT NULL,
                marker_type TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                UNIQUE(marker, marker_type)
            )
        """)

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS learned_markers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marker TEXT NOT NULL,
                category TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                UNIQUE(marker, category)
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
    def pattern_lookup(self, key: str):
        row = self.connection.execute("""
            SELECT *
            FROM situation_patterns
            WHERE situation_key = ?
        """, (key,)).fetchone()

        if row is None:
            return None

        return dict(row)

    @_synchronized
    def pattern_record(
        self,
        key: str,
        action: str,
        confidence: float = 0.5,
    ):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        existing = self.connection.execute("""
            SELECT id
            FROM situation_patterns
            WHERE situation_key = ?
        """, (key,)).fetchone()

        if existing is not None:
            self.connection.execute("""
                UPDATE situation_patterns
                SET action = ?,
                    confidence = ?,
                    last_seen = ?
                WHERE id = ?
            """, (
                action,
                confidence,
                now,
                existing["id"],
            ))
        else:
            self.connection.execute("""
                INSERT INTO situation_patterns (
                    situation_key,
                    action,
                    confidence,
                    times_used,
                    first_seen,
                    last_seen
                )
                VALUES (?, ?, ?, 0, ?, ?)
            """, (
                key,
                action,
                confidence,
                now,
                now,
            ))

        self.connection.commit()

    @_synchronized
    def pattern_bump(self, key: str):
        self.connection.execute("""
            UPDATE situation_patterns
            SET times_used = times_used + 1,
                last_seen = ?
            WHERE situation_key = ?
        """, (
            datetime.now(
                timezone.utc
            ).isoformat(),
            key,
        ))

        self.connection.commit()

    @_synchronized
    def pattern_stats(self):
        row = self.connection.execute("""
            SELECT COUNT(*) AS n,
                   COALESCE(SUM(times_used), 0)
                       AS total_uses
            FROM situation_patterns
        """).fetchone()

        return {
            "patterns": row["n"],
            "total_uses": row["total_uses"],
        }

    @_synchronized
    def speech_bump(
        self,
        marker: str,
        marker_type: str,
    ):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        self.connection.execute("""
            INSERT INTO speech_habits (
                marker,
                marker_type,
                count,
                first_seen,
                last_seen
            )
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(marker, marker_type)
            DO UPDATE SET
                count = count + 1,
                last_seen = excluded.last_seen
        """, (
            marker,
            marker_type,
            now,
            now,
        ))

        self.connection.commit()

    @_synchronized
    def speech_top(
        self,
        marker_type: str | None = None,
        limit: int = 10,
    ):
        if marker_type is None:
            rows = self.connection.execute("""
                SELECT marker, marker_type, count
                FROM speech_habits
                ORDER BY count DESC, marker ASC
                LIMIT ?
            """, (limit,)).fetchall()
        else:
            rows = self.connection.execute("""
                SELECT marker, marker_type, count
                FROM speech_habits
                WHERE marker_type = ?
                ORDER BY count DESC, marker ASC
                LIMIT ?
            """, (marker_type, limit)).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    @_synchronized
    def speech_stats(self):
        row = self.connection.execute("""
            SELECT COUNT(*) AS markers,
                   COALESCE(SUM(count), 0) AS total
            FROM speech_habits
        """).fetchone()

        return {
            "markers": row["markers"],
            "total": row["total"],
        }

    @_synchronized
    def learned_bump(
        self,
        marker: str,
        category: str,
    ):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        self.connection.execute("""
            INSERT INTO learned_markers (
                marker,
                category,
                count,
                first_seen,
                last_seen
            )
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(marker, category)
            DO UPDATE SET
                count = count + 1,
                last_seen = excluded.last_seen
        """, (
            marker,
            category,
            now,
            now,
        ))

        self.connection.commit()

    @_synchronized
    def learned_get(
        self,
        category: str,
        min_count: int = 1,
    ):
        rows = self.connection.execute("""
            SELECT marker, count
            FROM learned_markers
            WHERE category = ?
              AND count >= ?
            ORDER BY count DESC
        """, (
            category,
            min_count,
        )).fetchall()

        return [
            {
                "marker": row["marker"],
                "count": row["count"],
            }
            for row in rows
        ]

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
    def chat_add(self, sender, text):
        cur = self.connection.execute(
            "INSERT INTO chat_history "
            "(sender, text, ts) VALUES (?,?,?)",
            (
                sender,
                text,
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        self.connection.commit()

        return cur.lastrowid

    @_synchronized
    def chat_mark_read(self, msg_id):
        self.connection.execute(
            "UPDATE chat_history SET "
            "read_by_recipient=1, read_ts=? "
            "WHERE id=?",
            (
                datetime.now(
                    timezone.utc
                ).isoformat(),
                msg_id,
            ),
        )

        self.connection.commit()

    @_synchronized
    def chat_recent(self, limit: int = 50):
        rows = self.connection.execute(
            "SELECT id, sender, text, ts, "
            "read_by_recipient "
            "FROM chat_history "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        items = []

        for row in reversed(rows):
            items.append({
                "id": row["id"],
                "sender": row["sender"],
                "text": row["text"],
                "ts": row["ts"],
                "read": bool(
                    row[
                        "read_by_recipient"
                    ]
                ),
            })

        return items

    @_synchronized
    def chat_unread(self):
        row = self.connection.execute(
            "SELECT COUNT(*) AS n FROM "
            "chat_history WHERE sender=? "
            "AND read_by_recipient=0",
            ("EddieAI",),
        ).fetchone()

        return row["n"]

    @_synchronized
    def chat_unread_meta(self):
        row = self.connection.execute(
            "SELECT COUNT(*) AS n, "
            "MIN(ts) AS earliest, "
            "MAX(ts) AS latest "
            "FROM chat_history "
            "WHERE sender=? "
            "AND read_by_recipient=0",
            ("Eddie",),
        ).fetchone()

        return {
            "count": row["n"],
            "earliest": row["earliest"],
            "latest": row["latest"],
        }

    @_synchronized
    def chat_unread_eddie(self):
        rows = self.connection.execute(
            "SELECT id, text, ts FROM "
            "chat_history WHERE sender=? "
            "AND read_by_recipient=0 "
            "ORDER BY id ASC",
            ("Eddie",),
        ).fetchall()

        return [
            {
                "id": r["id"],
                "text": r["text"],
                "ts": r["ts"],
            }
            for r in rows
        ]

    @_synchronized
    def chat_mark_eddie_read(self, msg_id):
        self.connection.execute(
            "UPDATE chat_history SET "
            "read_by_recipient=1, read_ts=? "
            "WHERE id=?",
            (
                datetime.now(
                    timezone.utc
                ).isoformat(),
                msg_id,
            ),
        )

        self.connection.commit()

    @_synchronized
    def chat_unread_context(self, limit: int = 5):
        rows = self.connection.execute("""
            SELECT sender, text
            FROM chat_history
            WHERE sender = 'Eddie'
              AND read_by_recipient = 0
            ORDER BY id ASC
            LIMIT ?
        """, (limit,)).fetchall()

        lines = []

        for row in rows:
            text = str(
                row["text"] or ""
            ).strip()

            if not text:
                continue

            lines.append(
                "Эдди (непрочитано): " + text
            )

        if not lines:
            return ""

        return "\n".join(lines)

    @_synchronized
    def chat_context(self, limit: int = 8):
        rows = self.connection.execute("""
            SELECT sender, text
            FROM chat_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        lines = []

        for row in reversed(rows):
            if row["sender"] == "Eddie":
                prefix = "Эдди: "
            else:
                prefix = "EddieAI: "

            text = str(
                row["text"] or ""
            ).strip()

            if not text:
                continue

            lines.append(
                prefix + text
            )

        if not lines:
            return ""

        return "\n".join(lines)

    @_synchronized
    def close(self):
        self.connection.close()
