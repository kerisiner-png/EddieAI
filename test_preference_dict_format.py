import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory.database import Memory
from memory.evidence import EvidenceEngine
from memory.events import Event
from identity.action_preference_detector import ActionPreferenceDetector
from identity.identity_manager import IdentityManager
from identity.preference_label import preference_label, format_preferences
from identity.proposal import Proposal
from identity.self_state import SelfState


def _action_payload(context, options, selected, task=None):
    choice = {
        "context_type": context,
        "options": options,
        "selected": selected,
    }
    if task:
        choice["task"] = task
    return json.dumps(
        {"choice": choice},
        ensure_ascii=False,
    )


def _fill_choices(memory, task=None):
    for sel in ["read", "read", "read", "walk"]:
        memory.remember(Event.create(
            content=_action_payload(
                "break", ["read", "walk"], sel, task=task,
            ),
            event_type="ACTION_CHOICE",
            source_type="SELF_ACTION",
            personal_experience=True,
        ))


def test_detector_meta_present(tmpdir):
    db = Path(tmpdir) / "meta.db"
    memory = Memory(db)
    try:
        evidence = EvidenceEngine(memory)
        detector = ActionPreferenceDetector(memory, evidence)
        _fill_choices(memory, task="почитать книгу")

        results = detector.detect()

        assert results
        item = results[0]
        assert item["meta"]["context"] == "break"
        assert item["meta"]["method"] == "read"
        assert item["meta"]["share"] == 0.75
        assert item["meta"]["total"] == 4
        assert item["meta"]["task"] == "почитать книгу"
    finally:
        memory.close()


def test_identity_manager_writes_dict(tmpdir):
    db = Path(tmpdir) / "manager.db"
    memory = Memory(db)
    state = SelfState(Path(tmpdir) / "self.json")
    try:
        manager = IdentityManager(state, memory)

        proposal = Proposal(
            proposal_type="preference",
            value="break:action_method:read",
            reason="test",
            confidence=1.0,
            evidence=[],
            evidence_count=3,
            meta={
                "context": "break",
                "method": "read",
                "share": 0.75,
                "total": 4,
                "task": "почитать книгу",
            },
        )

        status = manager.evaluate(proposal)

        assert status == "accepted"
        prefs = state.get("preferences")
        assert len(prefs) == 1
        entry = prefs[0]
        assert isinstance(entry, dict)
        assert entry["context"] == "break"
        assert entry["method"] == "read"
        assert entry["share"] == 0.75
        assert entry["total"] == 4
        label = entry.get("label")
        assert label and label != "break:action_method:read"
        assert "почитать книгу" in label or "read" in label
        assert entry.get("source") == "ACTION_CHOICE"
        assert entry.get("ts")
    finally:
        memory.close()


def test_identity_manager_dedup_by_method(tmpdir):
    db = Path(tmpdir) / "dedup.db"
    memory = Memory(db)
    state = SelfState(Path(tmpdir) / "dedup_self.json")
    try:
        manager = IdentityManager(state, memory)

        def _mk():
            return Proposal(
                proposal_type="preference",
                value="break:action_method:read",
                reason="test",
                confidence=1.0,
                evidence=[],
                evidence_count=3,
                meta={
                    "context": "break",
                    "method": "read",
                    "share": 0.75,
                    "total": 4,
                    "task": "книга",
                },
            )

        assert manager.evaluate(_mk()) == "accepted"
        assert manager.evaluate(_mk()) == "already_present"
        assert len(state.get("preferences")) == 1
    finally:
        memory.close()


def test_identity_manager_keeps_plain_strings(tmpdir):
    db = Path(tmpdir) / "plain.db"
    memory = Memory(db)
    state = SelfState(Path(tmpdir) / "plain_self.json")
    try:
        manager = IdentityManager(state, memory)
        # Пропозиция без meta (обычный LLM-клейм) — остаётся строкой.
        proposal = Proposal(
            proposal_type="preference",
            value="люблю читать в тишине",
            reason="test",
            confidence=1.0,
            evidence=[],
            evidence_count=1,
        )
        status = manager.evaluate(proposal)
        assert status == "accepted"
        prefs = state.get("preferences")
        assert len(prefs) == 1
        assert prefs[0] == "люблю читать в тишине"
    finally:
        memory.close()


def test_preference_label_dict_and_str():
    d = format_preferences([
        {"label": "книга",
         "context": "break", "method": "read"},
        "research:action_method:RESEARCH",
    ])
    assert d[0] == "книга"
    assert d[1] == "research:action_method:RESEARCH"

    # dict без label — фолбэк-шаблон.
    assert preference_label(
        {"context": "break", "method": "read"}
    ).startswith("в контексте")


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="pref_dict_")
    test_detector_meta_present(tmpdir)
    test_identity_manager_writes_dict(tmpdir)
    test_identity_manager_dedup_by_method(tmpdir)
    test_identity_manager_keeps_plain_strings(tmpdir)
    test_preference_label_dict_and_str()
    print("ALL OK")
