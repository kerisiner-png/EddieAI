# -*- coding: utf-8 -*-
# Патч UI v3: галочки, даты, поиск, PLVS, уведомления, канал FLVMEN.
p = 'communication/web_messenger.py'
s = open(p, encoding='utf-8').read()

# --- 1. CSS-дополнения перед </style> ---
css_add = '''.receipt {
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
</style>'''
s = s.replace('</style>', css_add, 1)
assert 'receipt' in s

# --- 2. кнопки в header ---
s = s.replace(
    '  <span id="conn">tabvla aperitvr&hellip;</span>',
    '  <button class="hbtn" id="qvaerere"\n'
    '    onclick="toggleSearch()">QVAERERE</button>\n'
    '  <button class="hbtn" id="flvmen"\n'
    '    onclick="toggleFlumen()">FLVMEN</button>\n'
    '  <span id="conn">tabvla aperitvr&hellip;</span>',
    1,
)

# --- 3. PLVS внутри scroll ---
s = s.replace(
    '<div id="scroll">\n  <div id="feed" style="display:contents"></div>',
    '<div id="scroll">\n'
    '  <div id="plvs"><button onclick="loadMore()">PLVS</button></div>\n'
    '  <div id="feed" style="display:contents"></div>',
    1,
)

# --- 4. панель и поиск перед footer ---
s = s.replace(
    '<footer>',
    '<div id="panel">\n'
    '  <h2>FLVMEN — ВНУТРЕННИЙ ПОТОК\n'
    '    <button onclick="toggleFlumen()">✕</button></h2>\n'
    '  <div class="moodbox" id="moodbox"></div>\n'
    '  <div id="flist"></div>\n'
    '</div>\n\n'
    '<div id="searchbox">\n'
    '  <input id="q" placeholder="Qvaerere в истории…"\n'
    '    oninput="doSearch()">\n'
    '  <div id="qres"></div>\n'
    '</div>\n\n'
    '<footer>',
    1,
)

# --- 5. новый JS ---
old_js_start = s.index('<script>')
old_js_end = s.index('</script>')
new_js = '''<script>
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
  const m = String(ts).match(/T(\\d{2}:\\d{2})/);
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
    ? "" : '<span class="who">EDDIE&middot;AI</span>';
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
</script>'''
s = s[:old_js_start] + new_js + s[old_js_end:]

open(p, 'w', encoding='utf-8', newline='\n').write(s)
import py_compile
py_compile.compile(p, doraise=True)
print('UI v3 applied, COMPILE OK')
