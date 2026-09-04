import threading
import time


class SenseListener:
    """Фоновый слушатель чувств: микрофон + вебка + голос.

    Микрофон транскрибируется локальным Vosk (бесплатно),
    ответ озвучивается голосом (Piper TTS, локально) и
    дублируется в мессенджер (редкий канал). Вебка
    периодически снимает кадр и описывает облачной
    vision-моделью (лимит вызовов в ScreenPerceiver).
    Инициатива: сам заговаривает, если тишина дольше
    initiative_interval.
    """

    def __init__(
        self,
        agent=None,
        server=None,
        screen_perceiver=None,
        check_interval=1.0,
        webcam_interval=600.0,
        initiative_interval=1800.0,
    ):
        self._agent = agent
        self._server = server
        self._screen = screen_perceiver
        self._check_interval = check_interval
        self._webcam_interval = webcam_interval
        self._initiative_interval = initiative_interval
        self._stop = threading.Event()
        self._threads = []
        self._voice = None
        self._last_spoken_at = time.time()

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
        init_thread = threading.Thread(
            target=self._initiative_loop,
            name="EddieAI-Initiative",
            daemon=True,
        )
        self._threads = [
            mic_thread,
            cam_thread,
            init_thread,
        ]
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()

    # -------------------------------------------------
    # Голос (Piper TTS, локально, без Whisper)
    # -------------------------------------------------

    def _get_voice(self):
        if self._voice is None:
            try:
                from communication.voice_io import (
                    VoiceIO,
                )

                self._voice = VoiceIO.__new__(
                    VoiceIO
                )
                self._voice._stop_flag = False
                self._voice._playback_thread = None
                self._voice._temp_dir = None
            except Exception:
                self._voice = None
        return self._voice

    def _speak(self, text):
        if not text or not text.strip():
            return
        try:
            import numpy as np
            import sounddevice as sd

            voice = self._get_voice()
            if voice is None:
                return
            pcm, rate = voice._synth_piper(text)
            pcm = voice._boyify(pcm, rate, None)
            sd.play(pcm, samplerate=rate)
        except Exception:
            return

    # -------------------------------------------------
    # Микрофон
    # -------------------------------------------------

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
            self._last_spoken_at = time.time()
            self._handle_spoken(cleaned)
        except Exception:
            return

    def _handle_spoken(self, text):
        try:
            answer = ""
            if self._agent is not None:
                try:
                    conversation = self._recent_conversation()
                    answer = (
                        self._agent.respond_call_fast(
                            conversation,
                            text,
                        )
                    )
                except Exception:
                    answer = self._agent.respond(text)
            self._speak(answer or "")
        except Exception:
            pass

    def _recent_conversation(self):
        try:
            server = self._server
            if server is None:
                return ""
            history = getattr(
                server, "history", None
            )
            if history is None:
                return ""
            items = history.chat_recent(6)
            lines = []
            for item in items:
                sender = item.get("sender", "?")
                label = (
                    "Эдди"
                    if sender == "Eddie"
                    else "EddieAI"
                )
                lines.append(
                    f"{label}: {item.get('text', '')}"
                )
            return "\n".join(lines)
        except Exception:
            return ""

    # -------------------------------------------------
    # Вебка
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Инициатива: сам заговаривает
    # -------------------------------------------------

    def _initiative_loop(self):
        while not self._stop.is_set():
            try:
                self._initiative_pass()
            except Exception:
                pass
            self._stop.wait(
                timeout=min(
                    self._initiative_interval, 60.0
                )
            )

    def _initiative_pass(self):
        if self._agent is None:
            return
        if self._initiative_interval <= 0:
            return
        now = time.time()
        if now - self._last_spoken_at < self._initiative_interval:
            return
        try:
            from core.life_cycle import LifeCycle

            life = getattr(
                self._agent, "life_cycle", None
            )
            if life is not None and life.is_asleep():
                self._last_spoken_at = now
                return
        except Exception:
            pass

        try:
            from identity.shared_activity_manager import (
                SharedActivityManager,
            )

            manager = SharedActivityManager(
                self_state=self._agent.self_state
            )
            suggestion = manager.suggest_activity(
                affective_state=getattr(
                    self._agent,
                    "affective_state",
                    None,
                ),
                interests=self._agent.self_state.get(
                    "interests", []
                ),
            )
            if suggestion:
                self._last_spoken_at = now
                act_type = suggestion.get(
                    "activity_type", ""
                )
                labels = {
                    "movie": "посмотреть фильм",
                    "music": "послушать музыку",
                    "game": "поиграть вместе",
                    "coding": "поработать над кодом",
                    "reading": "почитать вместе",
                    "conversation": "поболтать",
                }
                label = labels.get(
                    act_type, act_type
                )
                text = (
                    f"Эдди, хочешь {label}? "
                    "Мне кажется, это было бы приятно."
                )
                self._speak(text)
        except Exception:
            pass