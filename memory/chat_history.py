from memory.database import Memory


class ChatHistory:
    """Чат-история EddieAI: контракт eddie_server
    (chat_add/chat_unread_eddie/chat_mark_eddie_read/
    chat_recent) поверх SQLite-хранилища Memory
    (таблица chat_history в data/memory.db)."""

    def __init__(self, database=None):
        self._db = (
            database
            if database is not None
            else Memory()
        )

    def chat_add(self, sender, text):
        return self._db.chat_add(
            sender,
            text,
        )

    def chat_unread_eddie(self):
        return self._db.chat_unread_eddie()

    def chat_mark_eddie_read(self, msg_id):
        return self._db.chat_mark_eddie_read(
            msg_id,
        )

    def chat_recent(self, limit=50):
        return self._db.chat_recent(limit)

    def close(self):
        try:
            self._db.close()
        except Exception:
            pass
