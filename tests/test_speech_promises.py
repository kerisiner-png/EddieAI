from identity.speech_promises import (
    detect_promises,
    has_recent_evidence,
    promise_goal_value,
    strip_unmapped_promises,
    strip_unverified_past_claims,
)


def test_detect_promise_with_capability():
    found = detect_promises(
        "Ок, запускаю видео, а дальше посмотрим."
    )
    assert found, found
    assert found[0]["verb"] == "запуск"
    assert found[0]["capability"] == "programs"


def test_promise_goal_value_extracts_object():
    value = promise_goal_value(
        "запуск",
        "Ок, запускаю видео про котиков, погнали.",
    )
    assert "видео" in value
    assert value.startswith("запустить")


def test_strip_unmapped_promise():
    text = strip_unmapped_promises(
        "Ну что, сделаю тебе сайт с нуля, конечно."
    )
    assert "сделаю" not in text
    assert "сайт" not in text


def test_mapped_promise_is_kept():
    text = strip_unmapped_promises(
        "Ок, запускаю видео."
    )
    assert "запускаю видео" in text


def test_past_claim_with_evidence_kept():
    text = "Я уже запустил видео."
    recent = [
        "Я самостоятельно выполнил действие "
        "'Запустить видео' через инструмент programs."
    ]
    assert (
        strip_unverified_past_claims(text, recent)
        == text
    )


def test_past_claim_without_evidence_stripped():
    text = (
        "Я уже запустил видео. Что смотрим дальше?"
    )
    cleaned = strip_unverified_past_claims(
        text, []
    )
    assert "запустил" not in cleaned
    assert "Что смотрим дальше?" in cleaned


def test_no_past_claim_no_change():
    text = "Просто болтаю без заявлений."
    assert (
        strip_unverified_past_claims(text, [])
        == text
    )


def test_evidence_stem_match():
    import re

    from identity.speech_promises import (
        PAST_CLAIM_RE,
    )

    match = PAST_CLAIM_RE.search("я уже запустил")

    assert has_recent_evidence(
        match,
        ["TOOL_RESULT: запустил видео для Эдди"],
    )


if __name__ == "__main__":
    test_detect_promise_with_capability()
    test_promise_goal_value_extracts_object()
    test_strip_unmapped_promise()
    test_mapped_promise_is_kept()
    test_past_claim_with_evidence_kept()
    test_past_claim_without_evidence_stripped()
    test_no_past_claim_no_change()
    test_evidence_stem_match()
    print("ALL OK")
