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
VOICE = "ru-RU-SvetlanaNeural"
SAMPLE_RATE = 16000
CHUNK_SEC = 0.1
SILENCE_LIMIT_SEC = 1.5
MAX_RECORD_SEC = 15.0
MIN_SPEECH_SEC = 0.7


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


class VoiceIO:
    def __init__(self):
        from vosk import KaldiRecognizer, Model

        self._model = Model(str(VOSK_MODEL_DIR))
        self._rec = KaldiRecognizer(self._model, SAMPLE_RATE)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="eddie_voice_"))
        self._stop_flag = False
        self._playback_thread = None

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

    def speak(self, text: str):
        self._stop_flag = False
        self._playback_thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True,
        )
        self._playback_thread.start()

    def _boyify(self, pcm: np.ndarray, rate: int):
        snd = parselmouth.Sound(pcm.astype(np.float64), rate)
        snd = flatten_pitch(snd, 0.60)
        proc_pcm = snd.values[0]

        sped = resample_poly(
            proc_pcm,
            100,
            125,
            window=("kaiser", 14),
        )
        out_pcm = brighten(sped, rate, 6500, 18.0)
        out_pcm = saturate(out_pcm, 2.6)
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
                160.0 / base_f0,
            )
            parselmouth.praat.call(
                [man, tier], "Replace pitch tier"
            )
            syn = parselmouth.praat.call(
                man, "Get resynthesis (overlap-add)"
            )
            return syn.values[0]
        return out_pcm

    def _speak_worker(self, text: str):
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
            voiced = self._boyify(pcm, rate)
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
