import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\EddieAI")
DATA = ROOT / "data"
SNAP_DIR = DATA / "soul_snapshots"

COUNTERS = [
    "events",
    "evidence_events",
    "knowledge",
    "personality_history",
    "self_proposals",
    "diary",
]


def take_snapshot(label):
    SNAP_DIR.mkdir(
        parents=True, exist_ok=True
    )

    stamp = datetime.now(timezone.utc)
    name = stamp.strftime("%Y%m%d_%H%M%S")

    soul = json.loads(
        (DATA / "self_state.json").read_text(
            encoding="utf-8"
        )
    )

    counters = {}

    db_path = DATA / "memory.db"

    if db_path.exists():
        import sqlite3

        conn = sqlite3.connect(str(db_path))

        for table in COUNTERS:
            try:
                counters[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            except Exception:
                counters[table] = None

        conn.close()

    snapshot = {
        "label": label,
        "ts": stamp.isoformat(),
        "soul": soul,
        "counters": counters,
    }

    out = SNAP_DIR / f"{name}_{label}.json"

    out.write_text(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"snapshot_saved: {out.name}")

    return out


def diff(before_path, after_path):
    before = json.loads(
        Path(before_path).read_text(
            encoding="utf-8"
        )
    )

    after = json.loads(
        Path(after_path).read_text(
            encoding="utf-8"
        )
    )

    report = {
        "counters": {},
        "soul_fields": [],
    }

    for table, n_after in after[
        "counters"
    ].items():
        n_before = before["counters"].get(
            table
        )

        if n_before != n_after:
            report["counters"][table] = (
                f"{n_before} -> {n_after}"
            )

    b_soul = before["soul"]
    a_soul = after["soul"]

    for field in set(b_soul) | set(a_soul):
        if (
            field == "emotional_state"
            or field.endswith("_applied")
            or field.endswith("_provenance")
        ):
            continue

        if b_soul.get(field) != a_soul.get(
            field
        ):
            report["soul_fields"].append(
                field
            )

    return report


if __name__ == "__main__":
    label = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "manual"
    )

    take_snapshot(label)
