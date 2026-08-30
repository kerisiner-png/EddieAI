import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory.database import Memory
from memory.events import Event


def _seed(memory):
    now = datetime.now(timezone.utc).isoformat()
    for i, (ctype, text) in enumerate([
        ("LIFE_CYCLE", "Я проснулся после сна"),
        ("SELF_EXPERIENCE", "Я сделал полезное дело"),
        ("ACTION_CHOICE", "Я решил заняться темой"),
        ("REFLECTION", "Я подвёл итог дня"),
        ("COGNITIVE_DECISION", "Я принял когнитивное решение"),
        ("CHAT_OUTPUT", "Это не должно попасть в ленту жизни"),
    ]):
        memory.remember(
            Event.create(
                content=text,
                event_type=ctype,
                source_type="SELF_OUTPUT" if ctype == "CHAT_OUTPUT" else "SELF_OBSERVATION",
                source="self",
                personal_experience=True,
                confidence=1.0,
                verified=True,
                interpretation=text,
            )
        )


def test_life_feed_filters_and_orders():
    memory = Memory(Path(":memory:"))
    _seed(memory)

    feed = memory.recent_life_feed(limit=10)

    assert "CHAT_OUTPUT" not in feed
    assert "не должно попасть" not in feed
    assert "Я проснулся после сна" in feed
    assert "Я подвёл итог дня" in feed
    assert "Я сделал полезное дело" in feed

    lines = [line for line in feed.splitlines() if line.strip()]
    times = [line[1:6] for line in lines]
    assert len(times) == 5
    assert all(len(t) == 5 for t in times)


def test_life_feed_limit():
    memory = Memory(Path(":memory:"))
    _seed(memory)

    feed = memory.recent_life_feed(limit=2)
    assert len([line for line in feed.splitlines() if line.strip()]) == 2


def test_life_feed_empty():
    memory = Memory(Path(":memory:"))
    assert memory.recent_life_feed() == ""


if __name__ == "__main__":
    test_life_feed_filters_and_orders()
    test_life_feed_limit()
    test_life_feed_empty()
    print("ALL OK")