import argparse
import socket

HOST = "127.0.0.1"
PORT = 7778


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Управление сном EddieAI "
            "(через мессенджер-порт)."
        )
    )
    parser.add_argument(
        "action",
        choices=["wake", "sleep", "status"],
        help="wake — разбудить, sleep — усыпить, "
        "status — показать состояние.",
    )
    args = parser.parse_args()

    if args.action == "status":
        try:
            import json
            from pathlib import Path

            d = json.loads(
                Path(
                    "C:/EddieAI/data/status.json"
                ).read_text(encoding="utf-8")
            )
            state = "СПИТ" if d.get("asleep") else (
                "БОДРСТВУЕТ"
            )
            print(f"EddieAI: {state}")
            return
        except Exception:
            print("не могу прочитать status.json")
            return

    try:
        s = socket.create_connection(
            (HOST, PORT), timeout=3
        )
        payload = (
            '{"type": "life_control", '
            f'"action": "{args.action}"}}\n'
        )
        s.sendall(payload.encode("utf-8"))
        s.close()
        print(
            f"Команда '{args.action}' отправлена EddieAI."
        )
    except OSError as exc:
        print(
            f"Не удалось подключиться к EddieAI "
            f"({HOST}:{PORT}): {exc}"
        )


if __name__ == "__main__":
    main()