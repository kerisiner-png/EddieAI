import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))

parser = argparse.ArgumentParser()

parser.add_argument(
    "--minutes",
    type=int,
    default=30,
    help=(
        "Длительность проверочной сессии "
        "автономии в минутах."
    ),
)

parser.add_argument(
    "--no-chat",
    action="store_true",
    help=(
        "Не поднимать окно чата "
        "(по умолчанию чат включён)."
    ),
)

args = parser.parse_args()

LOG = str(BASE_DIR / "logs" / "eddie_night.log")
END_AT = time.time() + args.minutes * 60
_call_count = {"n": 0}


def log(msg):
    stamp = datetime.now().strftime(
        "%H:%M:%S",
    )
    line = f"[{stamp}] {msg}"
    with open(
        LOG,
        "a",
        encoding="utf-8",
    ) as f:
        f.write(line + "\n")


log("=== NIGHT RUN START (restart) ===")

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)
from core.resource_watchdog import (
    ResourceWatchdog,
)

agent = Agent()

try:
    from identity.soul_snapshot import (
        take_snapshot as soul_take_snapshot,
        diff as soul_diff,
    )

    before_snap = soul_take_snapshot("before")
    log(f"soul snapshot before: {before_snap.name}")
except Exception as exc:
    before_snap = None
    log(
        f"soul snapshot before unavailable: "
        f"{type(exc).__name__}"
    )

runtime = AutonomyRuntimeFactory(
    agent,
    scheduler_max_ticks_per_window=(
        10**9
    ),
    scheduler_interval_seconds=15,
    enable_decision_core=True,
    resource_watchdog=ResourceWatchdog(
        enabled=True,
        low_ram_mb=256,
        critical_ram_mb=192,
    ),
).build()

original_cloud = (
    agent.model_orchestrator._cloud_chat
)


def limited_cloud(**kwargs):
    _call_count["n"] += 1
    log(
        f"cloud call #{_call_count['n']}"
    )
    return original_cloud(**kwargs)


agent.model_orchestrator._cloud_chat = (
    limited_cloud
)

import ollama

_original_ollama_chat = ollama.chat


def _cloud_bridge_chat(*args, **kwargs):
    messages = kwargs.get(
        "messages",
        [],
    )

    system = ""
    user = ""

    for message in messages:
        role = message.get("role")
        content = message.get(
            "content",
            "",
        )

        if role == "system":
            system += "\n" + content
        else:
            user += "\n" + content

    options = kwargs.get(
        "options",
        {},
    )

    result = limited_cloud(
        system=system.strip(),
        user=user.strip(),
        options=options,
        task="deep",
    )

    if result is None:
        result = ""

    return {
        "message": {
            "role": "assistant",
            "content": result,
        },
    }


ollama.chat = _cloud_bridge_chat

from core.night_consolidation import (
    NightConsolidator,
)

from memory.events import Event

import sqlite3 as _sq

_start_event_id = 0

_check = _sq.connect(
    f"file:{BASE_DIR / 'data' / 'memory.db'}?mode=ro",
    uri=True,
)

row = _check.execute(
    "SELECT MAX(id) FROM events"
).fetchone()

if row and row[0]:
    _start_event_id = row[0]

_perm_exists = _check.execute(
    "SELECT COUNT(*) FROM events "
    "WHERE source='Eddie' AND "
    "content LIKE '%выходить за обычные лимиты%'"
).fetchone()[0]

_check.close()

if not _perm_exists:
    eddie_message = (
        "Эдди: давай, изучай. Я разрешил тебе "
        "выходить за обычные лимиты — ничего "
        "страшного. Исследуй свои темы: "
        "понимание устройства мира, развитие "
        "способностей, свою собственную природу. "
        "Утром расскажешь, к чему пришёл."
    )

    agent.memory.remember(
        Event.create(
            content=eddie_message,
            event_type="CONVERSATION",
            source_type="DIRECT_INTERACTION",
            source="Eddie",
            personal_experience=False,
            confidence=1.0,
            verified=True,
        )
    )

    log("записано разрешение Эдди на исследование")

else:
    log(
        "разрешение Эдди уже в памяти — "
        "не дублирую"
    )

conn = sqlite3.connect(
    f"file:{BASE_DIR / 'data' / 'memory.db'}?mode=ro",
    uri=True,
)

recent_system = conn.execute(
    "SELECT COUNT(*) FROM events "
    "WHERE event_type='SYSTEM' "
    "AND content LIKE '%до 11:00 утра%'"
).fetchone()[0]

conn.close()

if recent_system == 0:
    from memory.events import Event

    deadline_text = (
        "Эдди запустил тебя в проверочном "
        "режиме автономии. Поработай "
        f"самостоятельно {args.minutes} минут, "
        "а потом он посмотрит, чем ты занимался "
        "и к каким выводам пришёл."
    )

    agent.memory.remember(
        Event.create(
            content=deadline_text,
            event_type="SYSTEM",
            source_type="SYSTEM",
            source="SYSTEM",
            personal_experience=False,
            confidence=1.0,
            verified=True,
        )
    )

    log("записано событие о времени до 11:00")
else:
    log("событие о времени уже в памяти — не дублирую")

status = runtime.start_background_loop()
log(f"autonomy loop: {status['status']}")

chat = None

if not args.no_chat:
    try:
        from communication.chat_app import (
            EddieChatApp,
        )

        chat = EddieChatApp(
            agent=agent,
            server=getattr(
                runtime,
                "eddie_server",
                None,
            ),
        )
        chat.start_embedded()
        log("chat attached")
    except Exception as exc:
        chat = None
        log(
            f"chat unavailable: "
            f"{type(exc).__name__}: {exc}"
        )

try:
    while True:

        if time.time() >= END_AT:
            log(
                f"сессия {args.minutes} мин "
                "завершена"
            )
            break

        state = getattr(
            runtime,
            "state",
            "?",
        )

        ls = getattr(
            runtime,
            "orchestrator",
            None,
        )
        ls = (
            getattr(ls, "_last_state", None)
            or {}
        )

        dec = getattr(
            runtime,
            "orchestrator",
            None,
        )
        dec = getattr(
            dec, "_last_decision", None
        )

        ag = getattr(runtime, "agent", None)
        chat_len = getattr(
            ag, "_last_chat_len", None
        )

        log(
            f"tick-статус: state={state}, "
            f"cloud_calls={_call_count['n']}, "
            f"inbox={ls.get('inbox_unread')}, "
            f"idle={ls.get('idle_seconds')}, "
            f"decision={dec}, "
            f"chat_len={chat_len}"
        )

        remaining = END_AT - time.time()

        deadline = time.time() + min(
            20.0, max(1.0, remaining)
        )

        while time.time() < deadline:
            if chat is not None:
                chat.update()
            time.sleep(0.2)
finally:
    if chat is not None:
        try:
            grace_deadline = (
                time.time() + 90
            )

            while (
                chat.is_busy()
                and time.time()
                < grace_deadline
            ):
                chat.update()
                time.sleep(0.2)

            chat.stop()
            log("chat stopped")
        except Exception:
            log("chat stop failed")

    try:
        runtime.stop_background_loop()
        log("autonomy loop stopped")
    except Exception:
        log("runtime stop failed (not initialized?)")

    ollama.chat = _original_ollama_chat

    try:
        consolidator = NightConsolidator(
            memory=agent.memory,
            model_orchestrator=(
                agent.model_orchestrator
            ),
            conclusion_store=(
                agent.self_conclusion_store
            ),
        )

        night_result = consolidator.run(
            since_id=_start_event_id
        )

        log(
            f"консолидация: "
            f"{night_result['chronicle_events']} "
            f"событий, выводов сохранено: "
            f"{len(night_result['conclusions_saved'])}, "
            f"llm_used={night_result['llm_used']}"
        )
    except Exception as exc:
        log(
            f"консолидация ошибка: "
            f"{type(exc).__name__}: {exc}"
        )

    agent.close()
    log("agent closed")

    if before_snap is not None:
        try:
            after_snap = soul_take_snapshot("after")
            diff_report = soul_diff(
                before_snap,
                after_snap,
            )
            log(
                f"soul diff: "
                f"{diff_report}"
            )
        except Exception as exc:
            log(
                f"soul diff unavailable: "
                f"{type(exc).__name__}"
            )
    log("=== NIGHT RUN END ===")
