from pathlib import Path
from tempfile import TemporaryDirectory

from core.agent_loop import AgentLoop
from identity.self_state import SelfState
from memory.database import Memory
from memory.evidence import EvidenceEngine


def _make_loop(temp):
    memory = Memory(Path(temp) / "memory.db")
    evidence = EvidenceEngine(memory)
    loop = AgentLoop.__new__(AgentLoop)
    loop.evidence = evidence
    loop.memory = memory
    return loop, memory, evidence


def test_reflection_signals_become_evidence():
    with TemporaryDirectory() as temp:
        loop, memory, evidence = _make_loop(temp)
        try:
            reflection = {
                "status": "OK",
                "signals": [
                    {
                        "category": "interest",
                        "value": "астрофизика",
                        "confidence": 0.6,
                    },
                    {
                        "category": "preference",
                        "value": "исследование через research",
                        "confidence": 0.5,
                    },
                ],
            }
            loop._apply_reflection_signals(
                reflection, "изучить тему: космос"
            )
            rec = evidence.get("interest", "астрофизика")
            assert rec.count == 1
            assert "SELF_INTERPRETATION" in rec.source_types
            rec2 = evidence.get(
                "preference",
                "исследование через research",
            )
            assert rec2.count == 1
        finally:
            memory.close()


def test_reflection_no_signals_no_evidence():
    with TemporaryDirectory() as temp:
        loop, memory, evidence = _make_loop(temp)
        try:
            reflection = {
                "status": "OK",
                "signals": [],
            }
            loop._apply_reflection_signals(
                reflection, "изучить тему: космос"
            )
            rows = memory.connection.execute(
                "SELECT COUNT(*) AS c FROM evidence_events"
            ).fetchone()
            assert rows["c"] == 0
        finally:
            memory.close()


def test_reflection_signals_require_valid_category():
    with TemporaryDirectory() as temp:
        loop, memory, evidence = _make_loop(temp)
        try:
            reflection = {
                "status": "OK",
                "signals": [
                    {
                        "category": "whatever",
                        "value": "тест",
                        "confidence": 0.9,
                    }
                ],
            }
            loop._apply_reflection_signals(
                reflection, "цель"
            )
            rows = memory.connection.execute(
                "SELECT COUNT(*) AS c FROM evidence_events"
            ).fetchone()
            assert rows["c"] == 0
        finally:
            memory.close()


def test_reflection_signals_idempotent_per_goal():
    with TemporaryDirectory() as temp:
        loop, memory, evidence = _make_loop(temp)
        try:
            reflection = {
                "status": "OK",
                "signals": [
                    {
                        "category": "interest",
                        "value": "физика",
                        "confidence": 0.6,
                    }
                ],
            }
            loop._apply_reflection_signals(
                reflection, "изучить тему: физика"
            )
            loop._apply_reflection_signals(
                reflection, "изучить тему: физика"
            )
            rec = evidence.get("interest", "физика")
            assert rec.count == 1
        finally:
            memory.close()