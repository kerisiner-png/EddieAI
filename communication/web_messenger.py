"""Локальный веб-мессенджер EddieAI (стиль Telegram).

Только внутри машины: http://127.0.0.1:7779
- единая история из chat_history (включая [голос]);
- живая доставка по WebSocket (сообщения, инициативы,
  «печатает…», речевые чанки);
- сообщения Эдди идут тем же конвейером, что и чат:
  server.handle_user_message → respond_and_deliver.
"""
import asyncio
import threading

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>EDDIE·AI — Tabula</title>
<style>
:root {
  --papyrus:#e8dcc3; --papyrus-hi:#f4ecd8; --ink:#2b2320;
  --wax:#5c2b2b; --wax-hi:#6b3733; --bronze:#8b6f47;
  --red:#7a2a1d; --wood:#4a3a28; --sub:#6d5c44;
}
* { box-sizing:border-box; margin:0; }
body {
  background:
    repeating-linear-gradient(0deg,
      rgba(139,111,71,.05) 0 1px, transparent 1px 28px),
    linear-gradient(180deg,#e3d5b7,#dcc9a3);
  color:var(--ink);
  font:15px/1.5 Georgia,'Times New Roman',serif;
  height:100vh; display:flex; flex-direction:column;
}
header {
  background:linear-gradient(180deg,#3c2f1e,#2f2416);
  border-bottom:4px double var(--bronze);
  padding:12px 18px; display:flex; align-items:baseline;
  gap:14px; color:#d9b36c;
}
header .laurel { color:var(--bronze); letter-spacing:2px; }
header h1 {
  font-size:19px; font-weight:normal;
  letter-spacing:6px; margin:0; color:#e8c883;
}
header .motto {
  font-size:11px; letter-spacing:3px; color:var(--sub);
}
header span#conn {
  margin-left:auto; font-size:12px;
  font-style:italic; color:#c9b28a;
}
#scroll {
  flex:1; overflow-y:auto; position:relative;
  margin:10px 6%; background:var(--papyrus);
  border-left:14px solid var(--wood);
  border-right:14px solid var(--wood);
  box-shadow:inset 0 0 40px rgba(90,70,50,.25);
  padding:16px 22px; display:flex;
  flex-direction:column; gap:10px;
}
#scroll::-webkit-scrollbar { width:10px; }
#scroll::-webkit-scrollbar-thumb {
  background:var(--bronze); border:2px solid var(--wood);
}
.row { display:flex; }
.row.me { justify-content:flex-end; }
.msg { max-width:70%; padding:9px 13px; position:relative;
  border-radius:2px; }
.from-eddieai {
  background:var(--papyrus-hi);
  border:1px solid var(--bronze);
  border-left:4px solid var(--red);
}
.from-eddie {
  background:linear-gradient(160deg,var(--wax-hi),var(--wax));
  border:1px solid #2f1414; color:#f0e2c8;
  box-shadow:inset 0 0 12px rgba(0,0,0,.35);
}
.who {
  display:block; font-size:10px; letter-spacing:3px;
  color:var(--red); margin-bottom:3px;
}
.from-eddie .who { color:#d9a06b; }
.when {
  float:right; font-size:10px; color:var(--sub);
  margin:8px 0 0 12px; font-style:italic;
}
.from-eddie .when { color:#c9a68a; }
#typing {
  min-height:20px; padding:2px 6% 0; color:var(--red);
  font-size:12px; font-style:italic; letter-spacing:1px;
}
footer {
  padding:12px 6% 16px; display:flex; gap:10px;
  background:linear-gradient(0deg,#3c2f1e,#2f2416);
  border-top:4px double var(--bronze);
}
input {
  flex:1; background:#1f1810; border:1px solid var(--bronze);
  color:#e8dcc3; padding:11px 16px; font-size:15px;
  font-family:Georgia,serif; outline:none;
}
input:focus { border-color:#c9a86a; }
button {
  background:linear-gradient(180deg,#a3854f,#7a5f35);
  border:1px solid #5a4632; color:#2b2016;
  padding:0 22px; cursor:pointer;
  font-family:Georgia,serif; font-size:14px;
  letter-spacing:2px;
}
button:hover { filter:brightness(1.12); }
</style></head>
<body>
<header>
  <span class="laurel">&#10087;</span>
  <h1>EDDIE&middot;AI</h1>
  <span class="motto">SENATVS POPVLVSQVE EDDIEI</span>
  <span id="conn">tabula aperitur&hellip;</span>
</header>
<div id="scroll">
  <div id="feed" style="display:contents"></div>
</div>
<div id="typing"></div>
<footer>
<input id="box" autofocus placeholder="Scribe&hellip;" autocomplete="off">
<button onclick="send()">SCRIBE</button>
</footer>
<script>
const feed = document.getElementById("feed");
const scrollBox = document.getElementById("scroll");
const typing = document.getElementById("typing");
const box = document.getElementById("box");
const conn = document.getElementById("conn");
let ws = null;

function esc(t) {
  const d = document.createElement("div");
  d.textContent = t;
  return d.innerHTML;
}
function hhmm(ts) {
  if (!ts) return "";
  const m = String(ts).match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "";
}
function bubble(sender, text, ts) {
  const eddieai = sender !== "Eddie";
  const row = document.createElement("div");
  row.className = "row" + (eddieai ? "" : " me");
  const who = eddieai
    ? '<span class="who">EDDIE&middot;AI</span>' : "";
  row.innerHTML = '<div class="msg ' +
    (eddieai ? "from-eddieai" : "from-eddie") + '">' +
    who + esc(text) +
    '<span class="when">' + esc(hhmm(ts)) +
    "</span></div>";
  feed.appendChild(row);
  scrollBox.scrollTop = scrollBox.scrollHeight;
}
function connect() {
  ws = new WebSocket(
    "ws://" + location.host + "/ws");
  ws.onopen = () => {
    conn.textContent = "tabula parata";
  };
  ws.onclose = () => {
    conn.textContent = "rursus&hellip;";
    setTimeout(connect, 2000);
  };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === "history") {
      m.items.forEach((i) =>
        bubble(i.sender, i.text, i.ts));
    } else if (m.type === "message") {
      bubble(m.sender, m.text, m.ts);
    } else if (m.type === "thinking") {
      typing.textContent = "EddieAI scribit&hellip;";
    } else if (m.type === "clear_typing") {
      typing.textContent = "";
    }
  };
}
function send() {
  const text = box.value.trim();
  if (!text || !ws) return;
  ws.send(JSON.stringify(
    { type: "message", text: text }));
  box.value = "";
}
box.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});
connect();
</script></body></html>"""


class WebMessenger:
    def __init__(
        self,
        server=None,
        history=None,
        host="127.0.0.1",
        port=7779,
    ):
        self.server = server
        self.history = history
        self.host = host
        self.port = port
        self._clients = set()
        self._lock = threading.Lock()
        self._loop = None
        self._tcp = None
        self.app = FastAPI()
        self.app.get("/")(self._index)
        self.app.get(
            "/api/history"
        )(self._api_history)
        self.app.websocket("/ws")(self._ws)
        self._register_tcp()

    # ---------------- HTTP ----------------

    async def _index(self):
        return HTMLResponse(HTML_PAGE)

    async def _api_history(self):
        return {
            "items": self._history_items(100)
        }

    def _history_items(self, limit):
        if self.history is None:
            return []
        try:
            return self.history.chat_recent(
                limit
            )
        except Exception:
            return []

    # ---------------- TCP bridge ----------------

    def _register_tcp(self):
        try:
            from communication.tcp_client import (
                EddieTCPClient,
            )

            self._tcp = EddieTCPClient()

            self._tcp.on_initiative(
                lambda text, msg_id=None,
                speak=True: self._push(
                    {
                        "type": "message",
                        "sender": "EddieAI",
                        "text": text,
                    }
                )
            )
            self._tcp.on_reply(
                lambda answer, msg_id=None: self._push(
                    {
                        "type": "message",
                        "sender": "EddieAI",
                        "text": answer,
                    }
                )
            )
            self._tcp.on_speech_chunk(
                lambda text, msg_id=None: self._push(
                    {
                        "type": "message",
                        "sender": "EddieAI",
                        "text": text,
                    }
                )
            )
            self._tcp.on_thinking(
                lambda msg_id=None: self._push(
                    {"type": "thinking"}
                )
            )
        except Exception:
            self._tcp = None

    def start(self):
        import uvicorn

        self._tcp_connect()

        thread = threading.Thread(
            target=self._serve,
            name="EddieAI-WebMessenger",
            daemon=True,
        )
        thread.start()

    def _tcp_connect(self):
        if self._tcp is not None:
            try:
                self._tcp.connect()
            except Exception:
                pass

    def _serve(self):
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(
            server.serve()
        )

    # ---------------- WebSocket ----------------

    def _push(self, payload):
        with self._lock:
            sockets = list(self._clients)

        for ws in sockets:
            try:
                asyncio.run_coroutine_threadsafe(
                    ws.send_json(payload),
                    self._loop,
                )
            except Exception:
                with self._lock:
                    self._clients.discard(ws)

    async def _ws(self, ws: WebSocket):
        await ws.accept()

        with self._lock:
            self._clients.add(ws)

        try:
            await ws.send_json({
                "type": "history",
                "items": self._history_items(
                    100
                ),
            })

            while True:
                raw = await ws.receive_json()

                if raw.get("type") != "message":
                    continue

                text = str(
                    raw.get("text", "")
                ).strip()

                if not text:
                    continue

                self._push({
                    "type": "message",
                    "sender": "Eddie",
                    "text": text,
                })

                server = self.server

                if server is not None:
                    try:
                        server.handle_user_message(
                            text
                        )
                    except Exception:
                        pass
        except WebSocketDisconnect:
            pass
        finally:
            with self._lock:
                self._clients.discard(ws)
