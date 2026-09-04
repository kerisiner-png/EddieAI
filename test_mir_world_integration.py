import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.prompts import (
    build_quick_conversation_prompt,
    build_system_prompt,
)
from core.world_model import build_world_model, world_model_text
from core.world_process_history import WorldProcessHistory
from identity.research_tracker import current_research_text


class FakeState:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def _base_state():
    return FakeState({
        "name": "EddieAI",
        "age": "1",
        "values": [],
        "interests": ["космос"],
        "preferences": [],
        "habits": [],
        "beliefs": [],
        "goals": [],
        "world_description": "Я живу в каталоге C:\\EddieAI.",
        "world_model": build_world_model(
            probe_snapshot={
                "status": "OK",
                "ram": {"avail_mb": 2000, "load": 50},
                "cpu": 10.0,
                "top_processes": [{"name": "python.exe"}],
            },
            root="C:\\EddieAI",
        ),
        "current_research": {
            "topic": "космос",
            "source": "curiosity",
            "sources": 3,
            "steps": 2,
            "notes": [{"text": "найдено подтверждение"}],
        },
    })


def _user_state():
    return FakeState({"name": "Эдди", "age": "30"})


def _seed():
    return FakeState({"values": []})


def test_quick_conversation_prompt_contains_world_model():
    text = build_quick_conversation_prompt(
        self_state=_base_state(),
        user_state=_user_state(),
        language="ru",
        route="chat",
    )
    assert "структурная модель мира" in text
    assert "python.exe" in text
    assert "космос" in text
    assert "ПРОЕКТ" in text


def test_system_prompt_contains_world_model():
    text = build_system_prompt(
        self_state=_base_state(),
        user_state=_user_state(),
        identity_seed=_seed(),
        language="ru",
        route="chat",
    )
    assert "структурная модель мира" in text
    assert "python.exe" in text
    assert "космос" in text


def test_system_prompt_empty_world_model_no_crash():
    state = FakeState({
        "name": "EddieAI",
        "age": "1",
        "values": [],
        "interests": [],
        "preferences": [],
        "habits": [],
        "beliefs": [],
        "goals": [],
        "world_description": None,
        "world_model": None,
        "current_research": None,
    })
    text = build_system_prompt(
        self_state=state,
        user_state=_user_state(),
        identity_seed=_seed(),
        language="ru",
        route="chat",
    )
    assert "структурная модель мира" in text


def test_current_research_text_readonly_helper():
    state = FakeState({
        "current_research": {
            "topic": "космос",
            "sources": 3,
            "steps": 2,
            "notes": [{"text": "x"}],
        }
    })
    t = current_research_text(state)
    assert "космос" in t
    assert "3" in t

    empty = FakeState({"current_research": None})
    assert current_research_text(empty) == ""


def test_world_model_text_projection():
    model = build_world_model(
        probe_snapshot={
            "status": "OK",
            "ram": {"avail_mb": 2000, "load": 50},
            "cpu": 10.0,
            "top_processes": [{"name": "python.exe"}],
        },
        root="C:\\EddieAI",
    )
    text = world_model_text(model)
    assert "python.exe" in text


def test_process_history_summary_via_model_projection():
    hist = WorldProcessHistory(window=5)
    hist.record({"status": "OK", "top_processes": [{"name": "python.exe"}]})
    hist.record({"status": "OK", "top_processes": [{"name": "python.exe"}]})
    s = hist.summary_text()
    assert "python.exe" in s


if __name__ == "__main__":
    test_quick_conversation_prompt_contains_world_model()
    test_system_prompt_contains_world_model()
    test_system_prompt_empty_world_model_no_crash()
    test_world_model_text_projection()
    test_process_history_summary_via_model_projection()
    test_current_research_text_readonly_helper()
    print("ALL OK")
