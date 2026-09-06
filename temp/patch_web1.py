# -*- coding: utf-8 -*-
# Патч веб-мессенджера: эндпоинты поиска, пагинации и канала потока.
p = 'communication/web_messenger.py'
s = open(p, encoding='utf-8').read()

old = '''    async def _api_history(self):
        return {
            "items": self._history_items(100)
        }'''

new = '''    async def _api_history(self, before_id: int = 0):
        if self.history is None:
            return {"items": []}
        try:
            rows = self.history.connection.execute(
                "SELECT id, sender, text, ts, "
                "read_by_recipient, read_ts "
                "FROM chat_history "
                + ("WHERE id < ? " if before_id else "")
                + "ORDER BY id DESC LIMIT 60",
                ((before_id,) if before_id else ()),
            ).fetchall()
        except Exception:
            return {"items": []}
        items = [
            {
                "id": r["id"],
                "sender": r["sender"],
                "text": r["text"],
                "ts": r["ts"],
                "read": bool(r["read_by_recipient"]),
                "read_ts": r["read_ts"],
            }
            for r in reversed(rows)
        ]
        return {"items": items}

    async def _api_search(self, q: str = ""):
        if self.history is None or not q.strip():
            return {"items": []}
        try:
            rows = self.history.connection.execute(
                "SELECT id, sender, text, ts "
                "FROM chat_history WHERE text "
                "LIKE ? ORDER BY id DESC LIMIT 40",
                ("%" + q.strip() + "%",),
            ).fetchall()
        except Exception:
            return {"items": []}
        return {
            "items": [
                {
                    "id": r["id"],
                    "sender": r["sender"],
                    "text": r["text"],
                    "ts": r["ts"],
                }
                for r in rows
            ]
        }

    def _stream_state(self):
        agent = getattr(self.server, "agent", None)
        stream = getattr(agent, "inner_stream", None)
        if stream is None:
            return {"items": [], "mood": {}}
        mood = getattr(agent, "mood", None)
        return {
            "items": [
                {
                    "kind": i["kind"],
                    "text": i["text"],
                }
                for i in list(stream.items)[-30:]
            ],
            "mood": (
                mood.snapshot() if mood else {}
            ),
        }

    async def _api_stream(self):
        return self._stream_state()'''

assert s.count(old) == 1, "api_history anchor: %d" % s.count(old)
s = s.replace(old, new)

old2 = '''        self.app.get("/")(self._index)
        self.app.get(
            "/api/history"
        )(self._api_history)
        self.app.websocket("/ws")(self._ws)'''

new2 = '''        self.app.get("/")(self._index)
        self.app.get(
            "/api/history"
        )(self._api_history)
        self.app.get(
            "/api/search"
        )(self._api_search)
        self.app.get(
            "/api/stream"
        )(self._api_stream)
        self.app.websocket("/ws")(self._ws)'''

assert s.count(old2) == 1, "routes anchor: %d" % s.count(old2)
s = s.replace(old2, new2)

open(p, 'w', encoding='utf-8', newline='\n').write(s)
import py_compile
py_compile.compile(p, doraise=True)
print('endpoints wired, COMPILE OK')
