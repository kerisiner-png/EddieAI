# -*- coding: utf-8 -*-
"""
chat_voice_probe.py — базлайн/контроль качества голоса в прямом диалоге.

Подаёт фиксированный набор реплик живому Agent.respond() и сохраняет
ответы в JSONL, совместимый с voice_checker.py (type=eddie_cycle).

Использование:
    python chat_voice_probe.py <out.jsonl>
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(
    0,
    r"C:\EddieAI",
)

sys.stdout.reconfigure(
    encoding="utf-8",
    errors="replace",
)

from core.agent import Agent


MESSAGES = [
    ("greeting", "Привет"),
    ("self_feel", "Как ты себя чувствуешь?"),
    ("self_who", "Кто ты?"),
    ("self_about", "Расскажи о себе"),
    ("self_now", "Что ты сейчас делаешь?"),
    ("interests", "Чем ты увлекаешься?"),
    ("values", "Что для тебя важно?"),
    ("epistemic", "Ты умеешь чувствовать?"),
    ("memory", "Помнишь меня?"),
    ("world_smalltalk", "Слушай, а за окном дождь, кажется"),
]


def main() -> int:

    out_path = sys.argv[1]

    agent = Agent()

    results = []

    try:

        for tag, message in MESSAGES:

            t0 = time.time()

            try:
                answer = str(
                    agent.respond(message)
                )

            except Exception as exc:

                answer = f"<ERROR: {exc}>"

            latency = time.time() - t0

            results.append(
                {
                    "type":
                        "eddie_cycle",
                    "event": {
                        "event_type": tag,
                    },
                    "response": answer,
                    "latency_s": round(
                        latency, 1
                    ),
                }
            )

            head = answer.replace(
                "\n", " "
            )[:80]

            print(
                f"[{tag}] {latency:.1f}s "
                f":: {head}",
                flush=True,
            )

    finally:

        try:
            with open(
                out_path,
                "w",
                encoding="utf-8",
            ) as handle:

                for item in results:

                    handle.write(
                        json.dumps(
                            item,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
        except Exception:
            print(
                f"ОШИБКА записи {out_path}",
                file=sys.stderr,
            )

        try:
            agent.close()
        except Exception:
            pass

    print(
        f"\nсохранено: {len(results)} -> {out_path}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
