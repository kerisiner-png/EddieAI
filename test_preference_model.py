from pathlib import Path
from tempfile import TemporaryDirectory

from identity.identity_manager import IdentityManager
from identity.preference_label import preference_label
from identity.preference_model import (
    enrich_entry,
    entry_strength,
    entry_type,
    format_preferences_rich,
    preference_conflicts,
    preference_type,
    strength_of,
)
from identity.proposal import Proposal
from identity.self_state import SelfState


class _NoopMemory:
    def remember_proposal(self, **kwargs):
        pass


def test_preference_type_action_context():
    assert preference_type("read", "activity") == "action"
    assert preference_type("walk", "move") == "action"


def test_preference_type_topic_method():
    assert preference_type("изучение космоса", "unknown") == "topic"


def test_enrich_entry_adds_fields():
    entry = enrich_entry(
        {
            "label": "книга",
            "context": "activity",
            "method": "read",
            "share": 0.8,
            "total": 5,
            "evidence_count": 6,
        },
        source="ACTION_CHOICE",
    )
    assert entry["type"] == "action"
    assert 0.0 <= entry["strength"] <= 1.0
    assert entry["provenance"] == "ACTION_CHOICE"
    assert entry["first_seen_ts"]
    assert entry["last_seen_ts"]
    assert entry["first_seen_ts"] == entry["last_seen_ts"]


def test_enrich_entry_back_compat_minimal():
    entry = enrich_entry(
        {"label": "книга", "method": "read"}
    )
    assert entry["type"] in {
        "action",
        "topic",
        "environment",
        "unknown",
    }
    assert 0.0 <= entry["strength"] <= 1.0
    assert entry["provenance"]


def test_accessors_defaults():
    assert entry_type({}) == "unknown"
    assert entry_type("plain string") == "unknown"
    assert 0.0 <= entry_strength({}) <= 1.0
    assert 0.0 <= entry_strength("plain") <= 1.0


def test_strength_of_blends_share_and_evidence():
    s_high = strength_of(
        {"share": 1.0, "evidence_count": 20}
    )
    s_low = strength_of(
        {"share": 0.1, "evidence_count": 0}
    )
    assert s_high > s_low


def test_conflict_detected_on_negation_same_topic():
    prefs = [
        {
            "label": "не люблю читать про космос",
            "context": "unknown",
            "method": "избегаю чтения про космос",
        }
    ]
    conflicts = preference_conflicts(
        prefs,
        ["космос"],
    )
    assert conflicts
    assert conflicts[0]["interest"] == "космос"


def test_no_conflict_without_negative_marker():
    prefs = [
        {
            "label": "люблю читать",
            "context": "unknown",
            "method": "чтение",
        }
    ]
    conflicts = preference_conflicts(prefs, ["космос"])
    assert conflicts == []


def test_format_rich_dict_and_str():
    items = [
        {
            "label": "читаю о космосе",
            "context": "unknown",
            "method": "изучение космоса",
            "share": 0.8,
        },
        "research:action_method:RESEARCH",
    ]
    out = format_preferences_rich(items)
    assert "читаю о космосе" in out[0]
    assert "тип" in out[0] or "сила" in out[0]
    assert out[1] == "research:action_method:RESEARCH"


def test_format_rich_conflict_hint():
    prefs = [
        {
            "label": "не люблю читать про космос",
            "context": "unknown",
            "method": "избегаю про космос",
            "share": 0.9,
        }
    ]
    out = format_preferences_rich(prefs, ["космос"])
    assert any("конфликт" in line for line in out)


def test_identity_manager_writes_enriched_dict(tmpdir):
    db = Path(tmpdir)
    memory = _NoopMemory()
    state = SelfState(db / "self.json")
    manager = IdentityManager(state, memory)
    proposal = Proposal(
        proposal_type="preference",
        value="unknown:action_method:read",
        reason="test",
        confidence=1.0,
        evidence=[],
        evidence_count=3,
        meta={
            "context": "activity",
            "method": "read",
            "share": 0.75,
            "total": 4,
            "task": "почитать книгу",
        },
    )
    status = manager.evaluate(proposal)
    assert status == "accepted"
    entry = state.get("preferences")[0]
    assert entry["type"] == "action"
    assert 0.0 <= entry["strength"] <= 1.0
    assert entry["provenance"] == "ACTION_CHOICE"


def test_identity_manager_dedup_updates_last_seen(tmpdir):
    db = Path(tmpdir)
    memory = _NoopMemory()
    state = SelfState(db / "dedup_self.json")
    manager = IdentityManager(state, memory)

    def _mk():
        return Proposal(
            proposal_type="preference",
            value="unknown:action_method:read",
            reason="test",
            confidence=1.0,
            evidence=[],
            evidence_count=3,
            meta={
                "context": "activity",
                "method": "read",
                "share": 0.75,
                "total": 4,
                "task": "почитать книгу",
            },
        )

    assert manager.evaluate(_mk()) == "accepted"
    assert manager.evaluate(_mk()) == "already_present"
    prefs = state.get("preferences")
    assert len(prefs) == 1
    first = prefs[0]["first_seen_ts"]
    last = prefs[0]["last_seen_ts"]
    assert first and last


if __name__ == "__main__":
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="pref_model_")
    test_preference_type_action_context()
    test_preference_type_topic_method()
    test_enrich_entry_adds_fields()
    test_enrich_entry_back_compat_minimal()
    test_accessors_defaults()
    test_strength_of_blends_share_and_evidence()
    test_conflict_detected_on_negation_same_topic()
    test_no_conflict_without_negative_marker()
    test_format_rich_dict_and_str()
    test_format_rich_conflict_hint()
    test_identity_manager_writes_enriched_dict(tmpdir)
    test_identity_manager_dedup_updates_last_seen(tmpdir)
    print("ALL OK")
