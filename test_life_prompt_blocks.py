import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.prompts import (
    build_system_prompt,
    build_quick_conversation_prompt,
)


class FakeState:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


FULL_STATE = FakeState({
    "name": "EddieAI",
    "age": 1,
    "interests": [],
    "preferences": [],
    "habits": [],
    "beliefs": [],
    "goals": [],
    "personality_traits": {},
    "mission_statement": "Быть и развиваться",
    "relationships": {},
})

USER_STATE = FakeState({"name": "Эдди"})


def test_full_prompt_contains_life_blocks():
    prompt = build_system_prompt(
        self_state=FULL_STATE,
        user_state=USER_STATE,
        identity_seed={"values": []},
        language="ru",
        route="default",
    )
    assert "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" in prompt
    assert "ТВОЯ ВОЛЯ" in prompt


def test_quick_prompt_contains_life_blocks():
    prompt = build_quick_conversation_prompt(
        self_state=FULL_STATE,
        user_state=USER_STATE,
        language="ru",
        route="default",
    )
    assert "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" in prompt
    assert "ТВОЯ ВОЛЯ" in prompt


def test_route_variants_contain_life_blocks():
    for route in ("MEMORY_QUERY", "USER_QUERY", "SELF_QUERY", "default"):
        prompt = build_system_prompt(
            self_state=FULL_STATE,
            user_state=USER_STATE,
            identity_seed={"values": []},
            language="ru",
            route=route,
        )
        assert "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" in prompt, route
        assert "ТВОЯ ВОЛЯ" in prompt, route


if __name__ == "__main__":
    test_full_prompt_contains_life_blocks()
    test_quick_prompt_contains_life_blocks()
    test_route_variants_contain_life_blocks()
    print("ALL OK")