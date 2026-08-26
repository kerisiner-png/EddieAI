from pathlib import Path
from tempfile import TemporaryDirectory

from memory.database import Memory


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")

    key = "g=изучить тему: космос|t=research|i=n|a=positive|p=day|f=0"

    found = db.pattern_lookup(key)

    assert found is None, "пустое хранилище не должно находить паттерн"

    db.pattern_record(
        key,
        '{"kind": "EXECUTE", "payload": null}',
        confidence=0.8,
    )

    found = db.pattern_lookup(key)

    assert found is not None, "паттерн должен находиться после записи"
    assert found["situation_key"] == key
    assert found["confidence"] == 0.8
    assert found["times_used"] == 0

    db.pattern_bump(key)
    db.pattern_bump(key)

    found = db.pattern_lookup(key)

    assert found["times_used"] == 2, "times_used должен стать 2 после двух bump"

    stats = db.pattern_stats()

    assert stats["patterns"] == 1
    assert stats["total_uses"] == 2

    db.pattern_record(
        key,
        '{"kind": "GENERATE_PLAN", "payload": null}',
        confidence=0.9,
    )

    found = db.pattern_lookup(key)

    assert found["confidence"] == 0.9
    assert "GENERATE_PLAN" in found["action"]

    stats = db.pattern_stats()

    assert stats["patterns"] == 1, "повторная запись не должна плодить строки"

    print("STATS:", stats)
    print("ALL PASS")

    db.close()
