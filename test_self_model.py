from pathlib import Path
from tempfile import TemporaryDirectory

from identity.self_model import (
    SelfModel,
    self_model_text,
)
from identity.self_state import SelfState
from identity.tool_registry import ToolRegistry


def _registry():
    reg = ToolRegistry()
    reg.register("research", object(), "внешний поиск", enabled=True)
    reg.register("filesystem", object(), "чтение и запись файлов", enabled=True)
    reg.register("vision", object(), "зрение", enabled=False)
    return reg


class FakeAgent:
    def __init__(self, state):
        self.self_state = state
        self.goal_manager = _FakeGoals()


class _FakeGoals:
    def active(self):
        return [object(), object()]


def _make():
    temp = TemporaryDirectory()
    state = SelfState(Path(temp.name) / "sm.json")
    return temp, state


def test_build_creates_full_model():
    temp, state = _make()
    agent = FakeAgent(state)
    reg = _registry()
    model = SelfModel(state)
    built = model.build(reg.describe(), agent=agent)
    assert built["identity"]["entity"] == "EddieAI"
    assert built["identity"]["mission_code"] == "exist_and_develop"
    names = {
        c["name"] for c in built["capabilities"]
    }
    assert "research" in names
    assert len(built["capabilities"]) == 2  # vision выключен -> не способность
    assert built["current_state"]["age"] == state.get("age")
    assert built["current_state"]["active_goals_count"] == 2


def test_disabled_tools_become_limitations():
    temp, state = _make()
    model = SelfModel(state)
    built = model.build(_registry().describe())
    ids = [
        l["id"] for l in built["limitations"]
    ]
    assert "tool_disabled:vision" in ids


def test_limitations_include_known_contour_facts():
    temp, state = _make()
    model = SelfModel(state)
    built = model.build(_registry().describe())
    scopes = [
        l["scope"] for l in built["limitations"]
    ]
    assert "perceptual" in scopes


def test_snapshot_returns_model():
    temp, state = _make()
    model = SelfModel(state)
    model.build(_registry().describe())
    snap = model.snapshot()
    assert isinstance(snap, dict)
    assert "capabilities" in snap


def test_render_non_empty():
    temp, state = _make()
    model = SelfModel(state)
    model.build(_registry().describe())
    text = model.render()
    assert "СПОСОБНОСТИ" in text
    assert "research" in text or "filesystem" in text


def test_render_empty_when_not_built():
    temp, state = _make()
    model = SelfModel(state)
    # не собран -> пустая строка (местоположение для промпта)
    assert model.render() == ""


def test_get_returns_persisted():
    temp, state = _make()
    model = SelfModel(state)
    built = model.build(_registry().describe())
    got = model.get()
    assert got == built


def test_self_model_text_helper():
    temp, state = _make()
    assert self_model_text(state) == ""
    SelfModel(state).build(_registry().describe())
    assert "СПОСОБНОСТИ" in self_model_text(state)


class FakeState:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def _built_model_dict():
    temp, state = _make()
    SelfModel(state).build(_registry().describe())
    return state.get("self_model")


def _prompt_state():
    return FakeState({
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
        "self_model": _built_model_dict(),
    })


def _user_state():
    return FakeState({"name": "Эдди", "age": "30"})


def _seed():
    return FakeState({"values": []})


def test_quick_prompt_contains_self_model_block():
    from core.prompts import (
        build_quick_conversation_prompt,
    )
    text = build_quick_conversation_prompt(
        self_state=_prompt_state(),
        user_state=_user_state(),
        language="ru",
        route="chat",
    )
    assert "СПОСОБНОСТИ И ОГРАНИЧЕНИЯ" in text
    assert "research" in text


def test_system_prompt_contains_self_model_bullet():
    from core.prompts import (
        build_system_prompt,
    )
    text = build_system_prompt(
        self_state=_prompt_state(),
        user_state=_user_state(),
        identity_seed=_seed(),
        language="ru",
        route="chat",
    )
    assert "самооценка" in text
    assert "research" in text


def test_prompts_fallback_when_no_self_model():
    from core.prompts import (
        build_quick_conversation_prompt,
        build_system_prompt,
    )
    empty = FakeState({
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
        "self_model": None,
    })
    quick = build_quick_conversation_prompt(
        self_state=empty,
        user_state=_user_state(),
        language="ru",
        route="chat",
    )
    assert "модель себя ещё не собрана" in quick

    system = build_system_prompt(
        self_state=empty,
        user_state=_user_state(),
        identity_seed=_seed(),
        language="ru",
        route="chat",
    )
    assert "модель себя ещё не собрана" in system


if __name__ == "__main__":
    test_build_creates_full_model()
    test_disabled_tools_become_limitations()
    test_limitations_include_known_contour_facts()
    test_snapshot_returns_model()
    test_render_non_empty()
    test_render_empty_when_not_built()
    test_get_returns_persisted()
    test_self_model_text_helper()
    test_quick_prompt_contains_self_model_block()
    test_system_prompt_contains_self_model_bullet()
    test_prompts_fallback_when_no_self_model()
    print("ALL OK")
