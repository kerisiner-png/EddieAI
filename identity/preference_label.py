from typing import Any


def _fallback_label(
    context: str,
    method: str,
) -> str:
    if not method:
        return "предпочтение"

    return (
        f"в контексте «{context or 'обычном'}» "
        f"предпочитает «{method}»"
    )


def preference_label(item: Any) -> str:
    if isinstance(item, dict):
        label = item.get("label")

        if isinstance(label, str) and label.strip():
            return label

        return _fallback_label(
            str(item.get("context", "")),
            str(item.get("method", "")),
        )

    return str(item)


def format_preferences(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    return [
        preference_label(item)
        for item in items
    ]
