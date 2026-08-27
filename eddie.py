import os
import sys
import time
import argparse
import traceback
from pathlib import Path


ROOT = Path(r"C:\EddieAI")
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"


class Tee:
    def __init__(self, stream, path):
        self.stream = stream
        self.file = open(
            path,
            "a",
            encoding="utf-8",
            buffering=1,
        )

    def write(self, data):
        self.stream.write(data)
        self.file.write(data)

    def flush(self):
        self.stream.flush()
        self.file.flush()


def _setup_logging():
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    log_path = LOG_DIR / "eddie_session.log"
    sys.stdout = Tee(sys.stdout, log_path)
    sys.stderr = Tee(sys.stderr, log_path)


def _build(verbose=True):
    from core.agent import Agent
    from core.autonomy_runtime_factory import (
        AutonomyRuntimeFactory,
    )

    if verbose:
        print("Гружу мозг...")

    t0 = time.perf_counter()

    agent = Agent()

    AutonomyRuntimeFactory(
        agent
    ).build()

    if verbose:
        print(
            f"мозг готов за "
            f"{time.perf_counter() - t0:.0f}с"
        )

    return agent


def _baseline_event_id(agent):
    try:
        return (
            agent.memory.connection.execute(
                "SELECT MAX(id) FROM events"
            ).fetchone()[0]
            or 0
        )
    except Exception:
        return 0


def _make_voice():
    from communication.voice_io import VoiceIO
    return VoiceIO()


def _run_text(agent):
    print("=" * 60)
    print("EddieAI v0.1 — текстовый режим")
    print("=" * 60)
    print("Отправка — пустая строка.")
    print("Для выхода напиши: exit")

    try:
        while True:
            first = input("Эдди > ").strip()

            if first.lower() == "exit":
                break

            if not first:
                continue

            lines = [first]

            while True:
                line = input()
                if not line.strip():
                    break
                lines.append(line)

            user_message = (
                "\n".join(lines).strip()
            )

            if not user_message:
                continue

            if len(user_message) < 2:
                print(
                    "\n[EddieAI] Напиши что-нибудь "
                    "подлиннее — я же хочу понять "
                    "тебя правильно.\n"
                )
                continue

            print(
                f"[принято символов: "
                f"{len(user_message)}]"
            )

            try:
                answer = agent.respond(user_message)
                print(
                    f"\nEddieAI > {answer}\n"
                )
            except Exception as exc:
                print(f"\nОшибка агента: {exc}\n")
                traceback.print_exc()
    except KeyboardInterrupt:
        pass


def _run_voice(agent, voice):
    print("=== Голосовой режим ===")
    if not ensure_ollama():
        print(
            "Предупреждение: Ollama не поднялась. "
            "Облачный мозг (Zen) работает без неё."
        )
    if voice is None:
        print("Голосовые уши недоступны. Переключитесь в --mode text.")
        return
    print("Уши: vosk small-ru (локально).")
    print("Enter — начать говорить (стоп: тишина). Ctrl+C — выход.")

    try:
        while True:
            input("\n[Enter = говорить] ")
            try:
                text = voice.record_and_transcribe()
                if not text:
                    print("   (тишина, ничего не разобрал)")
                    continue
                print(f"Эдди: {text}")
                answer = agent.respond(text)
                print(f"EddieAI: {answer}")
                try:
                    from communication.voice_io import (
                        mood_from_agent,
                    )

                    voice.speak(
                        answer,
                        mood=mood_from_agent(agent),
                    )
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


def _run_chat(agent, use_chat_voice):
    from communication.chat_app import EddieChatApp

    try:
        from communication.voice_io import VoiceIO
        use_chat_voice = use_chat_voice and VoiceIO
    except Exception:
        pass

    app = EddieChatApp(
        agent=agent,
    )
    app.start_embedded()

    print("=== Режим общения (вкладка в трее) ===")
    print("Enter — пустая строка → ответить текстом.")
    print("v + Enter — голосовое сообщение.")
    print("exit — выход.")

    try:
        while True:
            line = input("Эдди > ").strip()

            if line.lower() == "exit":
                break

            if line.lower() == "v":
                app._on_mic()
                time.sleep(0.2)
                continue

            if not line:
                continue

            if len(line) < 2:
                print(
                    "\n[EddieAI] Напиши что-нибудь "
                    "подлиннее — я же хочу понять "
                    "тебя правильно.\n"
                )
                continue

            app._on_user_send(line)
            time.sleep(0.2)

            while app.is_busy():
                app.update()
                time.sleep(0.1)

            while True:
                try:
                    if app._chat is not None:
                        app.update()
                    break
                except Exception:
                    break

            time.sleep(0.3)
            app.update()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()


def _run_mixed(agent, voice):
    print("=== Режим mixed ===")
    print("Enter + текст — написать сообщение.")
    print("v + Enter — голосовое сообщение.")
    print("exit — выход.")

    try:
        while True:
            mark = input("\n[текст или v] Эдди > ").strip()

            if mark.lower() == "exit":
                break

            if mark.lower() == "v":
                if voice is None:
                    print("   (голос недоступен)")
                    continue
                try:
                    text = voice.record_and_transcribe()
                    if not text:
                        print("   (тишина, ничего не разобрал)")
                        continue
                    print(f"Эдди: {text}")
                except KeyboardInterrupt:
                    print("   (прервано)")
                    continue
                except Exception:
                    print("   [сбой голоса]:")
                    traceback.print_exc()
                    continue
            else:
                text = mark

            if not text:
                print("   (пусто)")
                continue

            if len(text) < 2:
                print(
                    "\n[EddieAI] Напиши что-нибудь "
                    "подлиннее — я же хочу понять "
                    "тебя правильно.\n"
                )
                continue

            print(f"[принято символов: {len(text)}]")

            try:
                answer = agent.respond(text)
                print(f"\nEddieAI > {answer}\n")
                if voice is not None:
                    try:
                        from communication.voice_io import (
                            mood_from_agent,
                        )

                        voice.speak(
                            answer,
                            mood=mood_from_agent(agent),
                        )
                    except Exception as exc:
                        print(f"   [рот молчит: {exc}]")
            except KeyboardInterrupt:
                print("   (прервано)")
                continue
            except Exception as exc:
                print(f"\nОшибка агента: {exc}\n")
                traceback.print_exc()
    except KeyboardInterrupt:
        pass


def ensure_ollama(timeout_sec=40):
    import subprocess
    import urllib.request

    OLLAMA_EXE = Path(
        r"C:\Users\keris\AppData\Local\Programs\Ollama\ollama.exe"
    )

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


def main():
    parser = argparse.ArgumentParser(
        description="EddieAI — единая точка входа"
    )
    parser.add_argument(
        "--mode",
        choices=["text", "voice", "mixed", "chat"],
        default="mixed",
        help="режим общения: text|voice|mixed|chat",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="писать лог в logs/eddie_session.log",
    )
    args = parser.parse_args()

    mode = args.mode

    if args.log:
        _setup_logging()

    if mode in ("voice", "mixed"):
        if not ensure_ollama():
            print(
                "Предупреждение: Ollama не поднялась. "
                "Облачный мозг (Zen) работает без неё."
            )

    agent = None

    try:
        agent = _build()
    except Exception as exc:
        print(f"Ошибка инициализации агента: {exc}")
        traceback.print_exc()
        return

    baseline = _baseline_event_id(agent)

    voice = None
    use_voice = mode in ("voice", "mixed", "chat")

    if use_voice:
        try:
            voice = _make_voice()
        except Exception as exc:
            print(f"[голос недоступен: {exc}]")
            voice = None

    try:
        if mode == "text":
            _run_text(agent)
        elif mode == "voice":
            _run_voice(agent, voice)
        elif mode == "mixed":
            _run_mixed(agent, voice)
        elif mode == "chat":
            _run_chat(agent, use_voice and voice is not None)
    except Exception as exc:
        print(f"Ошибка сессии: {exc}")
        traceback.print_exc()

    from communication.session import (
        close_session,
    )

    close_session(
        agent,
        ROOT,
        baseline_event_id=baseline,
        prefix="eddie",
    )


if __name__ == "__main__":
    main()
