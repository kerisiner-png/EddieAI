import json
import asyncio
import tempfile
import threading
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
        from vosk import KaldiRecognizer, Model

        self._model = Model(str(VOSK_MODEL_DIR))
        self._rec = KaldiRecognizer(self._model, SAMPLE_RATE)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="eddie_voice_"))
        self._stop_flag = False
        self._playback_thread = None
        self._int_det_thread = None
        self._int_det_stop = False
        self._int_det_cb = None

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
        self._rec.Reset()
        data = (np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes()
        self._rec.AcceptWaveform(data)
        result = json.loads(self._rec.FinalResult())
        return (result.get("text") or "").strip()

    def record_and_transcribe(self) -> str:
        try:
            pcm = self._record_audio()
            text = self._transcribe_pcm(pcm)
            return text
        except Exception:
            return ""

    def speak(self, text: str, mood=None):
        self._stop_flag = False
        self._playback_thread = threading.Thread(
            target=self._speak_worker,
            args=(text, mood),
            daemon=True,
        )
        self._playback_thread.start()

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
            sd.play(voiced.astype(np.float32), samplerate=rate)
            sd.wait()
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
            sd.play(voiced.astype(np.float32), samplerate=rate)
            sd.wait()
        except Exception:
            pass

    def stop_speaking(self):
        self._stop_flag = True
        try:
            sd.stop()
        except Exception:
            pass

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
                        if len(text.split()) >= INTERRUPT_MIN_WORDS:
                            self._fire_interrupt()
                            break
                        silent = 0.0
                        continue
                    partial = json.loads(rec.PartialResult())
                    ptext = (partial.get("partial") or "").strip()
                    if ptext:
                        silent = 0.0
                        if len(ptext.split()) >= INTERRUPT_MIN_WORDS:
                            self._fire_interrupt()
                            break
                    else:
                        silent += CHUNK_SEC
                        if silent >= INTERRUPT_SILENCE_SEC:
                            rec.Reset()
        except Exception:
            pass
        finally:
            self._int_det_thread = None
            self._int_det_cb = None
            self._int_det_stop = False

    def _fire_interrupt(self):
        cb = self._int_det_cb
        self._int_det_cb = None
        if cb is not None:
            try:
                cb()
            except Exception:
                pass
