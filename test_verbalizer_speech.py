from core.prompt_builder import (
    build_verbalizer_system_prompt,
)


base = build_verbalizer_system_prompt()

assert "РЕЧЕВОЙ ПОЧЕРК" not in base, (
    "без профиля блок речи не должен добавляться"
)

empty = build_verbalizer_system_prompt(
    speech_profile={
        "favorite_words": [],
        "filler_words": [],
    },
)

assert "РЕЧЕВОЙ ПОЧЕРК" not in empty, (
    "пустой профиль не должен добавлять блок"
)

with_profile = build_verbalizer_system_prompt(
    speech_profile={
        "favorite_words": ["космос", "звёзды"],
        "filler_words": ["ну", "вот"],
    },
)

assert "РЕЧЕВОЙ ПОЧЕРК" in with_profile
assert "космос" in with_profile
assert "звёзды" in with_profile
assert "ну" in with_profile
assert "вот" in with_profile

assert "РЕЧЕВОЙ ПОЧЕРК" in build_verbalizer_system_prompt(
    speech_profile={
        "favorite_words": [],
        "filler_words": ["кстати"],
    },
), "только слова-паразиты тоже включают блок"

persistent = build_verbalizer_system_prompt(
    persistent_conclusion=True,
    speech_profile={
        "favorite_words": ["космос"],
        "filler_words": [],
    },
)

assert "РЕЧЕВОЙ ПОЧЕРК" in persistent
assert "ДОПОЛНИТЕЛЬНО" in persistent, (
    "persistent-суффикс должен сохраняться"
)

print("ALL PASS")
