# -*- coding: utf-8 -*-
# Патч: мессенджер для обоих — картинки от Эдди (vision),
# «Эдди печатает» в поток, симметричные подписи.
p = 'communication/web_messenger.py'
s = open(p, encoding='utf-8').read()

# --- 1. подпись EDDIE на своих сообщениях (симметрия) ---
old = '''  const who = me
    ? "" : '<span class="who">EDDIE&middot;AI</span>';'''
new = '''  const who = me
    ? '<span class="who">EDDIE</span>'
    : '<span class="who">EDDIE&middot;AI</span>';'''
assert s.count(old) == 1, "who: %d" % s.count(old)
s = s.replace(old, new)

# --- 2. обработка входящих изображений и «печатает» на сервере ---
old2 = '''                if raw.get("type") != "message":
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
                        pass'''
new2 = '''                if raw.get("type") == "typing":
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
                        pass'''
assert s.count(old2) == 1, "ws loop: %d" % s.count(old2)
s = s.replace(old2, new2)

# --- 3. методы: eddie_typing → поток; изображение → vision ---
old3 = '''    async def _ws(self, ws: WebSocket):
        await ws.accept()'''
new3 = '''    def _eddie_typing(self):
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

        bucket = str(
            int(_t.time() // 10)
        )
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
        await ws.accept()'''
assert s.count(old3) == 1, "_ws anchor: %d" % s.count(old3)
s = s.replace(old3, new3, 1)

# --- 4. клиент: вставка картинок (paste/файл) и «печатает» ---
old4 = '''    }, 120);
  } catch (e) {}
}
connect();'''
new4_tail = '''    }, 120);
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
connect();'''
new4 = '''box.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});
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
connect();'''
assert s.count(old4) == 1, "js tail: %d" % s.count(old4)
s = s.replace(old4, new4_tail)

open(p, 'w', encoding='utf-8', newline='\n').write(s)
import py_compile
py_compile.compile(p, doraise=True)
print('both-sides messenger applied, COMPILE OK')
