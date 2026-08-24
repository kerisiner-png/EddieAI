import sys
import time
import json
import asyncio
import traceback
import subprocess
import urllib.request
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
    resample_poly,
    lfilter,
)

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\EddieAI")
sys.path.insert(0, str(ROOT))

OLLAMA_EXE = Path(
    r"C:\Users\keris\AppData\Local\Programs\Ollama\ollama.exe"
)


def ensure_ollama(timeout_sec=40):
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags", timeout=2
        ):
            print("ollama уже работает.")
            return True
    except Exception:
        pass
    print("Поднимаю Ollama...")
    subprocess.Popen(
        [str(OLLAMA_EXE), "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:11434/api/tags", timeout=2
            ):
                print("ollama готова.")
                return True
        except Exception:
            time.sleep(1)
    print("!!! Ollama не поднялась за", timeout_sec, "сек")
    return False

TEMP_DIR = Path(r"C:\Users\keris\AppData\Local\Temp\opencode")
REPLY_MP3 = TEMP_DIR / "eddie_reply.mp3"

SAMPLE_RATE = 16000
CHUNK_SEC = 0.1
SILENCE_LIMIT_SEC = 1.5
MAX_RECORD_SEC = 15.0
MIN_SPEECH_SEC = 0.7
VOICE = "ru-RU-SvetlanaNeural"


def calibrate_noise(stream, seconds=0.6):
    levels = []
    blocks = int(seconds / CHUNK_SEC)
    for _ in range(blocks):
        data, _ = stream.read(int(SAMPLE_RATE * CHUNK_SEC))
        levels.append(float(np.sqrt((data ** 2).mean())))
    return max(levels)


def record_until_silence():
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
        noise = calibrate_noise(stream)
        threshold = noise * 3.0 + 0.005
        print(f"   слушаю... (порог {threshold:.4f})")
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


MISTRAL_KEY_PATH = Path.home() / ".eddieai_secrets" / "mistral.key"
WHISPER = {"model": None}


def get_whisper():
    if WHISPER["model"] is None:
        from faster_whisper import WhisperModel

        t0 = time.perf_counter()
        WHISPER["model"] = WhisperModel(
            "medium", device="cpu", compute_type="int8"
        )
        print(
            f"уши-резерв готовы за {time.perf_counter() - t0:.0f}с"
        )
    return WHISPER["model"]


def cloud_transcribe(audio_path):
    if not MISTRAL_KEY_PATH.exists():
        return None
    try:
        key = MISTRAL_KEY_PATH.read_text(
            encoding="utf-8"
        ).strip()
        boundary = "----eddiestt"
        file_bytes = Path(audio_path).read_bytes()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"voxtral-mini-latest\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; '
            f'filename="audio.wav"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8")
        body += (
            file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": (
                    f"multipart/form-data; boundary={boundary}"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("text") or "").strip()
        return text or None
    except Exception:
        return None


def transcribe(pcm):
    tmp_wav = TEMP_DIR / "mic_input.wav"
    import wave

    with wave.open(str(tmp_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes())

    cloud_text = cloud_transcribe(tmp_wav)
    if cloud_text:
        return cloud_text

    model = get_whisper()
    segments, _info = model.transcribe(
        str(tmp_wav),
        language="ru",
        beam_size=1,
        vad_filter=True,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    return text


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


def speak(text):
    async def synth():
        tts = edge_tts.Communicate(text, VOICE, rate="+0%")
        await tts.save(str(REPLY_MP3))

    asyncio.run(synth())
    container = av.open(str(REPLY_MP3))
    stream = container.streams.audio[0]
    rate = stream.codec_context.sample_rate
    frames = []
    for frame in container.decode(stream):
        arr = frame.to_ndarray()
        arr = arr.astype(np.float32)
        if np.abs(arr).max() > 1.0:
            arr = arr / 32768.0
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        frames.append(arr)
    container.close()
    pcm = np.concatenate(frames)

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
    tier = parselmouth.praat.call(man, "Extract pitch tier")
    base_f0 = parselmouth.praat.call(
        snd2.to_pitch(None, 100, 500), "Get mean...", 0, 0, "Hertz"
    )
    parselmouth.praat.call(
        tier,
        "Multiply frequencies",
        0,
        snd2.duration,
        160.0 / base_f0,
    )
    parselmouth.praat.call([man, tier], "Replace pitch tier")
    syn = parselmouth.praat.call(
        man, "Get resynthesis (overlap-add)"
    )

    sd.play(syn.values[0].astype(np.float32), samplerate=rate)
    sd.wait()


def collect_chronicle(
    agent,
    baseline_event_id,
):
    try:
        connection = agent.memory.connection
        rows = connection.execute(
            """
            SELECT event_type, content
            FROM events
            WHERE id > ?
              AND event_type IN (
                  'CONVERSATION',
                  'AFFECTIVE_BEHAVIOR_VIOLATION',
                  'IDENTITY_CONSISTENCY_VIOLATION'
              )
            ORDER BY id ASC
            """,
            (baseline_event_id,),
        ).fetchall()
    except Exception:
        return []

    lines = []

    for event_type, content in rows:
        content = (content or "").strip()
        short = content[:220]

        if event_type == "CONVERSATION":
            lines.append(short)
        else:
            lines.append(
                f"[внутреннее событие: {short}]"
            )

    return lines


def save_diary_entry(agent, baseline_event_id):
    from identity.personal_diary import (
        PersonalDiary,
        generate_session_entry,
    )

    chronicle = collect_chronicle(
        agent,
        baseline_event_id,
    )

    if len(chronicle) < 2:
        print("Дневник: нечего записывать.")
        return

    entry = generate_session_entry(
        agent.model_orchestrator,
        chronicle,
    )

    if not entry:
        print("Дневник: генерация не удалась.")
        return

    diary = PersonalDiary(
        str(ROOT / "data" / "memory.db")
    )

    diary.write(entry, trigger="session_end")

    print("Запись в личный дневник сохранена.")


def main():
    print("=== Голосовой REPL EddieAI ===")
    if not ensure_ollama():
        print("Без Ollama мозг не работает. Выход.")
        return
    print("Гружу мозг...")
    t0 = time.perf_counter()
    from core.agent import Agent
    from core.autonomy_runtime_factory import (
        AutonomyRuntimeFactory,
    )

    agent = Agent()
    runtime = AutonomyRuntimeFactory(
        agent
    ).build()
    print(f"мозг готов за {time.perf_counter() - t0:.0f}с")

    baseline_event_id = 0

    try:
        baseline_event_id = (
            agent.memory.connection.execute(
                "SELECT MAX(id) FROM events"
            ).fetchone()[0]
            or 0
        )
    except Exception:
        pass

    try:
        from identity.soul_snapshot import (
            take_snapshot,
        )

        take_snapshot("voice_start")
    except Exception as exc:
        print(f"[снимок души недоступен: {exc}]")

    print("Уши: облако (voxtral), резерв — локальный whisper medium.")

    print()
    print("Enter — начать говорить (стоп: тишина 1.5с). Ctrl+C — выход.")
    try:
        while True:
            input("\n[Enter = говорить] ")
            try:
                pcm = record_until_silence()
                heard = transcribe(pcm)
                if not heard:
                    print("   (тишина, ничего не разобрал)")
                    continue
                print(f"Эдди: {heard}")
                answer = agent.respond(heard)
                print(f"EddieAI: {answer}")
                try:
                    speak(answer)
                except Exception as exc:
                    print(f"   [рот молчит: {exc}]")
            except KeyboardInterrupt:
                print("   (прервано)")
                continue
            except Exception:
                print("   [сбой шага, продолжаю]:")
                traceback.print_exc()
                continue
    except KeyboardInterrupt:
        pass
    finally:
        try:
            save_diary_entry(
                agent,
                baseline_event_id,
            )
        except Exception as exc:
            print(f"[дневник недоступен: {exc}]")

        try:
            from identity.soul_snapshot import (
                take_snapshot,
                diff,
            )

            before = sorted(
                (ROOT / "data" / "soul_snapshots").glob(
                    "*_voice_start.json"
                )
            )

            after = take_snapshot("voice_end")

            if before:
                report = diff(
                    before[-1], after
                )
                print(
                    "Изменения души за сессию: "
                    + json.dumps(
                        report,
                        ensure_ascii=False,
                    )
                )
        except Exception as exc:
            print(f"[снимок души недоступен: {exc}]")

        agent.close()
        print("EddieAI уснул.")


if __name__ == "__main__":
    main()
