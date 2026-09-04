from datetime import datetime, timezone
from typing import Any


TOPIC_MARKERS = (
    "изуч",
    "тема",
    "про ",
    "космо",
    "книг",
    "наук",
    "музык",
    "фильм",
    "игр",
    "язык",
)

ENVIRONMENT_MARKERS = (
    "сред",
    "комнат",
    "офис",
    "улиц",
    "природ",
    "локац",
    "вечер",
    "утр",
    "ночь",
)

NEGATIVE_MARKERS = (
    "не люб",
    "не нрав",
    "избег",
    "не хоч",
    "против",
    "ненави",
)


def _normal(value):
    return (
        str(value)
        .casefold()
        .replace("ё", "е")
    )


def _tokens(text):
    import re

    return set(
        re.findall(
            r"[A-Za-zА-Яа-яЁё0-9]{2,}",
            _normal(text),
        )
    )


def preference_type(
    method,
    context,
) -> str:
    method_text = (
        method or ""
    ).strip().casefold()

    context_text = (
        context or ""
    ).strip().casefold()

    if not method_text:
        return "unknown"

    if context_text in {
        "activity",
        "move",
    }:
        return "action"

    if any(
        marker in method_text
        for marker in TOPIC_MARKERS
    ):
        return "topic"

    if any(
        marker in method_text
        for marker in ENVIRONMENT_MARKERS
    ):
        return "environment"

    return "action"


def strength_of(entry) -> float:
    if not isinstance(entry, dict):
        return 0.0

    try:
        share = float(
            entry.get("share", 0.0) or 0.0
        )
    except (TypeError, ValueError):
        share = 0.0

    try:
        evidence = float(
            entry.get("evidence_count", 0) or 0
        )
    except (TypeError, ValueError):
        evidence = 0.0

    maturity = min(1.0, evidence / 10.0)

    value = (0.6 * share) + (0.4 * maturity)

    return round(
        min(1.0, max(0.0, value)),
        3,
    )


def entry_type(entry) -> str:
    if not isinstance(entry, dict):
        return "unknown"

    value = entry.get("type")

    if isinstance(value, str) and value:
        return value

    return preference_type(
        entry.get("method"),
        entry.get("context"),
    )


def entry_strength(entry) -> float:
    if not isinstance(entry, dict):
        return 0.0

    value = entry.get("strength")

    if value is not None:
        try:
            return max(
                0.0,
                min(1.0, float(value)),
            )
        except (TypeError, ValueError):
            pass

    return strength_of(entry)


def enrich_entry(
    entry,
    source="ACTION_CHOICE",
):
    if not isinstance(entry, dict):
        return entry

    result = dict(entry)

    now = datetime.now(
        timezone.utc
    ).isoformat()

    result.setdefault(
        "type",
        preference_type(
            result.get("method"),
            result.get("context"),
        ),
    )

    result["strength"] = strength_of(result)

    result.setdefault(
        "provenance",
        source,
    )

    result.setdefault(
        "first_seen_ts",
        result.get("ts") or now,
    )

    result["last_seen_ts"] = now

    return result


def _shares_token(
    left,
    right,
) -> bool:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)

    if not left_tokens or not right_tokens:
        return False

    return bool(
        left_tokens & right_tokens
    )


def preference_conflicts(
    preferences,
    interests,
):
    conflicts = []

    if not isinstance(
        interests,
        list,
    ):
        interests = []

    interests = [
        str(item)
        for item in interests
    ]

    for pref in preferences:
        if not isinstance(pref, dict):
            continue

        label = str(
            pref.get("label", "")
        )
        method = str(
            pref.get("method", "")
        )

        text = _normal(
            (label + " " + method).lower()
        )

        if not any(
            marker in text
            for marker in NEGATIVE_MARKERS
        ):
            continue

        for interest in interests:
            if not _shares_token(
                text,
                interest,
            ):
                continue

            conflicts.append({
                "preference": str(
                    pref.get(
                        "label",
                        "предпочтение",
                    )
                ),
                "interest": interest,
                "reason": (
                    "предпочтение выражает негатив "
                    "про тему интереса"
                ),
            })

            break

    return conflicts


def format_preferences_rich(
    items,
    interests=None,
) -> list[str]:
    if not isinstance(items, list):
        return []

    from identity.preference_label import (
        preference_label,
    )

    conflict_by_label = {}

    for conflict in preference_conflicts(
        items,
        interests,
    ):
        conflict_by_label[
            conflict["preference"]
        ] = conflict

    result = []

    for item in items:
        if not isinstance(item, dict):
            result.append(str(item))
            continue

        label = preference_label(item)

        kind = entry_type(item)

        strength = entry_strength(item)

        line = (
            f"{label} (тип: {kind}, "
            f"сила: {strength:.2f})"
        )

        conflict = conflict_by_label.get(
            label
        )

        if conflict is not None:
            line += (
                " [конфликт с интересом "
                f"«{conflict['interest']}»]"
            )

        result.append(line)

    return result
