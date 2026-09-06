import threading
import time
from pathlib import Path


def _log(msg):
    stamp = time.strftime("%H:%M:%S")
    try:
        with open(
            Path(__file__).resolve().parent.parent
            / "logs"
            / "eddie_forever.log",
            "a",
            encoding="utf-8",
        ) as f:
            f.write(f"[{stamp}] {msg}\n")
    except Exception:
        pass


class SenseListener:
    """Фоновый слушатель чувств: микрофон + вебка + голос.

    Микрофон — непрерывный стриминг через Vosk (локально,
    не блокирует на 15с): фраза фиксируется по паузе ~1.0с,
    ответ озвучивается голосом (Piper TTS, локально).
    Мессенджер не используется для ответа (только редкий
    канал). Вебка периодически снимает кадр и описывает
    облачной vision-моделью (лимит в ScreenPerceiver).
    Инициатива: сам заговаривает при тишине дольше
    initiative_interval.
    """

    def __init__(
        self,
        agent=None,
        server=None,
        screen_perceiver=None,
        webcam_interval=600.0,
        initiative_interval=1800.0,
        max_phrase_sec=8.0,
        silence_end_sec=1.0,
    ):
        self._agent = agent
        self._server = server
        self._screen = screen_perceiver
        self._webcam_interval = webcam_interval
        self._initiative_interval = initiative_interval
        self._max_phrase_sec = max_phrase_sec
        self._silence_end_sec = silence_end_sec
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
    # Голос (Piper TTS, локально)
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
    # Микрофон: непрерывный стриминг Vosk
    # -------------------------------------------------

    def _mic_loop(self):
        while not self._stop.is_set():
            try:
                self._stream_listen()
            except Exception:
                pass
            self._stop.wait(timeout=1.0)

    def _stream_listen(self):
        import json
        import numpy as np
        import sounddevice as sd

        from voice_repl import (
            SAMPLE_RATE,
            CHUNK_SEC,
            get_vosk,
        )

        rec = get_vosk()
        rec.Reset()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=int(SAMPLE_RATE * CHUNK_SEC),
        ) as stream:
            noise = self._calibrate_noise(stream)
            threshold = noise * 3.0 + 2.0

            recording = False
            speech_sec = 0.0
            silent_sec = 0.0
            raw = bytearray()

            while not self._stop.is_set():
                data, _ = stream.read(
                    int(SAMPLE_RATE * CHUNK_SEC)
                )
                pcm = data.reshape(-1)
                rms = float(
                    np.sqrt(
                        (pcm.astype(np.float32) ** 2).mean()
                    )
                )

                if rms > threshold:
                    if not recording:
                        recording = True
                        speech_sec = 0.0
                        silent_sec = 0.0
                        raw = bytearray()
                    raw.extend(pcm.tobytes())
                    speech_sec += CHUNK_SEC
                    silent_sec = 0.0
                elif recording:
                    raw.extend(pcm.tobytes())
                    silent_sec += CHUNK_SEC
                    speech_sec += CHUNK_SEC

                    if speech_sec >= self._max_phrase_sec:
                        self._finish_phrase(rec, raw)
                        recording = False
                        raw = bytearray()
                    elif silent_sec >= self._silence_end_sec:
                        self._finish_phrase(rec, raw)
                        recording = False
                        raw = bytearray()

    def _calibrate_noise(self, stream):
        import numpy as np

        levels = []
        for _ in range(6):
            data, _ = stream.read(
                int(16000 * 0.1)
            )
            pcm = data.reshape(-1)
            levels.append(
                float(
                    np.sqrt(
                        (pcm.astype(np.float32) ** 2).mean()
                    )
                )
            )
        return max(levels) if levels else 0.0

    def _finish_phrase(self, rec, raw):
        import json

        if not raw:
            return
        try:
            rec.AcceptWaveform(bytes(raw))
            result = json.loads(
                rec.FinalResult()
            )
            text = (
                result.get("text") or ""
            ).strip()
        except Exception:
            return
        rec.Reset()
        if not text:
            return
        cleaned = text.strip()
        if len(cleaned) < 3:
            return
        if len(cleaned.split()) < 2:
            return
        self._last_spoken_at = time.time()
        if self._is_asleep():
            self._wake_up()
        self._handle_spoken(cleaned)

    def _wake_up(self):
        try:
            life = getattr(
                self._agent, "life_cycle", None
            )
            if life is not None:
                life.force_wake()
        except Exception:
            pass

    def _is_asleep(self):
        try:
            life = getattr(
                self._agent, "life_cycle", None
            )
            if life is not None and life.is_asleep():
                return True
        except Exception:
            pass
        return False

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
                except Exception as exc:
                    _log(
                        f"voice respond_call_fast "
                        f"failed: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
                    answer = self._agent.respond(text)
            if not (answer or "").strip():
                _log(
                    "voice empty answer: "
                    f"phrase={text[:80]!r}"
                )
            self._record_voice_turn(text, answer)
            self._speak(answer or "")
        except Exception as exc:
            _log(
                f"voice handle_spoken failed: "
                f"{type(exc).__name__}: {exc}"
            )

    def _record_voice_turn(self, user_text, agent_text):
        try:
            memory = getattr(
                self._agent, "memory", None
            )
            if memory is None:
                return
            from memory.events import Event

            user_text = (user_text or "").strip()
            agent_text = (agent_text or "").strip()

            if user_text:
                memory.remember(
                    Event.create(
                        content=user_text,
                        event_type="CONVERSATION",
                        source_type="VOICE",
                        source="Eddie",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

            if agent_text:
                memory.remember(
                    Event.create(
                        content=agent_text,
                        event_type="CONVERSATION",
                        source_type="VOICE",
                        source="EddieAI",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )
        except Exception:
            pass

    def _recent_conversation(self):
        try:
            memory = getattr(
                self._agent, "memory", None
            )
            if memory is not None:
                items = memory.recent_dialogue(6)
                if items:
                    return "\n".join(
                        f"{item['label']}: "
                        f"{item['text']}"
                        for item in items
                    )
        except Exception:
            pass
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