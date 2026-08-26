from datetime import datetime


def _normalize(text, limit):
    value = str(text or "").strip().lower()

    value = " ".join(value.split())

    if len(value) > limit:
        value = value[:limit]

    return value


def _period(now):
    hour = now.hour

    if 5 <= hour < 12:
        return "morning"

    if 12 <= hour < 17:
        return "day"

    if 17 <= hour < 23:
        return "evening"

    return "night"


def _freshness_bucket(minutes):
    if minutes < 30:
        return 0

    if minutes < 120:
        return 1

    if minutes < 360:
        return 2

    if minutes < 720:
        return 3

    return 4


def _affect_key(affect):
    if affect is None:
        return "neutral"

    if isinstance(affect, dict):
        value = affect.get("valence")
    else:
        value = affect

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "neutral"

    if value > 0.3:
        return "positive"

    if value < -0.3:
        return "negative"

    return "neutral"


def encode_situation(state):
    goal = _normalize(state.get("goal"), 120)
    task_type = _normalize(state.get("task_type"), 60)

    inbox = "y" if state.get("inbox_unread") else "n"

    affect = _affect_key(state.get("affect"))

    now = state.get("now") or datetime.now()

    period = _normalize(
        state.get("period")
        or _period(now),
        20,
    )

    try:
        freshness = int(state.get("freshness", 0))
    except (TypeError, ValueError):
        freshness = 0

    return "|".join([
        f"g={goal or 'none'}",
        f"t={task_type or 'none'}",
        f"i={inbox}",
        f"a={affect}",
        f"p={period or 'unknown'}",
        f"f={_freshness_bucket(freshness)}",
    ])
