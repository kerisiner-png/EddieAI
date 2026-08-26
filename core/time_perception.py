from datetime import datetime, timezone

from memory.events import Event


def period_name(now=None):
    now = now or datetime.now()

    hour = now.hour

    if 5 <= hour < 12:
        return "утро"

    if 12 <= hour < 17:
        return "день"

    if 17 <= hour < 23:
        return "вечер"

    return "ночь"


def current_time_context():
    now = datetime.now()

    return (
        f"Текущее время: "
        f"{now.strftime('%Y-%m-%d %H:%M')}, "
        f"период суток: {period_name(now)}"
    )


def recent_action_times(
    memory,
    limit: int = 5,
):
    rows = memory.connection.execute("""
        SELECT content, timestamp
        FROM events
        WHERE event_type = 'TIME_PERCEPTION'
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        return ""

    lines = []

    for row in reversed(rows):
        content = str(
            row["content"] or ""
        ).strip()

        ts = str(row["timestamp"] or "")

        lines.append(
            f"- {content}"
            + (
                f" (в {ts[11:16]} UTC)"
                if len(ts) >= 16
                else ""
            )
        )

    return (
        "Недавние временные затраты EddieAI:\n"
        + "\n".join(lines)
    )


def record_action_time(
    memory,
    description: str,
    duration_sec: float,
):
    try:
        duration_sec = max(
            0.0,
            float(duration_sec),
        )
    except (TypeError, ValueError):
        duration_sec = 0.0

    minutes = duration_sec / 60.0

    if duration_sec >= 60.0:
        duration_text = (
            f"{minutes:.1f} мин"
        )
    else:
        duration_text = (
            f"{duration_sec:.0f} с"
        )

    memory.remember(
        Event.create(
            content=(
                f"{description} заняло "
                f"{duration_text}"
            ),
            event_type="TIME_PERCEPTION",
            source_type="SELF_OBSERVATION",
            source="time_perception",
            personal_experience=True,
            confidence=1.0,
            verified=True,
        )
    )
