import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.agent import Agent
from memory.database import Memory
from memory.events import Event


class FakeSelfState:
    def __init__(self, value):
        self._v = value

    def get(self, key, default=None):
        return self._v.get(key, default)


def _make_agent_with_feed():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    agent.memory.remember(
        Event.create(
            content="Я проснулся после сна",
            event_type="LIFE_CYCLE",
            source_type="SELF_OBSERVATION",
            source="self",
            personal_experience=True,
            confidence=1.0,
            verified=True,
            interpretation="сон",
        )
    )
    agent.self_state = FakeSelfState({
        "life_state": {"asleep": False},
    })
    agent.life_cycle = None
    return agent


def test_life_feed_block_present():
    agent = _make_agent_with_feed()
    block = agent._life_feed_block(limit=5)
    assert "НЕДАВНИЕ СОБЫТИЯ ТВОЕЙ ЖИЗНИ" in block
    assert "Я проснулся после сна" in block


def test_life_feed_block_empty_memory():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    assert agent._life_feed_block() == ""


def test_life_feed_block_no_memory():
    agent = object.__new__(Agent)
    agent.memory = None
    assert agent._life_feed_block() == ""


def test_self_context_has_life_state():
    agent = _make_agent_with_feed()
    ctx = agent._self_context_block()
    assert "бодрствую" in ctx
    assert "SELF CONTEXT" in ctx


if __name__ == "__main__":
    test_life_feed_block_present()
    test_life_feed_block_empty_memory()
    test_life_feed_block_no_memory()
    test_self_context_has_life_state()
    print("ALL OK")