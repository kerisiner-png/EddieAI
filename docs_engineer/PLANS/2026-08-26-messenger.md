# EddieAI Messenger — Implementation Plan

**Goal:** Turn the EddieAI chat into a full messenger: persistent chat_history, read receipts, thinking indicator, presence status.

**Architecture:** chat_history table in memory.db (server side); TCP protocol extended (history/agent_thinking/mark_read/msg_id); client loads history + shows ticks/status.

**Tech Stack:** Python, sqlite3, tkinter, threading, TCP sockets.

**Spec:** `docs_engineer\SPECS\2026-08-26-messenger-design.md`

## Global Constraints

- UTF-8 no BOM, no literal CJK chars, no comments in code (project style)
- Vertical style: each statement on own line with blank-line grouping (match existing files)
- chat_history table in memory.db (same DB as events)
- Existing types (user_message, agent_message, agent_initiative) remain backward compatible
- respond() continues writing CONVERSATION to memory events — do NOT change
- Read receipt semantics per spec section 5

---

### Task 1: chat_history table in memory/database.py

**Files:**
- Modify: `memory/database.py`
- Test: `%TEMP%\opencode\test_chat_history.py`

**Interfaces:**
- Produces: `ChatHistoryStore` class with `add_message(sender, text) -> int`, `mark_read(msg_id)`, `recent(limit=50) -> list[dict]`, `unread_count() -> int`

- [ ] Add `ChatHistoryStore` class using memory.db connection (same pattern as Memory/events tables; `_ensure_table()` creates table if not exists)

```python
class ChatHistoryStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self._ensure_table()

    def _ensure_table(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    read_by_recipient INTEGER DEFAULT 0,
                    read_ts TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def add_message(self, sender, text) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            ts = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                "INSERT INTO chat_history (sender, text, ts) VALUES (?,?,?)",
                (sender, text, ts),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def mark_read(self, msg_id):
        conn = sqlite3.connect(self.db_path)
        try:
            ts = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE chat_history SET read_by_recipient=1, read_ts=? WHERE id=?",
                (ts, msg_id),
            )
            conn.commit()
        finally:
            conn.close()

    def recent(self, limit=50) -> list:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT id, sender, text, ts, read_by_recipient FROM "
                "chat_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(zip(
                ["id", "sender", "text", "ts", "read"],
                row,
            )) for row in reversed(rows)]
        finally:
            conn.close()

    def unread_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM chat_history WHERE sender='EddieAI' AND read_by_recipient=0"
            ).fetchone()
            return row[0]
        finally:
            conn.close()
```

- [ ] Test: create temp DB, add Eddie msg → id, mark_read, recent shows 1 with read=1, unread_count 0. py_compile.

### Task 2: Server — write history, agent_thinking, mark_read, history batch

**Files:**
- Modify: `core/eddie_server.py`
- Test: `%TEMP%\opencode\test_server_messenger.py`

**Interfaces:**
- Consumes: `ChatHistoryStore` from Task 1
- Produces: server wires `self.history = ChatHistoryStore(db_path)`; on `user_message`: add Eddie msg + send agent_thinking(msg_id) + mark_read, then respond, add EddieAI reply, send agent_message with msg_id; on `mark_read` from client: history.mark_read; on client connect: send `history` batch

- [ ] In `__init__`: add `self.history = None` placeholder (set by factory later) — but for standalone, construct from db path. Actually wire via `EddieServer(agent, history_store=None)` param; default build from `_BASE_DIR / "data" / "memory.db"`.

- [ ] In `handle_user_message`: after getting text, before respond: `eddie_id = self.history.add_message("Eddie", text)`; `self.broadcast({"type":"agent_thinking","msg_id":eddie_id})`; `self.history.mark_read(eddie_id)`. After respond: `ai_id = self.history.add_message("EddieAI", answer)`; return `(answer, ai_id)` or store last ai_id. Then handler writes `{"type":"agent_message","msg_id":ai_id,"text":answer}`.

- [ ] In server Handler for `mark_read`: `self.history.mark_read(payload["msg_id"])`.

- [ ] In Handler on connect (before loop): after `self.flush_outbox()`, send `{"type":"history","messages":self.history.recent(50)}`.

- [ ] Modify Handler's user_message response to include msg_id (change from `{"type":"agent_message","text":answer}` to include `msg_id`).

### Task 3: TCP client — handle new types + msg_id

**Files:**
- Modify: `communication/tcp_client.py`
- Test: `%TEMP%\opencode\test_client_messenger.py`

**Interfaces:**
- Consumes: server protocol from Task 2
- Produces: `on_history(callback)`, `on_thinking(callback)`, `send(text)->str` unchanged (returns text), add `mark_read(msg_id)` method. `agent_message` still sets response for waiting send() (msg_id not needed client-side for reply, but store last known msg_id for read-ack of EddieAI messages).

- [ ] Add `self._history_callbacks`, `self._thinking_callbacks` lists + `on_history(cb)`, `on_thinking(cb)`.
- [ ] In `_handle_line`: dispatch `history` → call history callbacks with messages; `agent_thinking` → call thinking callbacks with msg_id; `agent_message`/`agent_initiative` → existing behavior + capture msg_id.
- [ ] Add `mark_read(msg_id)`: send `{"type":"mark_read","msg_id":msg_id}`.

### Task 4: chat_app wiring

**Files:**
- Modify: `communication/chat_app.py`

**Interfaces:**
- Consumes: Task 2 server, Task 3 client
- Produces: on history → chat.show_history(messages); on thinking → status "EddieAI думает..."; after sending own message → show ✓/✓✓; after displaying EddieAI message (window visible) → tcp.mark_read(msg_id)

- [ ] Wire `self._tcp.on_history(self._on_history)`, `self._tcp.on_thinking(self._on_thinking)`.
- [ ] `_on_history(messages)`: `_post_ui(self._chat.show_history, messages)`
- [ ] `_on_thinking(msg_id)`: `_post_ui(self._chat.set_status, "EddieAI думает...")` + mark that Eddie msg read (✓✓)
- [ ] In `_show_reply` / `_show_initiative`: after append, if window visible → `self._tcp.mark_read(msg_id)`
- [ ] In `_send_and_display`: before send set own message ✓; on reply, clear thinking status

### Task 5: UI — history display, ticks, status

**Files:**
- Modify: `communication/ui_chat.py`

**Interfaces:**
- Consumes: Task 4
- Produces: `show_history(messages)`, append_message supports read flag for ticks (✓/✓✓)

- [ ] Add `show_history(messages)`: clear text, append each with timestamp (no double timestamp), sender color/tag.
- [ ] Add optional `read` param to append_message: for Eddie sender show "✓✓" if read else "✓" appended after text.
- [ ] Keep auto-scroll.

---

## Self-review notes

- Spec section 5 (read receipts both directions) → Tasks 2,4
- Spec section 3 (chat_history) → Task 1
- Spec section 4 (protocol) → Tasks 2,3
- Spec section 6 (UI) → Tasks 4,5
- Spec section 7 (files) → matches Tasks 1-5
