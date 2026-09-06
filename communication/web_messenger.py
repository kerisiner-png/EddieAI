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
* { box-sizing:border-box; margin:0; }
body {
  min-height:100vh; display:flex; flex-direction:column;
  color:#f0e6cf;
  font:15px/1.5 Georgia,'Times New Roman',serif;
  background:
    radial-gradient(1100px 500px at 50% -8%,
      rgba(255,205,120,.12), transparent 60%),
    repeating-linear-gradient(115deg,
      rgba(0,0,0,.10) 0 2px, transparent 2px 90px),
    repeating-linear-gradient(65deg,
      rgba(255,255,255,.03) 0 2px, transparent 2px 110px),
    linear-gradient(175deg,#5c1016,#430a0e 55%,#2c060a);
}
header {
  display:flex; align-items:center; justify-content:center;
  gap:18px; padding:14px 18px 12px;
  background:linear-gradient(180deg,#6b1218,#430a0e);
  border-bottom:3px solid #c9a227;
  box-shadow:0 3px 18px rgba(0,0,0,.55);
}
header svg { opacity:.95; }
.header-text { text-align:center; }
header h1 {
  font-size:21px; font-weight:normal; color:#e8c85a;
  letter-spacing:9px; text-shadow:0 1px 3px rgba(0,0,0,.8);
}
header .motto {
  display:block; margin-top:3px; font-size:10px;
  letter-spacing:4px; color:#c9a86a;
}
header #conn {
  position:absolute; right:20px; top:16px;
  font-size:12px; font-style:italic; color:#d9b36c;
}
#scroll {
  flex:1; overflow-y:auto; margin:14px 8%;
  padding:18px 24px; display:flex; flex-direction:column;
  gap:10px;
  border:2px solid #c9a227;
  outline:6px solid #7a1f1f;
  outline-offset:5px;
  background:
    linear-gradient(103deg, transparent 46%,
      rgba(120,105,90,.14) 47%, transparent 48.5%),
    linear-gradient(76deg, transparent 28%,
      rgba(120,105,90,.11) 29.5%, transparent 31%),
    linear-gradient(158deg, transparent 58%,
      rgba(120,105,90,.09) 59%, transparent 61%),
    linear-gradient(180deg,#f8f3e9,#ece3d0);
  box-shadow:0 6px 30px rgba(0,0,0,.5),
    inset 0 0 60px rgba(140,120,90,.18);
}
#scroll::-webkit-scrollbar { width:10px; }
#scroll::-webkit-scrollbar-track { background:#430a0e; }
#scroll::-webkit-scrollbar-thumb {
  background:linear-gradient(180deg,#c9a227,#8a6f1f);
}
.row { display:flex; }
.row.me { justify-content:flex-end; }
.msg {
  max-width:70%; padding:10px 14px;
  border-radius:2px; position:relative;
}
.from-eddieai {
  background:linear-gradient(180deg,#fbf7ee,#f0e8d6);
  border:1px solid #c9a227;
  border-left:5px solid #7a1f1f;
  color:#2b2320;
  box-shadow:0 2px 8px rgba(0,0,0,.25);
}
.from-eddie {
  background:
    radial-gradient(340px 60px at 85% 0%,
      rgba(255,190,120,.16), transparent 70%),
    linear-gradient(160deg,#8f1d20,#5e0f14);
  border:1px solid #c9a227;
  color:#f5e9c8;
  box-shadow:0 2px 10px rgba(0,0,0,.4);
}
.who {
  display:block; font-size:10px; letter-spacing:4px;
  color:#7a1f1f; margin-bottom:4px;
}
.from-eddie .who { color:#e0b45e; }
.when {
  float:right; font-size:10px; color:#8a7555;
  margin:8px 0 0 12px; font-style:italic;
}
.from-eddie .when { color:#d8b98e; }
#typing {
  min-height:20px; padding:2px 8%; color:#e0b45e;
  font-size:12px; font-style:italic; letter-spacing:1px;
}
footer {
  display:flex; gap:10px; padding:12px 8% 16px;
  background:linear-gradient(0deg,#5c1016,#430a0e);
  border-top:3px solid #c9a227;
}
input {
  flex:1; background:#2c060a;
  border:1px solid #c9a227; color:#f0e6cf;
  padding:12px 16px; font-size:15px;
  font-family:Georgia,serif; outline:none;
}
input:focus { border-color:#e8c85a;
  box-shadow:0 0 0 1px #e8c85a inset; }
button {
  background:linear-gradient(180deg,#e8c85a,#c9a227);
  border:1px solid #8a6f1f; color:#430a0e;
  padding:0 24px; cursor:pointer;
  font-family:Georgia,serif; font-size:14px;
  letter-spacing:3px; font-weight:bold;
}
button:hover { filter:brightness(1.08); }
</style></head>
<body>
<header>
  <svg width="52" height="34" viewBox="0 0 100 66" fill="#c9a227">
    <path d="M96 6C70 8 50 22 44 52l6 2C56 28 74 14 96 10Z"/>
    <ellipse cx="88" cy="10" rx="9" ry="4" transform="rotate(-18 88 10)"/>
    <ellipse cx="74" cy="16" rx="9" ry="4" transform="rotate(-30 74 16)"/>
    <ellipse cx="61" cy="25" rx="9" ry="4" transform="rotate(-42 61 25)"/>
    <ellipse cx="51" cy="36" rx="9" ry="4" transform="rotate(-56 51 36)"/>
    <ellipse cx="45" cy="48" rx="9" ry="4" transform="rotate(-70 45 48)"/>
  </svg>
  <div class="header-text">
    <h1>EDDIE&middot;AI</h1>
    <span class="motto">S&#183;P&#183;Q&#183;R &mdash; TABVLA SERMONIS</span>
  </div>
  <svg width="52" height="34" viewBox="0 0 100 66" fill="#c9a227"
    style="transform:scaleX(-1)">
    <path d="M96 6C70 8 50 22 44 52l6 2C56 28 74 14 96 10Z"/>
    <ellipse cx="88" cy="10" rx="9" ry="4" transform="rotate(-18 88 10)"/>
    <ellipse cx="74" cy="16" rx="9" ry="4" transform="rotate(-30 74 16)"/>
    <ellipse cx="61" cy="25" rx="9" ry="4" transform="rotate(-42 61 25)"/>
    <ellipse cx="51" cy="36" rx="9" ry="4" transform="rotate(-56 51 36)"/>
    <ellipse cx="45" cy="48" rx="9" ry="4" transform="rotate(-70 45 48)"/>
  </svg>
  <span id="conn">tabvla aperitvr&hellip;</span>
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
    conn.textContent = "tabvla parata";
  };
  ws.onclose = () => {
    conn.textContent = "rvrsvs&hellip;";
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
