import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PASS = []
FAIL = []
RUN_START = datetime(2026, 8, 29, 22, 26, 0, tzinfo=timezone.utc)


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(("PASS" if ok else "FAIL"), name, detail)


log_path = BASE / "logs" / "eddie_night.log"
log_lines = log_path.read_text(encoding="utf-8").splitlines()

# 1. Прогон завершился
log_text = "\n".join(log_lines)
check(
    "прогон до END",
    "NIGHT RUN END" in log_text,
    "маркер NIGHT RUN END присутствует",
)

# 2. Лог растёт равномерно (последние тики, отсоединение от END)
check(
    "консолидация без ошибки",
    "консолидация: " in log_text
    and "консолидация ошибка" not in log_text,
    "NightConsolidator завершился без ошибки",
)

# 7. Консолидация: события > 0, выводы >= 1.
# Лог многопрогонный — берём ПОСЛЕДНЮЮ строку консолидации (текущий прогон).
matches = list(
    re.finditer(
        r"консолидация: (\d+) [Сс]обытий, выводов сохранено: (\d+)",
        log_text,
    )
)
m = matches[-1] if matches else None
if m:
    chronicle = int(m.group(1))
    conclusions = int(m.group(2))
    check(
        "консолидация хронических событий",
        chronicle > 0,
        f"chronicle_events={chronicle}",
    )
    check(
        "выводы сохранены",
        conclusions >= 1,
        f"conclusions={conclusions}",
    )
else:
    check("консолидация хронических событий", False, "строки консолидации нет")

# 5. Мало облачных вызовов: последний номер счётчика перед последним END
ends = [i for i, l in enumerate(log_lines) if "NIGHT RUN END" in l]
if ends:
    cc_nums = [
        int(mm.group(1))
        for i, l in enumerate(log_lines)
        if i < ends[-1]
        for mm in [re.search(r"cloud call #(\d+)", l)]
        if mm
    ]
    last_cc = cc_nums[-1] if cc_nums else 0
    check(
        "мало облачных вызовов",
        last_cc <= 40,
        f"last_cc_counter={last_cc}",
    )
else:
    check("мало облачных вызовов", False, "нет END-маркера")

# 6. Watchdog: нет THROTTLED
check(
    "watchdog без троттлинга",
    "THROTTLED" not in log_text,
    "нет серий THROTTLED",
)

conn = sqlite3.connect(str(BASE / "data" / "memory.db"))
conn.row_factory = sqlite3.Row
RUN_ISO = RUN_START.isoformat()

n_lc = conn.execute(
    "SELECT COUNT(1) c FROM events WHERE event_type='LIFE_CYCLE' "
    "AND timestamp > ?",
    (RUN_ISO,),
).fetchone()["c"]
check("переходы сна", n_lc >= 2, f"LIFE_CYCLE={n_lc}")

n_morning = conn.execute(
    "SELECT COUNT(1) c FROM events WHERE event_type='SELF_EXPERIENCE' "
    "AND timestamp > ? AND content LIKE '%проснул%'",
    (RUN_ISO,),
).fetchone()["c"]
n_evening = conn.execute(
    "SELECT COUNT(1) c FROM events WHERE event_type='REFLECTION' "
    "AND timestamp > ? AND content LIKE '%день%'",
    (RUN_ISO,),
).fetchone()["c"]
check(
    "ритуалы утро/вечер",
    n_morning >= 1 and n_evening >= 1,
    f"morning={n_morning}, evening={n_evening}",
)

check(
    "soul diff перед/после",
    "soul diff: " in log_text
    and "soul diff unavailable" not in log_text,
    "строки soul diff присутствуют",
)

print("---")
if FAIL:
    print("RUBEZH_B: FAIL —", len(FAIL))
    for name, det in FAIL:
        print("  FAIL", name, det)
    raise SystemExit(1)
print("RUBEZH_B: ALL PASS —", len(PASS))
