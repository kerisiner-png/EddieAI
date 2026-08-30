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


def _remember(agent, content, event_type, source_type="TOOL"):
    agent.memory.remember(
        Event.create(
            content=content,
            event_type=event_type,
            source_type=source_type,
            source="tool",
            personal_experience=True,
            confidence=1.0,
            verified=True,
        )
    )


def _make_agent():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    _remember(
        agent,
        "Инструмент web выполнил действие 'Старый поиск'. "
        "Найдено 3 результатов: - старая тема (http://old)",
        "TOOL_RESULT",
    )
    _remember(
        agent,
        "Я самостоятельно выполнил действие 'Старый поиск' "
        "через инструмент web. Статус: OK.",
        "SELF_EXPERIENCE",
    )
    _remember(
        agent,
        "Инструмент research выполнил действие 'Свежие данные'. "
        "Найдено 5 результатов: - связь интересна (http://new)",
        "TOOL_RESULT",
    )
    agent.self_state = FakeSelfState({"life_state": {"asleep": False}})
    agent.life_cycle = None
    return agent


def test_action_results_block_present():
    agent = _make_agent()
    block = agent._action_results_block(limit=4)
    assert "РЕЗУЛЬТАТЫ ТВОИХ ДЕЙСТВИЙ" in block
    assert "связь интересна" in block
    assert "Свежие данные" in block
    assert "Старый поиск" in block
    assert "Статус: OK" not in block


def test_action_results_block_limit():
    agent = _make_agent()
    block = agent._action_results_block(limit=1)
    assert "Свежие данные" in block
    assert "Старый поиск" not in block


def test_action_results_block_empty_memory():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    assert agent._action_results_block() == ""


def test_action_results_block_no_memory():
    agent = object.__new__(Agent)
    agent.memory = None
    assert agent._action_results_block() == ""


def test_recent_action_results_api():
    agent = _make_agent()
    feed = agent.memory.recent_action_results(limit=10)
    assert "связь интересна" in feed
    assert "Статус: OK" not in feed
    assert len(feed.splitlines()) == 2


def test_recent_action_results_excludes_self_output():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    _remember(
        agent,
        "Инструмент web выполнил действие 'Вывод'. "
        "Найдено 2 результатов.",
        "TOOL_RESULT",
        source_type="SELF_OUTPUT",
    )
    feed = agent.memory.recent_action_results(limit=4)
    assert feed == ""


if __name__ == "__main__":
    test_action_results_block_present()
    test_action_results_block_limit()
    test_action_results_block_empty_memory()
    test_action_results_block_no_memory()
    test_recent_action_results_api()
    test_recent_action_results_excludes_self_output()
    print("ALL OK")