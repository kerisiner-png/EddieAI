"""Слухи EddieAI: системный звук ПК → STT → память.

Основной путь — WASAPI-loopback основного выходного устройства
(pyaudiowpatch): слышим ровно то, что играет в наушниках/колонках —
фильмы, видео, игры. Запасной путь — кабельные входы (Voicemeeter
Out, Stereo Mix) через sounddevice. Речь распознаёт локальный Vosk,
реплики складываются в память как WORLD_SNAPSHOT (source=pc_audio).
"""
import json
import queue
import threading
import time
from pathlib import Path

import numpy as np

MIN_WORDS = 4
STORE_COOLDOWN_SEC = 45.0
SILENCE_RMS = 0.004
TARGET_RATE = 16000
VOSK_MODEL_DIR = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "vosk"
    / "vosk-model-small-ru-0.22"
)
CANDIDATE_DEVICE_NAMES = (
    "voicemeeter out",
    "stereo mix",
    "what u hear",
)


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
            f.write(f"[{stamp}] [pc-audio] {msg}\n")
    except Exception:
        pass


def text_worth_storing(
    text,
    min_words=MIN_WORDS,
):
    words = (text or "").strip().split()
    return len(words) >= min_words


def should_store(
    now,
    last_ts,
    cooldown=STORE_COOLDOWN_SEC,
):
    return now - last_ts >= cooldown


def rms_level(chunk) -> float:
    if chunk is None or len(chunk) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(chunk))))


def pick_device_index(
    devices,
    candidates=CANDIDATE_DEVICE_NAMES,
):
    for needle in candidates:
        for idx, dev in enumerate(devices):
            if (
                dev.get("max_input_channels", 0)
                > 0
                and needle
                in str(
                    dev.get("name", "")
                ).lower()
            ):
                return idx
    return None


def pick_loopback_device(
    devices,
    default_output_name,
):
    base = str(default_output_name or "").strip()
    if not base:
        return None

    for idx, dev in enumerate(devices):
        if not dev.get("isLoopbackDevice"):
            continue
        if str(dev.get("name", "")).startswith(
            base
        ):
            return idx

    prefix = base.split(" (")[0][:20]

    for idx, dev in enumerate(devices):
        if dev.get("isLoopbackDevice") and str(
            dev.get("name", "")
        ).startswith(prefix):
            return idx

    return None


class PcAudioListener:
    def __init__(
        self,
        agent=None,
        min_words=MIN_WORDS,
        cooldown=STORE_COOLDOWN_SEC,
    ):
        self._agent = agent
        self._min_words = min_words
        self._cooldown = cooldown
        self._last_store_ts = 0.0
        self.last_audio_ts = 0.0
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._recognizer = None
        self._channels = 1
        self._decimate = 1

    def start(self):
        self._thread = threading.Thread(
            target=self._loop,
            name="EddieAI-PcAudio",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _remember(self, text):
        memory = getattr(
            self._agent, "memory", None
        )
        if memory is None:
            return
        try:
            from memory.events import Event

            memory.remember(
                Event.create(
                    content=(
                        "Слышно с компьютера: "
                        f"{text}"
                    ),
                    event_type="WORLD_SNAPSHOT",
                    source_type="AUDIO",
                    source="pc_audio",
                )
            )
        except Exception:
            pass

    def _setup_recognizer(self):
        from vosk import Model, KaldiRecognizer

        model = Model(str(VOSK_MODEL_DIR))
        self._recognizer = KaldiRecognizer(
            model, TARGET_RATE
        )

    def _open_loopback(self) -> bool:
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            _log(
                "pyaudiowpatch не установлен — "
                "fallback на кабельные входы"
            )
            return False

        pa = None

        try:
            pa = pyaudio.PyAudio()
            wasapi = (
                pa.get_host_api_info_by_type(
                    pyaudio.paWASAPI
                )
            )
            default_out = (
                pa.get_device_info_by_index(
                    wasapi[
                        "defaultOutputDevice"
                    ]
                )
            )
            devices = [
                pa.get_device_info_by_index(i)
                for i in range(
                    pa.get_device_count()
                )
            ]
            idx = pick_loopback_device(
                devices,
                default_out.get("name", ""),
            )
            if idx is None:
                _log(
                    "loopback основного выхода "
                    "не найден"
                )
                pa.terminate()
                return False

            info = devices[idx]
            rate = int(
                info.get("defaultSampleRate", 0)
                or 48000
            )
            channels = int(
                info.get("maxInputChannels", 2)
                or 2
            )
            self._channels = channels
            self._decimate = max(
                1, rate // TARGET_RATE
            )
            self._setup_recognizer()

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=idx,
                frames_per_buffer=4000,
                stream_callback=(
                    self._pa_callback
                ),
            )
            stream.start_stream()

            _log(
                f"слушаю системный звук "
                f"[loopback]: "
                f"{info.get('name', '')[:50]}, "
                f"{rate} Hz, {channels}ch"
            )
            return True
        except Exception as exc:
            _log(
                f"loopback не поднялся: "
                f"{type(exc).__name__}: {exc}"
            )
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
            return False

    def _pa_callback(
        self, in_data, frame_count, time_info, flags
    ):
        self._queue.put(bytes(in_data))
        return None, 0

    def _open_fallback(self) -> bool:
        import sounddevice as sd

        devices = sd.query_devices()
        idx = pick_device_index(devices)
        if idx is None:
            _log(
                "кандидаты системного звука не "
                "найдены — слухи ПК выключены"
            )
            return False

        dev = devices[idx]
        rate = int(
            dev.get("default_samplerate", 48000)
        )
        try:
            stream = sd.RawInputStream(
                samplerate=rate,
                blocksize=4000,
                device=idx,
                channels=1,
                dtype="int16",
                callback=self._sd_callback,
            )
        except Exception as exc:
            _log(
                f"устройство {idx} не открылось: "
                f"{exc}"
            )
            return False

        self._channels = 1
        self._decimate = max(
            1, rate // TARGET_RATE
        )

        try:
            self._setup_recognizer()
        except Exception as exc:
            _log(f"vosk не поднялся: {exc}")
            return False

        _log(
            f"слушаю системный звук "
            f"[fallback]: устройство {idx} "
            f"({dev.get('name', '')[:40]}), "
            f"{rate} Hz"
        )
        stream.start()
        return True

    def _sd_callback(self, indata, frames, ct, status):
        self._queue.put(bytes(indata))

    def _loop(self):
        if not self._open_loopback():
            if not self._open_fallback():
                return
        self._consume()

    def _consume(self):
        last_level_log = 0.0

        while not self._stop.is_set():
            try:
                raw = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            samples = np.frombuffer(
                raw, dtype=np.int16
            ).astype(np.float32) / 32768.0

            if self._channels > 1:
                samples = samples.reshape(
                    -1, self._channels
                ).mean(axis=1)

            now = time.time()
            level = rms_level(samples)

            if level > SILENCE_RMS:
                self.last_audio_ts = now

            if now - last_level_log > 60.0:
                _log(f"level rms={level:.4f}")
                last_level_log = now

            if self._decimate > 1:
                samples = samples[
                    :: self._decimate
                ]

            pcm = (
                samples * 32767.0
            ).astype(np.int16).tobytes()

            if self._recognizer is None:
                continue

            if self._recognizer.AcceptWaveform(
                pcm
            ):
                try:
                    result = json.loads(
                        self._recognizer.Result()
                    )
                except Exception:
                    continue
                text = str(
                    result.get("text", "")
                ).strip()
                if not text_worth_storing(
                    text, self._min_words
                ):
                    continue
                if not should_store(
                    now,
                    self._last_store_ts,
                    self._cooldown,
                ):
                    continue
                self._last_store_ts = now
                _log(f"услышал: {text[:80]!r}")
                self._remember(text)
