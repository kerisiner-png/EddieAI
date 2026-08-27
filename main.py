import os
import sys

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)

import traceback


LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "logs",
)


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


def main():
    os.makedirs(
        LOG_DIR,
        exist_ok=True,
    )
    log_path = os.path.join(
        LOG_DIR,
        "eddie_session.log",
    )

    sys.stdout = Tee(
        sys.stdout,
        log_path,
    )
    sys.stderr = Tee(
        sys.stderr,
        log_path,
    )

    agent = None
    baseline = 0

    try:
        agent = Agent()
        baseline = (
            agent.memory.connection.execute(
                "SELECT MAX(id) FROM events"
            ).fetchone()[0]
            or 0
        )
    except Exception as exc:
        print(f"Ошибка инициализации агента: {exc}")
        traceback.print_exc()
        return

    runtime = (
        AutonomyRuntimeFactory(
            agent
        ).build()
    )

    print("=" * 60)
    print("EddieAI v0.1")
    print("=" * 60)
    print("Первичная стадия развития.")
    print("Сообщение может быть многострочным.")
    print("Отправка — пустая строка.")
    print("Для выхода напиши: exit")
    print()

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
                answer = agent.respond(
                    user_message
                )
                print(
                    f"\nEddieAI > {answer}\n"
                )
            except Exception as exc:
                print(
                    f"\nОшибка агента: {exc}\n"
                )
                traceback.print_exc()

    finally:
        if agent is not None:
            from communication.session import (
                close_session,
            )

            try:
                from pathlib import Path
                root = Path(
                    os.path.dirname(
                        os.path.abspath(__file__)
                    )
                )

                close_session(
                    agent,
                    root,
                    baseline_event_id=baseline,
                    prefix="session",
                )
            except Exception as exc:
                print(
                    f"Ошибка закрытия сессии: {exc}"
                )
                traceback.print_exc()


if __name__ == "__main__":
    main()
