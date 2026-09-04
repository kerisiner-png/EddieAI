from pathlib import Path
from tempfile import TemporaryDirectory

from core.autonomous_runtime import AutonomousRuntime
from identity.self_state import SelfState


class FakeLifecycle:
    def __init__(self):
        self.promoted = []

    def promote(
        self,
        field,
        value,
        strength,
        confidence,
        evidence_count,
    ):
        self.promoted.append(
            {
                "field": field,
                "value": value,
                "strength": strength,
                "confidence": confidence,
                "evidence_count": evidence_count,
            }
        )


class FakeAgent:
    def __init__(self, lifecycle):
        self.personality_lifecycle = lifecycle


def _runtime():
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt.agent = FakeAgent(FakeLifecycle())
    return rt


def test_promotable_candidate_is_promoted():
    rt = _runtime()
    result = rt._apply_consolidation(
        [
            {
                "status": "PROMOTABLE",
                "field": "interest",
                "value": "космос",
                "strength": 0.8,
                "confidence": 0.85,
                "evidence_count": 5,
            }
        ]
    )
    assert result[0]["status"] == "PROMOTED"
    assert rt.agent.personality_lifecycle.promoted
    assert (
        rt.agent.personality_lifecycle.promoted[0]["value"]
        == "космос"
    )


def test_waiting_candidate_not_promoted():
    rt = _runtime()
    result = rt._apply_consolidation(
        [
            {
                "status": "WAITING",
                "field": "interest",
                "value": "физика",
            }
        ]
    )
    assert result[0]["status"] == "WAITING"
    assert rt.agent.personality_lifecycle.promoted == []


def test_no_lifecycle_returns_unchanged():
    rt = _runtime()
    rt.agent.personality_lifecycle = None
    data = [
        {
            "status": "PROMOTABLE",
            "field": "interest",
            "value": "химия",
        }
    ]
    result = rt._apply_consolidation(data)
    assert result == data


def test_empty_consolidation_returns_empty():
    rt = _runtime()
    assert rt._apply_consolidation([]) == []
    assert rt._apply_consolidation(None) is None