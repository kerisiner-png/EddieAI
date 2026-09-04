import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory.database import Memory
from memory.evidence import EvidenceEngine
from memory.events import Event
from identity.action_preference_detector import ActionPreferenceDetector


def _action_payload(context, options, selected):
    return json.dumps(
        {"choice": {
            "context_type": context,
            "options": options,
            "selected": selected,
        }},
        ensure_ascii=False,
    )


def test_preference_detector_lower_threshold(tmpdir):
    db = Path(tmpdir) / "pref_test.db"
    memory = Memory(db)
    try:
        evidence = EvidenceEngine(memory)
        detector = ActionPreferenceDetector(memory, evidence)

        # 3 повтора "read" + 1 "walk" (4 выбора, share 0.75, реальное
        # сравнение) — при смягчённом MIN_CHOICES=4 ожидается предпочтение.
        for sel in ["read", "read", "read", "walk"]:
            memory.remember(Event.create(
                content=_action_payload("break", ["read", "walk"], sel),
                event_type="ACTION_CHOICE",
                source_type="SELF_ACTION",
                personal_experience=True,
            ))

        results = detector.detect()

        assert results, "при смягчённом MIN_CHOICES ожидается предпочтение"
        assert results[0]["category"] == "preference"
        assert results[0]["value"] == "break:action_method:read"
        assert results[0]["selected"] == "read"
        assert results[0]["total_choices"] == 4
        assert results[0]["created_evidence"] == 3
    finally:
        memory.close()


def test_preference_requires_clear_majority(tmpdir):
    db = Path(tmpdir) / "pref_majority.db"
    memory = Memory(db)
    try:
        evidence = EvidenceEngine(memory)
        detector = ActionPreferenceDetector(memory, evidence)

        # 2/2 — явного большинства нет (share 0.5 < 0.75) → не предпочтение.
        for sel in ["read", "read", "walk", "walk"]:
            memory.remember(Event.create(
                content=_action_payload("break", ["read", "walk"], sel),
                event_type="ACTION_CHOICE",
                source_type="SELF_ACTION",
                personal_experience=True,
            ))

        results = detector.detect()
        assert results == []
    finally:
        memory.close()


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="pref_test_")
    test_preference_detector_lower_threshold(tmpdir)
    test_preference_requires_clear_majority(tmpdir)
    print("ALL OK")
