from pathlib import Path
from tempfile import TemporaryDirectory

from identity.conscious_observer import (
    ConsciousObserver,
    conscious_state_text,
    conscious_state_summary_text,
)
from identity.personal_diary import PersonalDiary
from identity.self_state import SelfState


class FakeAffective:
    def snapshot(self):
        return {"valence": 0.6, "energy": 0.4}


class FakeGoals:
    def active(self):
        return ["изучить космос", "написать отчёт"]


class FakeMemory:
    def __init__(self, db_path):
        self.db_path = str(db_path)

    def recent_life_feed(self, limit=3):
        return "Изучал космос. Думал о памяти."

    def remember(self, event):
        self.store.append(event)

    store = []


class FakeAgent:
    def __init__(self, state, memory):
        self.self_state = state
        self.affective_state = FakeAffective()
        self.goal_manager = FakeGoals()
        self.memory = memory


def _make():
    temp = TemporaryDirectory()
    state = SelfState(Path(temp.name) / "cs.json")
    memory = FakeMemory(temp.name)
    agent = FakeAgent(state, memory)
    diary = PersonalDiary(Path(temp.name) / "diary.db")
    return temp, state, memory, agent, diary


def test_observe_collects_full_state():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    snapshot = obs.observe()
    assert snapshot["observed_at"]
    assert snapshot["affect"]["valence"] == 0.6
    assert "космос" in snapshot["active_focus"]["goals"][0]
    assert isinstance(snapshot["self_model"], dict)


def test_observe_reads_diary_and_feed():
    temp, state, memory, agent, diary = _make()
    diary.write("Сегодня я изучал звёзды.", trigger="test")
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    snapshot = obs.observe()
    assert "звёзды" in snapshot["recent_diary"]
    assert "памят" in snapshot["recent_feed"], (
        repr(snapshot["recent_feed"])
    )


def test_ask_affect_marker():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    answer = obs.ask("как моё настроение и эмоции?").lower()
    assert "настроение" in answer or "эмоци" in answer or "аффект" in answer


def test_ask_capability_marker():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    answer = obs.ask("что я умею?").lower()
    assert "умею" in answer or "способности" in answer


def test_ask_general_fallback():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    answer = obs.ask("расскажи о себе").lower()
    assert "состояние" in answer or "сознания" in answer


def test_render_non_empty():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    text = obs.render_consciousness()
    assert "СОСТОЯНИЕ СОЗНАНИЯ" in text


def test_no_data_fallback_no_crash():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=None)
    snapshot = obs.observe()
    assert snapshot["affect"] == {}
    assert snapshot["recent_diary"] == ""
    assert snapshot["recent_feed"] == ""
    assert obs.render_consciousness()


def test_history_writes_and_reads():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    obs.observe()
    hist = obs.history()
    assert len(hist) == 2


def test_self_state_persisted():
    temp, state, memory, agent, diary = _make()
    obs = ConsciousObserver(state, agent=agent, db_path=diary.db_path)
    obs.observe()
    assert state.get("conscious_state") is not None


def test_conscious_state_text_helper():
    temp, state, memory, agent, diary = _make()
    assert conscious_state_text(state) == ""
    ConsciousObserver(state, agent=agent).observe()
    assert "СОСТОЯНИЕ СОЗНАНИЯ" in conscious_state_text(state)


def test_conscious_state_summary_helper():
    temp, state, memory, agent, diary = _make()
    assert conscious_state_summary_text(state) == ""
    ConsciousObserver(state, agent=agent).observe()
    text = conscious_state_summary_text(state)
    assert "аффект" in text
    assert "космос" in text


def _built_conscious():
    temp, state, memory, agent, diary = _make()
    ConsciousObserver(
        state,
        agent=agent,
        db_path=diary.db_path,
    ).observe()
    return state.get("conscious_state")


def _prompt_state():
    return _PromptState({
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
        "self_model": {
            "capabilities": [
                {
                    "name": "research",
                    "description": "",
                }
            ]
        },
        "conscious_state": _built_conscious(),
    })


class _PromptState:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def _user_state():
    return _PromptState({
        "name": "Эдди",
        "age": "30",
    })


def _seed():
    return _PromptState({"values": []})


def test_quick_prompt_contains_conscious_block():
    from core.prompts import (
        build_quick_conversation_prompt,
    )
    text = build_quick_conversation_prompt(
        self_state=_prompt_state(),
        user_state=_user_state(),
        language="ru",
        route="chat",
    )
    assert "СОСТОЯНИЕ СОЗНАНИЯ" in text


def test_system_prompt_contains_conscious_bullet():
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
    assert "осознанное состояние" in text


def test_prompts_fallback_when_no_conscious():
    from core.prompts import (
        build_quick_conversation_prompt,
        build_system_prompt,
    )
    empty = _PromptState({
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
        "conscious_state": None,
    })
    quick = build_quick_conversation_prompt(
        self_state=empty,
        user_state=_user_state(),
        language="ru",
        route="chat",
    )
    assert "самонаблюдение ещё не проведено" in quick

    system = build_system_prompt(
        self_state=empty,
        user_state=_user_state(),
        identity_seed=_seed(),
        language="ru",
        route="chat",
    )
    assert "самонаблюдение ещё не проведено" in system


if __name__ == "__main__":
    test_observe_collects_full_state()
    test_observe_reads_diary_and_feed()
    test_ask_affect_marker()
    test_ask_capability_marker()
    test_ask_general_fallback()
    test_render_non_empty()
    test_no_data_fallback_no_crash()
    test_history_writes_and_reads()
    test_self_state_persisted()
    test_conscious_state_text_helper()
    test_conscious_state_summary_helper()
    test_quick_prompt_contains_conscious_block()
    test_system_prompt_contains_conscious_bullet()
    test_prompts_fallback_when_no_conscious()
    print("ALL OK")
