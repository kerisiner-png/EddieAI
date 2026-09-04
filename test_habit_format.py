import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity.habit_label import (
    habit_label,
    format_habits,
)

PHRASE = "привык действовать через источник"


def test_habit_label_signature_string():
    out = habit_label("repeated_action:research")
    assert PHRASE in out.lower()
    assert "research" in out


def test_habit_label_plain_string_passthrough():
    assert habit_label("люблю ранние подъёмы") == "люблю ранние подъёмы"


def test_habit_label_dict_with_label():
    out = habit_label({
        "label": "привык проверять факты",
        "action": "research",
    })
    assert out == "привык проверять факты"


def test_habit_label_dict_fallback():
    out = habit_label({
        "action": "research",
    })
    assert PHRASE in out.lower()


def test_format_habits_mixed():
    formatted = format_habits([
        "repeated_action:research",
        "люблю тишину",
        {"label": "привык писать заметки"},
    ])
    assert len(formatted) == 3
    assert "research" in formatted[0]
    assert formatted[1] == "люблю тишину"
    assert formatted[2] == "привык писать заметки"


def test_format_habits_not_list():
    assert format_habits(None) == []
    assert format_habits("strom") == []


if __name__ == "__main__":
    test_habit_label_signature_string()
    test_habit_label_plain_string_passthrough()
    test_habit_label_dict_with_label()
    test_habit_label_dict_fallback()
    test_format_habits_mixed()
    test_format_habits_not_list()
    print("ALL OK")
