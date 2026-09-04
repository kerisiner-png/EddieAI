import threading
import time


class SenseListener:
    """Фоновый слушатель чувств: микрофон + вебка.

    Не блокирует основной цикл. Микрофон транскрибируется
    локальным Vosk (бесплатно), ответ уходит через сервер.
    Вебка периодически снимает кадр и описывает облачной
    vision-моделью (лимит вызовов в ScreenPerceiver).
    """

    def __init__(
        self,
        agent=None,
        server=None,
        screen_perceiver=None,
        check_interval=1.0,
        webcam_interval=600.0,
    ):
        self._agent = agent
        self._server = server
        self._screen = screen_perceiver
        self._check_interval = check_interval
        self._webcam_interval = webcam_interval
        self._stop = threading.Event()
        self._threads = []

    def start(self):
        if self._threads:
            return
        mic_thread = threading.Thread(
            target=self._mic_loop,
            name="EddieAI-Mic",
            daemon=True,
        )
        cam_thread = threading.Thread(
            target=self._cam_loop,
            name="EddieAI-Cam",
            daemon=True,
        )
        self._threads = [mic_thread, cam_thread]
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()

    def _mic_loop(self):
        while not self._stop.is_set():
            try:
                self._mic_pass()
            except Exception:
                pass
            self._stop.wait(
                timeout=self._check_interval
            )

    def _mic_pass(self):
        if self._agent is None:
            return
        try:
            from voice_repl import (
                record_until_silence,
                transcribe,
            )
            import numpy as np

            pcm = record_until_silence()
            if pcm is None or len(pcm) == 0:
                return
            rms = float(
                np.sqrt((pcm ** 2).mean())
            )
            if rms < 0.02:
                return
            text = transcribe(pcm)
            if not text or not text.strip():
                return
            cleaned = text.strip()
            if len(cleaned) < 3:
                return
            if len(cleaned.split()) < 2:
                return
            self._handle_spoken(cleaned)
        except Exception:
            return

    def _handle_spoken(self, text):
        try:
            if self._agent is not None:
                answer = self._agent.respond(text)
            else:
                answer = ""
            if (
                self._server is not None
                and answer
            ):
                self._server.broadcast({
                    "type": "agent_initiative",
                    "text": (
                        f"Ты говорил(а): «{text}» — "
                        f"{answer}"
                    ),
                })
        except Exception:
            pass

    def _cam_loop(self):
        while not self._stop.is_set():
            try:
                self._cam_pass()
            except Exception:
                pass
            self._stop.wait(
                timeout=self._webcam_interval
            )

    def _cam_pass(self):
        if self._screen is None:
            return
        try:
            desc = self._screen.webcam_describe()
            if not desc or not desc.strip():
                return
            memory = getattr(
                self._agent, "memory", None
            )
            if memory is None:
                return
            from memory.events import Event

            memory.remember(
                Event.create(
                    content=f"Камера: {desc}",
                    event_type="SHARED_EXPERIENCE",
                    source_type="VISION",
                    source="webcam",
                )
            )
        except Exception:
            pass