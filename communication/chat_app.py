import queue
import socket
import threading
import tkinter as tk

from core.agent import Agent
from core.eddie_server import EddieServer
from communication.tcp_client import EddieTCPClient
from communication.ui_chat import ChatWindow
from communication.tray import TrayIcon
from communication.call_engine import (
    CallDirector,
    EDDIE_SPEAKING,
    EDDIEAI_SPEAKING,
)


class EddieChatApp:

    def __init__(
        self,
        agent=None,
        server=None,
    ):
        self._owns_agent = (
            agent is None
        )
        self._agent = (
            agent
            if agent is not None
            else Agent()
        )
        self._server = (
            server
            if server is not None
            else EddieServer(
                self._agent,
                history_store=(
                    self._agent.memory
                ),
            )
        )
        self._tcp = EddieTCPClient()
        self._tray = TrayIcon()
        try:
            from communication.voice_io import VoiceIO

            self._voice = VoiceIO()
        except Exception:
            self._voice = None
        self._call = CallDirector()
        self._call.set_interrupt_callback(
            self._on_eddie_interrupt
        )
        self._awaiting_speech_end = False

        if self._server is not None:
            try:
                self._server.call_director = (
                    self._call
                )
            except Exception:
                pass
        self._chat = None
        self._root = None
        self._tcp_server = None
        self._ui_queue = queue.Queue()
        self._pending_lock = (
            threading.Lock()
        )
        self._pending_sends = 0

    def is_busy(self) -> bool:
        with self._pending_lock:
            return self._pending_sends > 0

    def _post_ui(self, fn, *args):
        self._ui_queue.put((fn, args))

    def _drain_queue(self):
        while True:
            try:
                fn, args = (
                    self._ui_queue.get_nowait()
                )
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:
                pass

    def start_embedded(self):
        """
        Режим внутри сессии EddieAI:
        подготовить всё, но НЕ запускать mainloop.
        События tkinter обрабатываются через update()
        из главного цикла сессии.
        """
        self._root = tk.Tk()
        self._root.withdraw()
        self._chat = ChatWindow()

        self._tray.on_open_chat(self._on_open_chat)
        self._tray.on_exit(self._on_exit)
        self._chat.on_send(self._on_user_send)
        if hasattr(
            self._chat, "on_mic"
        ):
            self._chat.on_mic(self._on_mic)
        self._chat.on_call(self._on_call_toggle)
        self._tcp.on_initiative(self._on_initiative)
        self._tcp.on_history(self._on_history)
        self._tcp.on_thinking(self._on_thinking)
        self._tcp.on_reply(self._on_reply)

        self._tray.start()

        self._chat.set_status("Запуск сервера...")
        t = threading.Thread(
            target=self._run_server,
            daemon=True,
        )
        t.start()

        connected = self._wait_port(7778, timeout=15)

        if connected:
            self._tcp.connect()
            self._chat.set_status("Подключено")
        else:
            self._chat.set_status(
                "Ошибка: сервер не запустился"
            )

    def update(self):
        if self._root is None:
            return
        self._drain_queue()
        try:
            self._root.update()
        except tk.TclError:
            pass

    def stop(self):
        self._cleanup()
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass

    def start(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._chat = ChatWindow()

        self._tray.on_open_chat(self._on_open_chat)
        self._tray.on_exit(self._on_exit)
        self._chat.on_send(self._on_user_send)
        self._chat.on_mic(self._on_mic)
        self._chat.on_call(self._on_call_toggle)
        self._tcp.on_initiative(self._on_initiative)
        self._tcp.on_history(self._on_history)
        self._tcp.on_thinking(self._on_thinking)
        self._tcp.on_reply(self._on_reply)

        self._tray.start()

        self._chat.set_status("Запуск сервера...")
        t = threading.Thread(
            target=self._run_server, daemon=True
        )
        t.start()

        if not self._wait_port(7778, timeout=15):
            self._chat.set_status(
                "Ошибка: сервер не запустился"
            )
            self._chat.show()
            self._root.mainloop()
            return

        self._chat.set_status("Подключение...")
        self._tcp.connect()

        self._root.after(500, self._check_connected)
        self._root.after(100, self._drain_loop)

        self._chat.show()
        self._root.mainloop()

    def _drain_loop(self):
        self._drain_queue()
        if self._root is None:
            return
        try:
            self._root.after(
                100, self._drain_loop
            )
        except tk.TclError:
            pass

    def _run_server(self):
        try:
            self._tcp_server = (
                self._server.serve_forever()
            )
        except Exception:
            pass

    def _wait_port(self, port, timeout=15):
        deadline = _monotonic() + timeout
        while _monotonic() < deadline:
            try:
                s = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
                s.close()
                return True
            except OSError:
                _sleep(0.3)
        return False

    def _check_connected(self):
        if self._tcp.is_connected():
            self._chat.set_status("Подключено")
        else:
            self._chat.set_status(
                "Ожидание подключения..."
            )
            self._root.after(
                1000, self._check_connected
            )

    def _on_initiative(self, text, msg_id=None):
        self._post_ui(
            self._show_initiative,
            text,
            msg_id,
        )

    def _show_initiative(self, text, msg_id=None):
        if self._chat is None:
            return
        self._chat.append_message(
            "EddieAI", text
        )
        if (
            msg_id is not None
            and self._chat.is_visible()
        ):
            self._tcp.mark_read(msg_id)
        try:
            preview = text.strip()
            if len(preview) > 80:
                preview = preview[:80] + "…"
            self._tray.show_balloon(
                "EddieAI хочет сказать",
                preview,
            )
        except Exception:
            pass
        if (
            self._voice
            and self._chat.is_voice_mode()
        ):
            from communication.voice_io import (
                mood_from_agent,
            )

            self._speak_with_detector(
                text,
                mood_from_agent(self._agent),
            )

    def _on_history(self, messages):
        self._post_ui(
            self._chat.show_history,
            messages,
        )

    def _on_thinking(self, msg_id):
        self._post_ui(
            self._chat.set_status,
            "EddieAI думает...",
        )

        def mark():
            if self._chat is not None:
                self._chat.mark_eddie_read()

        self._post_ui(mark)

    def _on_user_send(self, text):
        self._chat.append_message("Eddie", text)
        self._chat.set_status(
            "Сообщение отправлено"
        )
        threading.Thread(
            target=self._send_only,
            args=(text,),
            daemon=True,
        ).start()

    def _send_only(self, text):
        try:
            self._tcp.send(text)
        except ConnectionError:
            self._post_ui(
                self._set_status_safe,
                "Оффлайн: сообщение не доставлено",
            )
            return
        except Exception:
            self._post_ui(
                self._set_status_safe,
                "Ошибка отправки",
            )
            return

    def _on_reply(self, answer, msg_id=None):
        self._post_ui(
            self._show_reply,
            answer,
            msg_id,
        )

    def _show_reply(self, answer, msg_id=None):
        if self._chat is None:
            return
        self._chat.append_message(
            "EddieAI", answer
        )

        if (
            msg_id is not None
            and self._chat.is_visible()
        ):
            self._tcp.mark_read(msg_id)
        elif not self._chat.is_visible():
            try:
                preview = answer.strip()
                if len(preview) > 80:
                    preview = (
                        preview[:80] + "…"
                    )
                self._tray.show_balloon(
                    "EddieAI ответил",
                    preview,
                )
            except Exception:
                pass

        if (
            self._voice
            and self._chat.is_voice_mode()
        ):
            from communication.voice_io import (
                mood_from_agent,
            )

            self._speak_with_detector(
                answer,
                mood_from_agent(self._agent),
            )

    def _set_status_safe(self, text):
        if self._chat is None:
            return
        self._chat.set_status(text)

    def _speak_with_detector(self, text, mood):
        self._voice.speak(text, mood=mood)
        if not self._call.in_call():
            return
        self._call.eddieai_starts_speaking()
        self._voice.on_interrupt_detector_end(
            self._on_detected_speech_end
        )
        self._voice.start_interrupt_detector(
            self._on_detected_speech
        )

        def reap():
            if not self._awaiting_speech_end:
                self._voice.stop_interrupt_detector()
            self._call.eddieai_stops_speaking()

        threading.Timer(
            max(0.1, self._est_speech_sec(text)),
            reap,
        ).start()

    def _est_speech_sec(self, text):
        return min(60.0, 0.28 + len(text) * 0.09)

    def _on_detected_speech(self):
        self._awaiting_speech_end = True
        self._call.eddie_starts_speaking()

    def _on_detected_speech_end(self):
        self._awaiting_speech_end = False
        self._call.eddie_stops_speaking()

    def _on_eddie_interrupt(self):
        if self._voice:
            try:
                self._voice.stop_speaking()
            except Exception:
                pass

    def _on_mic(self):
        if not self._voice:
            self._chat.set_status(
                "Голос недоступен (Vosk)"
            )
            return
        self._chat.set_status("Запись...")
        threading.Thread(
            target=self._mic_worker, daemon=True
        ).start()

    def _mic_worker(self):
        text = self._voice.record_and_transcribe()
        if text:
            self._post_ui(
                self._on_user_send, text
            )
        else:
            self._post_ui(
                self._set_status_safe,
                "Речь не распознана",
            )

    def _on_open_chat(self):
        self._post_ui(self._show_chat)

    def _show_chat(self):
        if self._chat is None:
            return
        self._chat.show()

    def _on_exit(self):
        self._post_ui(self._exit_from_tray)

    def _exit_from_tray(self):
        self._cleanup()
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass

    def _cleanup(self):
        try:
            self._tcp.disconnect()
        except Exception:
            pass
        try:
            if self._voice:
                self._voice.stop_interrupt_detector()
                self._voice.stop_speaking()
        except Exception:
            pass
        try:
            self._tray.stop()
        except Exception:
            pass


def _monotonic():
    import time
    return time.monotonic()


def _sleep(sec):
    import time
    time.sleep(sec)


if __name__ == "__main__":
    app = EddieChatApp()
    app.start()
