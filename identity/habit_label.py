from typing import Any

PHRASE = "привык действовать через источник"


def _fallback(action: str) -> str:
    if not action:
        return "склонен повторять одно действие"
    return f"{PHRASE} «{action}»"


def habit_label(item: Any) -> str:
    if isinstance(item, dict):
        label = item.get("label")

        if isinstance(label, str) and label.strip():
            return label

        return _fallback(
            str(item.get("action", "")),
        )

    text = str(item)

    if text.startswith("repeated_action:"):
        action = text[len("repeated_action:"):]
        return _fallback(action)

    return text


def format_habits(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    return [
        habit_label(item)
        for item in items
    ]
