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
.receipt {
  font-size:10px; margin-left:4px; color:#c9b28a;
}
.receipt.read { color:#7ec97e; }
.date-sep {
  text-align:center; color:#8a7555; font-size:11px;
  letter-spacing:3px; margin:6px 0 2px;
}
.date-sep span {
  border-top:1px solid #b09a6a; border-bottom:1px solid #b09a6a;
  padding:3px 12px;
}
#plvs { text-align:center; margin-bottom:8px; }
#plvs button {
  background:transparent; border:1px solid #c9a227;
  color:#8a7555; font-family:Georgia,serif;
  letter-spacing:3px; font-size:11px; padding:4px 14px;
  cursor:pointer;
}
#plvs button:hover { color:#e8c85a; border-color:#e8c85a; }
#panel {
  display:none; position:fixed; top:0; right:0;
  width:min(420px, 45vw); height:100vh;
  background:linear-gradient(180deg,#2c060a,#1d0406);
  border-left:2px solid #c9a227;
  box-shadow:-6px 0 24px rgba(0,0,0,.6);
  z-index:50; padding:14px 18px; overflow-y:auto;
}
#panel h2 {
  font-weight:normal; font-size:14px;
  letter-spacing:4px; color:#e8c85a;
  border-bottom:1px solid #8a6f1f; padding-bottom:8px;
  display:flex; justify-content:space-between;
}
#panel h2 button {
  background:none; border:none; color:#c9a227;
  cursor:pointer; font-size:16px;
}
.moodbox {
  margin:10px 0; padding:10px 12px;
  border:1px solid #8a6f1f;
  background:rgba(0,0,0,.25);
}
.moodbox .lbl { color:#e0b45e; font-size:12px;
  letter-spacing:2px; }
.moodbox .v { font-size:13px; }
.item {
  padding:6px 0; border-bottom:1px dashed #6b1218;
  font-size:13px;
}
.item .k {
  color:#c9a86a; font-size:10px; letter-spacing:2px;
  display:block;
}
#searchbox {
  display:none; position:fixed; top:60px; left:50%;
  transform:translateX(-50%); width:min(640px, 80vw);
  background:linear-gradient(180deg,#2c060a,#1d0406);
  border:2px solid #c9a227; z-index:60; padding:12px;
  box-shadow:0 8px 30px rgba(0,0,0,.7);
}
#searchbox input {
  width:100%; margin-bottom:8px;
}
.sres { padding:6px 8px; border-bottom:1px solid #6b1218;
  font-size:13px; cursor:pointer; }
.sres:hover { background:#430a0e; }
.sres .s { color:#c9a86a; font-size:10px;
  letter-spacing:2px; display:block; }
.hbtn {
  position:absolute; top:10px; background:transparent;
  border:1px solid #c9a227; color:#e0b45e; cursor:pointer;
  font-family:Georgia,serif; font-size:11px;
  letter-spacing:2px; padding:5px 10px;
}
.hbtn:hover { background:#7a1f1f; }
#qvaerere { left:18px; }
#flvmen { right:18px; }
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
  <button class="hbtn" id="qvaerere"
    onclick="toggleSearch()">QVAERERE</button>
  <button class="hbtn" id="flvmen"
    onclick="toggleFlumen()">FLVMEN</button>
  <span id="conn">tabvla aperitvr&hellip;</span>
</header>
<div id="scroll">
  <div id="plvs"><button onclick="loadMore()">PLVS</button></div>
  <div id="feed" style="display:contents"></div>
</div>
<div id="typing"></div>
<div id="panel">
  <h2>FLVMEN — ВНУТРЕННИЙ ПОТОК
    <button onclick="toggleFlumen()">✕</button></h2>
  <div class="moodbox" id="moodbox"></div>
  <div id="flist"></div>
</div>

<div id="searchbox">
  <input id="q" placeholder="Qvaerere в истории…"
    oninput="doSearch()">
  <div id="qres"></div>
</div>

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
let firstId = null;
let flumenOn = false;

function esc(t) {
  const d = document.createElement("div");
  d.textContent = t == null ? "" : String(t);
  return d.innerHTML;
}
function hhmm(ts) {
  if (!ts) return "";
  const m = String(ts).match(/T(\d{2}:\d{2})/);
  return m ? m[1] : "";
}
function dayKey(ts) {
  return String(ts || "").slice(0, 10);
}
function dayLabel(key) {
  const today = new Date().toISOString().slice(0, 10);
  const yest = new Date(Date.now() - 864e5)
    .toISOString().slice(0, 10);
  if (key === today) return "HODIE";
  if (key === yest) return "HERI";
  return key.split("-").reverse().join(".");
}
function dateSepIfNeeded(ts) {
  const key = dayKey(ts);
  if (key && key !== feed.dataset.lastDay) {
    feed.dataset.lastDay = key;
    const d = document.createElement("div");
    d.className = "date-sep";
    d.innerHTML = "<span>" + esc(dayLabel(key)) +
      "</span>";
    feed.appendChild(d);
  }
}
function receipt(item) {
  if (item.sender !== "Eddie") return "";
  return item.read
    ? ' <span class="receipt read">✓✓</span>'
    : ' <span class="receipt">✓</span>';
}
function bubble(item) {
  dateSepIfNeeded(item.ts);
  const me = item.sender === "Eddie";
  const row = document.createElement("div");
  row.className = "row" + (me ? " me" : "");
  const who = me
    ? '<span class="who">EDDIE</span>'
    : '<span class="who">EDDIE&middot;AI</span>';
  row.innerHTML = '<div class="msg ' +
    (me ? "from-eddie" : "from-eddieai") + '">' +
    who + esc(item.text) +
    '<span class="when">' + esc(hhmm(item.ts)) +
    receipt(item) + "</span></div>";
  feed.appendChild(row);
  scrollBox.scrollTop = scrollBox.scrollHeight;
  if (me && item.id) firstId = firstId || item.id;
}
function notify(text) {
  beep();
  try {
    if (Notification.permission === "granted") {
      new Notification("EDDIE·AI", {
        body: text.slice(0, 120),
      });
    } else if (
      Notification.permission !== "denied"
    ) {
      Notification.requestPermission();
    }
  } catch (e) {}
}
function beep() {
  try {
    const ctx = new (window.AudioContext ||
      window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.frequency.value = 660;
    g.gain.value = 0.06;
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    setTimeout(() => {
      o.stop();
      ctx.close();
    }, 120);
  } catch (e) {}
}
box.addEventListener("input", () => {
  if (!ws) return;
  const now = Date.now();
  if (now - (window._lastTyping || 0) > 3000) {
    window._lastTyping = now;
    ws.send(JSON.stringify({ type: "typing" }));
  }
});
document.addEventListener("paste", (e) => {
  for (const item of (e.clipboardData || {}).items || []) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      sendImage(file);
      e.preventDefault();
      return;
    }
  }
});
function sendImage(file) {
  if (!file || !ws) return;
  const reader = new FileReader();
  reader.onload = () => {
    ws.send(JSON.stringify({
      type: "image",
      data: reader.result,
    }));
  };
  reader.readAsDataURL(file);
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
      m.items.forEach(bubble);
    } else if (m.type === "message") {
      bubble({
        sender: m.sender,
        text: m.text,
        ts: m.ts || new Date().toISOString(),
      });
      if (m.sender === "EddieAI" &&
          document.hidden) {
        notify(m.text);
      }
      typing.textContent = "";
    } else if (m.type === "thinking") {
      typing.textContent = "EddieAI scribit&hellip;";
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
async function loadMore() {
  const r = await fetch(
    "/api/history?before_id=" + (firstId || 0));
  const data = await r.json();
  if (!data.items.length) {
    document.getElementById("plvs")
      .style.display = "none";
    return;
  }
  firstId = data.items[0].id;
  const keep = scrollBox.scrollHeight;
  const lastDay = feed.dataset.lastDay;
  feed.dataset.lastDay = "";
  data.items.slice().forEach((item) => {
    const row = document.createElement("div");
    row.className = "row" +
      (item.sender === "Eddie" ? " me" : "");
    const who = item.sender === "Eddie"
      ? "" : '<span class="who">EDDIE&middot;AI</span>';
    row.innerHTML = '<div class="msg ' +
      (item.sender === "Eddie"
        ? "from-eddie" : "from-eddieai") + '">' +
      who + esc(item.text) +
      '<span class="when">' + esc(hhmm(item.ts)) +
      receipt(item) + "</span></div>";
    feed.insertBefore(row, feed.firstChild);
  });
  scrollBox.scrollTop =
    scrollBox.scrollHeight - keep + 200;
  feed.dataset.lastDay = lastDay;
}
function toggleSearch() {
  const sb = document.getElementById("searchbox");
  sb.style.display =
    sb.style.display === "block" ? "none" : "block";
  document.getElementById("q").focus();
}
async function doSearch() {
  const q = document.getElementById("q").value;
  if (!q.trim()) {
    document.getElementById("qres").innerHTML = "";
    return;
  }
  const r = await fetch(
    "/api/search?q=" + encodeURIComponent(q));
  const data = await r.json();
  document.getElementById("qres").innerHTML =
    data.items.map((i) =>
      '<div class="sres" onclick="closeSearch()">'
      + '<span class="s">' + esc(i.sender) + " · " +
      esc(hhmm(i.ts)) + "</span>" +
      esc(i.text.slice(0, 140)) + "</div>"
    ).join("");
}
function closeSearch() {
  document.getElementById("searchbox")
    .style.display = "none";
}
function toggleFlumen() {
  flumenOn = !flumenOn;
  document.getElementById("panel").style.display =
    flumenOn ? "block" : "none";
  if (flumenOn) refreshFlumen();
}
async function refreshFlumen() {
  if (!flumenOn) return;
  const r = await fetch("/api/stream");
  const data = await r.json();
  document.getElementById("moodbox").innerHTML =
    '<span class="lbl">MOOD</span><div class="v">' +
    esc((data.mood || {}).label || "—") +
    " · valence " +
    ((data.mood || {}).valence ?? "—") +
    " · energy " +
    ((data.mood || {}).energy ?? "—") + "</div>";
  document.getElementById("flist").innerHTML =
    (data.items || []).map((i) =>
      '<div class="item"><span class="k">' +
      esc(i.kind.toUpperCase()) + "</span>" +
      esc(i.text) + "</div>"
    ).join("") || "поток пуст";
}
setInterval(refreshFlumen, 5000);
connect();
</script></script></body></html>"""


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
        self.app.get(
            "/api/search"
        )(self._api_search)
        self.app.get(
            "/api/stream"
        )(self._api_stream)
        self.app.websocket("/ws")(self._ws)
        self._register_tcp()

    # ---------------- HTTP ----------------

    async def _index(self):
        return HTMLResponse(HTML_PAGE)

    async def _api_history(self, before_id: int = 0):
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
        return self._stream_state()

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

    def _eddie_typing(self):
        """
        Эдди печатает — событие в поток
        (ведро 10 секунд, чтобы не спамить).
        """
        import time as _t

        agent = getattr(
            self.server, "agent", None
        )
        stream = getattr(
            agent, "inner_stream", None
        )
        if stream is None:
            return

        bucket = str(int(_t.time() // 10))
        stream.note_event(
            "Эдди печатает",
            bucket,
            "Эдди печатает в Tabula…",
            0.15,
        )

    async def _on_eddie_image(
        self, ws: WebSocket, data_b64: str
    ):
        """
        Эдди показал картинку: сохраняем,
        смотрим глазами (vision), реагируем
        в чате.
        """
        import base64
        import time as _t
        from pathlib import Path

        raw = data_b64.split(",")[-1]

        if not raw or len(raw) > 4_000_000:
            return

        inbox = Path("data") / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        name = (
            "imago_%s.png"
            % _t.strftime("%Y%m%d_%H%M%S")
        )
        path = inbox / name

        try:
            path.write_bytes(
                base64.b64decode(raw)
            )
        except Exception:
            return

        self._push({
            "type": "message",
            "sender": "Eddie",
            "text": "[imago] " + name,
        })

        agent = getattr(
            self.server, "agent", None
        )
        if agent is None:
            return

        body = getattr(agent, "body", None)
        if body is not None:
            body.satisfy_social()

        stream = getattr(
            agent, "inner_stream", None
        )
        if stream is not None:
            stream.note_event(
                "imago",
                name,
                "Эдди показал изображение",
                1.2,
            )

        try:
            orchestrator = (
                agent.model_orchestrator
            )
            result = (
                orchestrator._cloud_chat_vision(
                    "Ты EddieAI. Эдди показал тебе "
                    "это изображение в мессенджере. "
                    "Скажи коротко (1-2 предложения), "
                    "что видишь и что думаешь.",
                    "Что на изображении?",
                    [raw],
                )
            )
            text = (
                result.get("text", "").strip()
                if isinstance(result, dict)
                else str(result or "").strip()
            )
        except Exception:
            text = ""

        if not text:
            text = (
                "Не разглядел картинку — "
                "покажи ещё раз?"
            )

        if self.history is not None:
            try:
                self.history.chat_add(
                    "EddieAI", text
                )
            except Exception:
                pass

        self._push({
            "type": "message",
            "sender": "EddieAI",
            "text": text,
        })

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

                if raw.get("type") == "typing":
                    self._eddie_typing()
                    continue

                if raw.get("type") == "image":
                    await self._on_eddie_image(
                        ws,
                        str(raw.get("data", "")),
                    )
                    continue

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
