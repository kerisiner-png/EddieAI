import json
import socket
import threading
import time


RECONNECT_DELAYS = [1, 2, 5, 10]
MAX_BUFFER = 65536


class EddieTCPClient:

    def __init__(self, host="127.0.0.1", port=7778):
        self._host = host
        self._port = port
        self._sock = None
        self._lock = threading.Lock()
        self._connected = False
        self._running = False
        self._reader_thread = None
        self._initiative_callbacks = []
        self._history_callbacks = []
        self._thinking_callbacks = []
        self._reply_callbacks = []
        self._speech_chunk_callbacks = []
        self._call_ring_callbacks = []
        self._call_status_callbacks = []
        self._reconnect_index = 0

    def connect(self):
        with self._lock:
            if self._running:
                return
            self._running = True

        t = threading.Thread(
            target=self._run_loop,
            daemon=True,
        )
        self._reader_thread = t
        t.start()

    def disconnect(self):
        with self._lock:
            self._running = False
        self._close_socket()

    def is_connected(self):
        with self._lock:
            return self._connected

    def send(self, text):
        """
        Fire-and-forget: отправить сообщение, НЕ ждать
        ответа. EddieAI отвечает асинхронно через
        on_reply(), когда сам решит прочитать.
        """
        msg = json.dumps(
            {
                "type": "user_message",
                "text": text,
            },
            ensure_ascii=False,
        )

        with self._lock:
            if not self._connected:
                raise ConnectionError(
                    "Not connected to server"
                )
            try:
                self._sock.sendall(
                    (msg + "\n").encode("utf-8")
                )
            except OSError as e:
                self._connected = False
                raise ConnectionError(
                    f"Send failed: {e}"
                ) from e

    def on_initiative(self, callback):
        with self._lock:
            self._initiative_callbacks.append(callback)

    def on_history(self, callback):
        with self._lock:
            self._history_callbacks.append(callback)

    def on_thinking(self, callback):
        with self._lock:
            self._thinking_callbacks.append(callback)

    def on_reply(self, callback):
        with self._lock:
            self._reply_callbacks.append(callback)

    def on_speech_chunk(self, callback):
        with self._lock:
            self._speech_chunk_callbacks.append(callback)

    def mark_read(self, msg_id):
        msg = json.dumps({
            "type": "mark_read",
            "msg_id": msg_id,
        }, ensure_ascii=False)
        with self._lock:
            if not self._connected:
                return
            try:
                self._sock.sendall(
                    (msg + "\n").encode("utf-8")
                )
            except OSError:
                pass

    def _send_raw(self, payload):
        data = json.dumps(
            payload,
            ensure_ascii=False,
        )
        with self._lock:
            if not self._connected:
                return
            try:
                self._sock.sendall(
                    (data + "\n").encode("utf-8")
                )
            except OSError:
                pass

    def send_call(self, kind, payload=None):
        """
        Отправить управляющее событие звонка.
        kind: call_ring / call_answer / call_reject / call_end.
        """
        msg = dict(payload or {})
        msg["type"] = kind
        self._send_raw(msg)

    def on_call_ring(self, callback):
        with self._lock:
            self._call_ring_callbacks.append(callback)

    def on_call_status(self, callback):
        with self._lock:
            self._call_status_callbacks.append(callback)

    def _run_loop(self):
        while self._running:
            try:
                self._connect_socket()
                self._reconnect_index = 0
                self._reader()
            except Exception:
                pass
            finally:
                with self._lock:
                    self._connected = False
                self._close_socket()

            if not self._running:
                break
            delay = RECONNECT_DELAYS[
                min(
                    self._reconnect_index,
                    len(RECONNECT_DELAYS) - 1,
                )
            ]
            self._reconnect_index += 1
            time.sleep(delay)

    def _connect_socket(self):
        self._close_socket()
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        sock.settimeout(5)
        sock.connect((self._host, self._port))
        sock.settimeout(None)
        with self._lock:
            self._sock = sock
            self._connected = True

    def _reader(self):
        buf = b""
        while self._running:
            try:
                chunk = self._sock.recv(MAX_BUFFER)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._handle_line(line)

    def _handle_line(self, raw):
        try:
            msg = json.loads(
                raw.decode("utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type")
        text = msg.get("text", "")
        msg_id = msg.get("msg_id")

        if msg_type == "agent_message":
            with self._lock:
                cbs = list(
                    self._reply_callbacks
                )
            for cb in cbs:
                try:
                    cb(text, msg_id)
                except Exception:
                    pass

        elif msg_type == "agent_initiative":
            with self._lock:
                cbs = list(
                    self._initiative_callbacks
                )
            for cb in cbs:
                try:
                    cb(text, msg_id)
                except Exception:
                    pass

        elif msg_type == "history":
            messages = msg.get("messages", [])

            with self._lock:
                cbs = list(
                    self._history_callbacks
                )
            for cb in cbs:
                try:
                    cb(messages)
                except Exception:
                    pass

        elif msg_type == "agent_thinking":
            with self._lock:
                cbs = list(
                    self._thinking_callbacks
                )
            for cb in cbs:
                try:
                    cb(msg_id)
                except Exception:
                    pass

        elif msg_type == "agent_speech_chunk":
            with self._lock:
                cbs = list(
                    self._speech_chunk_callbacks
                )
            for cb in cbs:
                try:
                    cb(text, msg_id)
                except Exception:
                    pass

        elif msg_type in (
            "call_ring",
            "call_status",
        ):
            state = msg.get(
                "state",
                msg_type,
            )
            direction = msg.get(
                "direction",
            )

            with self._lock:
                cbs = list(
                    self._call_ring_callbacks
                    if msg_type == "call_ring"
                    else self._call_status_callbacks
                )
            for cb in cbs:
                try:
                    cb(state, direction)
                except Exception:
                    pass

    def _close_socket(self):
        with self._lock:
            sock = self._sock
            self._sock = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
