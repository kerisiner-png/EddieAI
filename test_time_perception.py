from pathlib import Path
from tempfile import TemporaryDirectory

from core.time_perception import (
    current_time_context,
    recent_action_times,
    record_action_time,
)
from memory.database import Memory


ctx = current_time_context()

assert "Текущее время" in ctx, ctx

with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")

    recent = recent_action_times(db, limit=5)

    assert recent == "", "без действий контекст времени пуст"

    record_action_time(db, "Провести исследование: космос", 90.0)
    record_action_time(db, "Проанализировать", 15.0)

    recent = recent_action_times(db, limit=5)

    assert "исследование: космос" in recent, recent
    assert "1.5 мин" in recent, recent
    assert "Проанализировать" in recent
    assert "15 с" in recent

    print("CTX:", ctx)
    print("RECENT:", recent.replace("\n", " | "))
    print("ALL PASS")

    db.close()
