from core import prompt_builder
from core.prompt_builder import (
    VERBALIZER_BASE,
    VERBALIZER_PERSISTENT_SUFFIX,
    build_repair_prompt,
    build_verbalizer_system_prompt,
)


import re


def _norm(text):
    return re.sub(r"\s+", " ", text).casefold()


def test_verbalizer_base_has_no_hard_shortness_cap():
    assert "1–3" not in VERBALIZER_BASE
    assert "МАКСИМУМ 4" not in VERBALIZER_BASE


def test_verbalizer_base_mentions_living_conversation():
    lowered = _norm(VERBALIZER_BASE)
    assert "живой беседе" in lowered


def test_verbalizer_base_allows_topic_development():
    lowered = _norm(VERBALIZER_BASE)
    assert "развивай тему" in lowered
    assert "встречный вопрос" in lowered


def test_persistent_suffix_allows_unfolding():
    lowered = _norm(VERBALIZER_PERSISTENT_SUFFIX)
    assert "живыми словами" in lowered
    assert "развернуть" in lowered


def test_repair_prompt_allows_questions():
    prompt = build_repair_prompt(
        answer="Тест.",
        mode="NEUTRAL",
        primary="Отвечай естественно.",
        avoid="Будь кратким.",
        violations_text="Нет.",
        language="русский",
    )
    assert "Никаких предложений помощи" not in prompt


def test_repair_prompt_has_liveliness_mandate():
    prompt = build_repair_prompt(
        answer="Тест.",
        mode="NEUTRAL",
        primary="Отвечай естественно.",
        avoid="Будь кратким.",
        violations_text="Нет.",
        language="русский",
    )
    assert "живой реплики" in prompt


def test_neutral_contract_does_not_forbid_initiative():
    policy = _neutral_policy()

    neutral = policy.behavior_contract(
        message="",
        route=None,
    )

    avoid = " ".join(
        neutral.get("avoid", [])
    ).lower()

    assert "искусственную инициативу" not in avoid

    primary = " ".join(
        neutral.get("primary", [])
    ).lower()

    assert "живой" in primary


class _FakeAffectiveState:
    def snapshot(self):
        return {
            "emotions": {
                "curiosity": 0.2,
                "frustration": 0.1,
                "sadness": 0.1,
                "fear": 0.1,
                "anger": 0.1,
                "interest": 0.2,
                "surprise": 0.1,
            },
            "behavior": {},
        }


def _neutral_policy():
    from identity.affective_dialogue_policy import (
        AffectiveDialoguePolicy,
    )

    return AffectiveDialoguePolicy(
        _FakeAffectiveState()
    )


def test_repair_unsupported_self_claim_keeps_interest():
    from core.identity_repair import (
        IdentityRepairStrategy,
    )

    repairer = IdentityRepairStrategy.__new__(
        IdentityRepairStrategy
    )

    answer = (
        "Мне интересна астрофизика, "
        "я хочу разобраться в ней глубже."
    )

    result = (
        repairer._repair_unsupported_self_claim(
            answer
        )
    )

    assert "астрофизика" in result


def test_repair_unsupported_self_claim_still_blocks_fact_claim():
    from core.identity_repair import (
        IdentityRepairStrategy,
    )

    repairer = IdentityRepairStrategy.__new__(
        IdentityRepairStrategy
    )

    result = (
        repairer._repair_unsupported_self_claim(
            "Люблю сериал «Офис»."
        )
    )

    assert "пока нет" in result