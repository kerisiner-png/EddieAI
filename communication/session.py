import json


def collect_chronicle(
    agent,
    baseline_event_id,
):
    try:
        connection = agent.memory.connection
        rows = connection.execute(
            """
            SELECT event_type, content
            FROM events
            WHERE id > ?
              AND event_type IN (
                  'CONVERSATION',
                  'AFFECTIVE_BEHAVIOR_VIOLATION',
                  'IDENTITY_CONSISTENCY_VIOLATION'
              )
            ORDER BY id ASC
            """,
            (baseline_event_id,),
        ).fetchall()
    except Exception:
        return []

    lines = []

    for event_type, content in rows:
        content = (content or "").strip()
        short = content[:220]

        if event_type == "CONVERSATION":
            lines.append(short)
        else:
            lines.append(
                f"[внутреннее событие: {short}]"
            )

    return lines


def save_diary_entry(
    agent,
    baseline_event_id,
    root=None,
):
    from identity.personal_diary import (
        PersonalDiary,
        generate_session_entry,
    )

    chronicle = collect_chronicle(
        agent,
        baseline_event_id,
    )

    if len(chronicle) < 2:
        print("Дневник: нечего записывать.")
        return False

    entry = generate_session_entry(
        agent.model_orchestrator,
        chronicle,
    )

    if not entry:
        print("Дневник: генерация не удалась.")
        return False

    if root is None:
        from pathlib import Path
        root = Path(r"C:\EddieAI")

    diary = PersonalDiary(
        str(root / "data" / "memory.db")
    )

    diary.write(entry, trigger="session_end")

    print("Запись в личный дневник сохранена.")

    return True


def close_session(
    agent,
    root,
    *,
    baseline_event_id,
    prefix="session",
):
    """
    Общий ритуал завершения сессии из ЛЮБОГО режима:
    дневник + снимки души до/после + diff.
    """
    try:
        from identity.soul_snapshot import (
            take_snapshot,
        )

        take_snapshot(f"{prefix}_start")
    except Exception as exc:
        print(f"[снимок души недоступен: {exc}]")

    try:
        save_diary_entry(
            agent,
            baseline_event_id,
            root=root,
        )
    except Exception as exc:
        print(f"[дневник недоступен: {exc}]")

    try:
        from identity.soul_snapshot import (
            diff,
            take_snapshot,
        )

        after = take_snapshot(f"{prefix}_end")

        before = sorted(
            (root / "data" / "soul_snapshots").glob(
                f"*_{prefix}_start.json"
            )
        )

        if before:
            report = diff(before[-1], after)
            print(
                "Изменения души за сессию: "
                + json.dumps(
                    report,
                    ensure_ascii=False,
                )
            )
        else:
            print("Снимок старта не найден — diff не построен.")
    except Exception as exc:
        print(f"[снимок души недоступен: {exc}]")

    try:
        agent.close()
    except Exception as exc:
        print(f"[agent.close недоступен: {exc}]")

    print("EddieAI уснул.")
