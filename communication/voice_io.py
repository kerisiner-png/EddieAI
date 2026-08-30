import json
import asyncio
import tempfile
import threading
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
import edge_tts
import av
import parselmouth
from scipy.signal import (
    butter,
    sosfilt,
    sosfilt_zi,
    lfilter,
    resample_poly,
)


VOSK_MODEL_DIR = Path(r"C:\EddieAI\models\vosk\vosk-model-small-ru-0.22")
WHISPER_MODEL = "small"
WHISPER_CACHE = Path(r"C:\EddieAI\models\whisper")
VOICE = "ru-RU-DmitryNeural"
PIPER_MODEL_DIR = Path(
    r"C:\EddieAI\models\piper\ru_RU-dmitri-medium.onnx"
)
PIPER_VOICE_PATH = Path(
    r"C:\EddieAI\models\piper\ru_RU-irina-medium.onnx"
)
TEEN_PITCH_HZ = 250.0
SAMPLE_RATE = 16000
CHUNK_SEC = 0.1
SILENCE_LIMIT_SEC = 1.5
MAX_RECORD_SEC = 15.0
MIN_SPEECH_SEC = 0.7
INTERRUPT_MIN_WORDS = 2
INTERRUPT_SILENCE_SEC = 0.9

_VOICE_DBG_LOG = Path(
    r"C:\Users\keris\AppData\Local\Temp\opencode\voice_dbg.log"
)


def _dbg(msg):
    try:
        import datetime

        with open(
            _VOICE_DBG_LOG,
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                f"{msg}\n"
            )
    except Exception:
        pass


def flatten_pitch(sound, keep):
    p0 = sound.to_pitch(None, 100, 500).selected_array["frequency"]
    p0 = p0[p0 > 0]
    med = float(np.median(p0))
    man = parselmouth.praat.call(
        sound, "To Manipulation", 0.01, 100, 500
    )
    tier = parselmouth.praat.call(man, "Extract pitch tier")
    k = round(1.0 - keep, 3)
    parselmouth.praat.call(
        tier,
        "Formula",
        f"self + ({med:.2f} - self) * {k}",
    )
    parselmouth.praat.call([man, tier], "Replace pitch tier")
    syn = parselmouth.praat.call(
        man, "Get resynthesis (overlap-add)"
    )
    return syn


def brighten(pcm, rate, freq_hz, gain_db):
    sos = butter(2, freq_hz, "highpass", fs=rate, output="sos")
    zi = sosfilt_zi(sos) * pcm[0]
    band, _ = sosfilt(sos, pcm.astype(np.float64), zi=zi)
    boosted = pcm + (gain_db / 10.0) * band
    return boosted


def saturate(pcm, drive):
    return np.tanh(pcm * drive) / np.tanh(drive)


def equalize(pcm, rate):
    b, a = butter(2, [1000, 5000], btype="bandpass", fs=rate)
    return lfilter(b, a, pcm)


def emotions_to_mood(emotions):
    """
    Связать эмоциональное состояние EddieAI с параметрами голоса
    (урок втуберов №2: эмоция должна звучать).

    Принимает dict эмоций (affective_state.snapshot()["emotions"]),
    возвращает параметры: target_pitch_hz, tempo_ratio,
    brighten_db, drive. Все значения в безопасных пределах.
    """
    if not emotions:
        return {
            "target_pitch_hz": 160.0,
            "tempo_ratio": 1.0,
            "brighten_db": 18.0,
            "drive": 2.6,
        }

    def _get(name):
        return float(emotions.get(name, 0.0) or 0.0)

    joy = _get("joy")
    sadness = _get("sadness")
    fear = _get("fear")
    anger = _get("anger")
    surprise = _get("surprise")
    frustration = _get("frustration")
    total = sum(
        abs(emotions.get(k, 0.0) or 0.0)
        for k in emotions
    ) or 1.0

    positive = joy + surprise
    negative = sadness + fear + anger + frustration

    valence = (positive - negative) / total

    arousal = (
        _get("surprise")
        + _get("fear")
        + _get("anger")
        + joy
    ) / total

    joy_soft = max(0.0, min(1.0, joy / 1.0))

    base_pitch = 160.0
    pitch = base_pitch + valence * 26.0

    pitch = max(120.0, min(205.0, pitch))

    tempo = 1.0 + arousal * 0.30
    tempo = max(0.82, min(1.28, tempo))

    brighten_db = 18.0 + valence * 6.0
    brighten_db = max(12.0, min(26.0, brighten_db))

    drive = 2.6 - joy_soft * 0.6
    drive = max(1.4, min(3.2, drive))

    return {
        "target_pitch_hz": float(pitch),
        "tempo_ratio": float(tempo),
        "brighten_db": float(brighten_db),
        "drive": float(drive),
    }


def mood_from_agent(agent):
    """
    Извлечь текущее эмоциональное состояние агента и
    преобразовать в аудиопараметры голоса.
    """
    try:
        affective = getattr(
            agent, "affective_state", None
        )
        if affective is None:
            return None
        snapshot = affective.snapshot()
        emotions = snapshot.get("emotions")
        if not emotions:
            return None
        return emotions_to_mood(emotions)
    except Exception:
        return None


class VoiceIO:
    _piper_voice = None
    _pip_lock = threading.Lock()

    def __init__(self):
        from faster_whisper import WhisperModel
        from vosk import KaldiRecognizer, Model

        self._whisper = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            cpu_threads=2,
            download_root=str(WHISPER_CACHE),
        )
        self._model = Model(str(VOSK_MODEL_DIR))
        self._rec = KaldiRecognizer(self._model, SAMPLE_RATE)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="eddie_voice_"))
        self._stop_flag = False
        self._playback_thread = None
        self._int_det_thread = None
        self._int_det_stop = False
        self._int_det_cb = None
        self._int_det_end_cb = None
        self._stream_stop = False
        self._stream_thread = None
        self._stream_on_phrase = None
        self._stream_on_speech_start = None
        self._stream_stop_check = None

    def _ensure_piper(self):
        with VoiceIO._pip_lock:
            if VoiceIO._piper_voice is None:
                from piper import PiperVoice

                VoiceIO._piper_voice = PiperVoice.load(
                    str(PIPER_MODEL_DIR)
                )
        return VoiceIO._piper_voice

    def _synth_piper(self, text):
        piper = self._ensure_piper()
        rate = piper.config.sample_rate
        chunks = []
        for chunk in piper.synthesize(text):
            chunks.append(chunk.audio_float_array)
        pcm = np.concatenate(chunks)
        return pcm.astype(np.float32), rate

    def _calibrate_noise(self, stream, seconds=0.6):
        levels = []
        blocks = int(seconds / CHUNK_SEC)
        for _ in range(blocks):
            data, _ = stream.read(int(SAMPLE_RATE * CHUNK_SEC))
            levels.append(float(np.sqrt((data ** 2).mean())))
        return max(levels)

    def _record_audio(self):
        chunks = []
        silent = 0.0
        speech_seen = 0.0
        duration = 0.0
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=int(SAMPLE_RATE * CHUNK_SEC),
        ) as stream:
            noise = self._calibrate_noise(stream)
            threshold = noise * 3.0 + 0.005
            while True:
                data, _ = stream.read(int(SAMPLE_RATE * CHUNK_SEC))
                chunks.append(data.copy())
                duration += CHUNK_SEC
                rms = float(np.sqrt((data ** 2).mean()))
                if rms > threshold:
                    speech_seen += CHUNK_SEC
                    silent = 0.0
                else:
                    silent += CHUNK_SEC
                if duration >= MAX_RECORD_SEC:
                    break
                if speech_seen >= MIN_SPEECH_SEC and silent >= SILENCE_LIMIT_SEC:
                    break
        return np.concatenate(chunks).reshape(-1)

    def _transcribe_pcm(self, pcm):
        segments, _info = self._whisper.transcribe(
            pcm,
            language="ru",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = " ".join(
            seg.text.strip() for seg in segments
        ).strip()
        return text

    def record_and_transcribe(self) -> str:
        try:
            pcm = self._record_audio()
            text = self._transcribe_pcm(pcm)
            return text
        except Exception:
            return ""

    def start_stream_listen(
        self,
        on_phrase,
        on_speech_start=None,
        stop_check=None,
    ):
        """
        Непрерывное прослушивание микрофона на весь звонок
        (полный duplex + partial-перебивание).

        Микрофонный поток никогда не блокируется на
        транскрипции (начало речи не теряется, кольцевой
        буфер). Отдельный partial-поток:
        - каждые ~1.6с речи транскрибирует накопленное;
          если слов >= 5 — фраза считается готовой и
          уходит on_phrase немедленно (не дожидаясь тишины);
        - транскрибирует завершённые фразы (по тишине)
          из очереди.
        on_speech_start вызывается в момент начала речи
        (немедленное прерывание EddieAI).
        """
        if self._stream_thread is not None:
            return
        self._stream_stop = False
        self._stream_on_phrase = on_phrase
        self._stream_on_speech_start = on_speech_start
        self._stream_stop_check = stop_check
        self._stream_lock = threading.Lock()
        self._stream_pending = []
        self._stream_recording = False
        self._stream_speech_sec = 0.0
        self._stream_silent_sec = 0.0
        self._stream_final_queue = deque()
        self._stream_last_partial_at = 0.0
        self._stream_last_emitted = ""
        self._stream_thread = threading.Thread(
            target=self._stream_listen_loop,
            daemon=True,
        )
        self._stream_thread.start()
        self._stream_partial_thread = (
            threading.Thread(
                target=self._stream_partial_loop,
                daemon=True,
            )
        )
        self._stream_partial_thread.start()

    def stop_stream_listen(self):
        self._stream_stop = True

    def _stream_listen_loop(self):
        import time

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=int(
                    SAMPLE_RATE * CHUNK_SEC
                ),
            ) as stream:
                noise = self._calibrate_noise(stream)
                threshold = noise * 3.0 + 0.005
                _dbg(
                    f"cal noise={noise:.4f} "
                    f"thresh={threshold:.4f}"
                )
                ring = deque(
                    maxlen=int(1.2 / CHUNK_SEC)
                )
                stop_check = (
                    self._stream_stop_check
                )
                while (
                    not self._stream_stop
                    and (
                        stop_check is None
                        or not stop_check()
                    )
                ):
                    data, _ = stream.read(
                        int(SAMPLE_RATE * CHUNK_SEC)
                    )
                    ring.append(data.copy())
                    rms = float(
                        np.sqrt((data ** 2).mean())
                    )
                    with self._stream_lock:
                        if rms > threshold:
                            if (
                                not self._stream_recording
                            ):
                                self._stream_recording = True
                                self._stream_pending = (
                                    list(ring)
                                )
                                self._stream_speech_sec = 0.0
                                self._stream_silent_sec = 0.0
                                _dbg(
                                    f"rec_start rms={rms:.4f} "
                                    f"thresh={threshold:.4f}"
                                )
                                if (
                                    self._stream_on_speech_start
                                    is not None
                                ):
                                    try:
                                        self._stream_on_speech_start()
                                    except Exception:
                                        pass
                            self._stream_pending.append(
                                data.copy()
                            )
                            self._stream_speech_sec += (
                                CHUNK_SEC
                            )
                            self._stream_silent_sec = 0.0
                        else:
                            if self._stream_recording:
                                self._stream_pending.append(
                                    data.copy()
                                )
                                self._stream_silent_sec += (
                                    CHUNK_SEC
                                )
                                if (
                                    self._stream_speech_sec
                                    >= MIN_SPEECH_SEC
                                    and self._stream_silent_sec
                                    >= SILENCE_LIMIT_SEC
                                ):
                                    self._stream_final_queue.append(
                                        list(
                                            self._stream_pending
                                        )
                                    )
                                    _dbg(
                                        "final enqueued "
                                        f"len={len(self._stream_pending)}"
                                    )
                                    self._stream_recording = False
                                    self._stream_pending = []
                                    self._stream_speech_sec = 0.0
                                    self._stream_silent_sec = 0.0
                        if (
                            self._stream_recording
                            and len(
                                self._stream_pending
                            )
                            * CHUNK_SEC
                            >= MAX_RECORD_SEC
                        ):
                            self._stream_final_queue.append(
                                list(
                                    self._stream_pending
                                )
                            )
                            _dbg(
                                "final maxlen enqueued "
                                f"len={len(self._stream_pending)}"
                            )
                            self._stream_recording = False
                            self._stream_pending = []
                            self._stream_speech_sec = 0.0
                            self._stream_silent_sec = 0.0
        except Exception as exc:
            _dbg(
                f"listen except {type(exc).__name__}: {exc}"
            )
        finally:
            self._stream_thread = None

    def _stream_partial_loop(self):
        import time

        stop_check = self._stream_stop_check
        while (
            not self._stream_stop
            and (
                stop_check is None
                or not stop_check()
            )
        ):
            if self._stream_final_queue:
                with self._stream_lock:
                    buf = (
                        self._stream_final_queue.popleft()
                        if self._stream_final_queue
                        else None
                    )
                if buf is not None:
                    self._emit_phrase(buf)
                    continue

            now = time.monotonic()
            take = False
            with self._stream_lock:
                if (
                    self._stream_recording
                    and self._stream_speech_sec >= 3.0
                    and (
                        now
                        - self._stream_last_partial_at
                        >= 2.2
                    )
                ):
                    take = True
            if take:
                with self._stream_lock:
                    self._stream_last_partial_at = now
                    buf = list(self._stream_pending)
                if buf:
                    try:
                        pcm = np.concatenate(
                            buf
                        ).reshape(-1)
                        text = self._transcribe_pcm(
                            pcm
                        )
                    except Exception:
                        text = ""
                    if len(text.split()) >= 5:
                        _dbg(
                            f"partial emit words={len(text.split())} "
                            f"text={text[:60]!r}"
                        )
                        self._emit_text(text)
                        with self._stream_lock:
                            self._stream_recording = False
                            self._stream_pending = []
                            self._stream_speech_sec = 0.0
                            self._stream_silent_sec = 0.0
                    else:
                        _dbg(
                            f"partial low words={len(text.split())} "
                            f"text={text[:60]!r}"
                        )
            time.sleep(0.2)

    def _emit_phrase(self, chunks):
        try:
            pcm = np.concatenate(
                chunks
            ).reshape(-1)
            text = self._transcribe_pcm(pcm)
        except Exception:
            text = ""
        self._emit_text(text)

    def _emit_text(self, text):
        if not text:
            _dbg("emit EMPTY")
            return
        if text == self._stream_last_emitted:
            _dbg(f"emit skip dup: {text[:40]!r}")
            return
        self._stream_last_emitted = text
        _dbg(f"emit: {text[:80]!r}")
        cb = self._stream_on_phrase
        if cb is not None:
            try:
                cb(text)
            except Exception:
                pass

    def speak(self, text: str, mood=None):
        self._stop_flag = False
        self._playback_thread = threading.Thread(
            target=self._speak_worker,
            args=(text, mood),
            daemon=True,
        )
        self._playback_thread.start()

    def play_ringtone(self):
        if self._stop_flag:
            return
        self._playback_thread = threading.Thread(
            target=self._ringtone_worker,
            daemon=True,
        )
        self._playback_thread.start()

    def _ringtone_worker(self):
        try:
            rate = SAMPLE_RATE
            tone_dur = 0.35
            gap_dur = 0.25
            rings = 2
            freq_a = 440.0
            freq_b = 480.0
            t_tone = np.linspace(
                0, tone_dur, int(rate * tone_dur),
                endpoint=False,
            )
            tone = (
                0.15 * np.sin(2 * np.pi * freq_a * t_tone)
                + 0.15 * np.sin(2 * np.pi * freq_b * t_tone)
            )
            gap = np.zeros(int(rate * gap_dur))
            ring = np.concatenate([tone, gap])
            signal = np.tile(ring, rings)
            sd.play(
                signal.astype(np.float32),
                samplerate=rate,
            )
            sd.wait()
        except Exception:
            pass

    def _boyify(self, pcm: np.ndarray, rate: int, mood=None):
        if not mood:
            mood = {
                "target_pitch_hz": 160.0,
                "tempo_ratio": 1.0,
                "brighten_db": 18.0,
                "drive": 2.6,
            }

        target_pitch = float(
            mood.get("target_pitch_hz", 160.0)
        )
        tempo = float(
            mood.get("tempo_ratio", 1.0)
        )
        brighten_db = float(
            mood.get("brighten_db", 18.0)
        )
        drive = float(
            mood.get("drive", 2.6)
        )

        snd = parselmouth.Sound(pcm.astype(np.float64), rate)
        snd = flatten_pitch(snd, 0.60)
        proc_pcm = snd.values[0]

        speed_out = int(round(100.0 / tempo))
        speed_out = max(78, min(130, speed_out))

        sped = resample_poly(
            proc_pcm,
            100,
            speed_out,
            window=("kaiser", 14),
        )
        out_pcm = brighten(sped, rate, 6500, brighten_db)
        out_pcm = saturate(out_pcm, drive)
        out_pcm = equalize(out_pcm, rate)
        peak = np.abs(out_pcm).max()
        if peak > 0.99:
            out_pcm = out_pcm / peak * 0.99

        snd2 = parselmouth.Sound(out_pcm, rate)
        man = parselmouth.praat.call(
            snd2, "To Manipulation", 0.01, 75, 500
        )
        tier = parselmouth.praat.call(
            man, "Extract pitch tier"
        )
        base_f0 = parselmouth.praat.call(
            snd2.to_pitch(None, 100, 500),
            "Get mean...",
            0,
            0,
            "Hertz",
        )
        if base_f0 and base_f0 > 0:
            parselmouth.praat.call(
                tier,
                "Multiply frequencies",
                0,
                snd2.duration,
                target_pitch / base_f0,
            )
            parselmouth.praat.call(
                [man, tier], "Replace pitch tier"
            )
            syn = parselmouth.praat.call(
                man, "Get resynthesis (overlap-add)"
            )
            return syn.values[0]
        return out_pcm

    def _play_pcm(self, pcm, rate):
        data = pcm.astype(np.float32)
        blocksize = max(1, int(rate / 20))
        with sd.OutputStream(
            samplerate=rate,
            channels=1,
            dtype="float32",
        ) as out:
            i = 0
            while i < len(data):
                if self._stop_flag:
                    break
                out.write(data[i:i + blocksize])
                i += blocksize

    def _speak_worker(self, text: str, mood=None):
        try:
            pcm, rate = self._synth_piper(text)
            if self._stop_flag:
                return

            if mood is None:
                mood = {}

            base_pitch = float(
                mood.get("target_pitch_hz", TEEN_PITCH_HZ)
            )
            voiced = self._boyify(
                pcm,
                rate,
                dict(mood, target_pitch_hz=base_pitch),
            )
            self._play_pcm(voiced, rate)
        except Exception:
            self._speak_worker_fallback(text, mood)

    def _speak_worker_fallback(self, text: str, mood=None):
        try:
            mp3_path = self._temp_dir / "reply.mp3"

            async def synth():
                tts = edge_tts.Communicate(text, VOICE, rate="+0%")
                await tts.save(str(mp3_path))

            asyncio.run(synth())

            if self._stop_flag:
                return

            container = av.open(str(mp3_path))
            stream = container.streams.audio[0]
            rate = stream.codec_context.sample_rate
            frames = []
            for frame in container.decode(stream):
                if self._stop_flag:
                    container.close()
                    return
                arr = frame.to_ndarray()
                arr = arr.astype(np.float32)
                if np.abs(arr).max() > 1.0:
                    arr = arr / 32768.0
                if arr.ndim > 1:
                    arr = arr.mean(axis=0)
                frames.append(arr)
            container.close()

            pcm = np.concatenate(frames)
            voiced = self._boyify(pcm, rate, mood)
            self._play_pcm(voiced, rate)
        except Exception:
            pass

    def stop_speaking(self):
        self._stop_flag = True

    def is_speaking(self):
        t = self._playback_thread
        return t is not None and t.is_alive()

    def start_interrupt_detector(self, callback):
        """
        Фоновая детекция речи собеседника во время озвучки
        (режим наушников: микрофон ловит только Эдди).

        Стримит микрофон через Vosk PartialResult; при первой
        осмысленной фразе (>= INTERRUPT_MIN_WORDS слов) вызывает
        callback() один раз и самостоятельно останавливается.
        Вне звонка активной речи нет, поэтому не мешает.
        """
        if self._int_det_thread is not None:
            return
        self._int_det_stop = False
        self._int_det_cb = callback
        self._int_det_thread = threading.Thread(
            target=self._interrupt_detector_loop,
            daemon=True,
        )
        self._int_det_thread.start()

    def on_interrupt_detector_end(self, callback):
        """
        Устанавливает callback на ОКОНЧАНИЕ речи собеседника
        (пауза >= INTERRUPT_SILENCE_SEC после установленной речи).

        Вызывается до/после start_interrupt_detector; callback
        выполняется в том же потоке детектора один раз после
        паузы. Если не задан — детектор умирает сразу после
        перехвата (поведение этапа 2).
        """
        self._int_det_end_cb = callback

    def stop_interrupt_detector(self):
        self._int_det_stop = True

    def _interrupt_detector_loop(self):
        try:
            from vosk import KaldiRecognizer

            rec = KaldiRecognizer(self._model, SAMPLE_RATE)
            rec.SetWords(True)
            rec.SetPartialWords(True)
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=int(SAMPLE_RATE * CHUNK_SEC),
            ) as stream:
                silent = 0.0
                speech_seen = False
                while not self._int_det_stop:
                    data, _ = stream.read(
                        int(SAMPLE_RATE * CHUNK_SEC)
                    )
                    pcm = (
                        np.clip(data, -1, 1) * 32767
                    ).astype(np.int16).tobytes()
                    if rec.AcceptWaveform(pcm):
                        result = json.loads(rec.Result())
                        text = (result.get("text") or "").strip()
                        if text:
                            speech_seen = True
                        if len(text.split()) >= INTERRUPT_MIN_WORDS:
                            self._fire_interrupt()
                            if self._int_det_end_cb is None:
                                break
                            silent = 0.0
                            continue
                        if not speech_seen:
                            silent = 0.0
                            continue
                        silent += CHUNK_SEC
                    else:
                        partial = json.loads(rec.PartialResult())
                        ptext = (
                            partial.get("partial") or ""
                        ).strip()
                        if ptext:
                            speech_seen = True
                            silent = 0.0
                            if (
                                len(ptext.split())
                                >= INTERRUPT_MIN_WORDS
                            ):
                                self._fire_interrupt()
                                if self._int_det_end_cb is None:
                                    break
                            continue
                        if not speech_seen:
                            silent += CHUNK_SEC
                            continue
                        silent += CHUNK_SEC

                    if (
                        speech_seen
                        and self._int_det_end_cb is not None
                        and silent >= INTERRUPT_SILENCE_SEC
                    ):
                        self._fire_speech_end()
                        break
        except Exception:
            pass
        finally:
            self._int_det_thread = None
            self._int_det_cb = None
            self._int_det_end_cb = None
            self._int_det_stop = False

    def _fire_interrupt(self):
        cb = self._int_det_cb
        self._int_det_cb = None
        if cb is not None:
            try:
                cb()
            except Exception:
                pass

    def _fire_speech_end(self):
        cb = self._int_det_end_cb
        self._int_det_end_cb = None
        if cb is not None:
            try:
                cb()
            except Exception:
                pass
