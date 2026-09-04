from identity.shared_activity_commands import (
    parse_activity_command,
)


def test_start_movie_command():
    cmd = parse_activity_command(
        "давай посмотрим Интерстеллар"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "movie"
    assert cmd["title"] == "Интерстеллар"


def test_start_music_command():
    cmd = parse_activity_command(
        "включи музыку"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "music"


def test_start_game_command():
    cmd = parse_activity_command(
        "давай поиграем в шахматы"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "game"


def test_start_coding_command():
    cmd = parse_activity_command(
        "поработаем над проектом"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "coding"


def test_start_reading_command():
    cmd = parse_activity_command(
        "давай почитаем"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "reading"


def test_start_conversation_command():
    cmd = parse_activity_command(
        "давай поболтаем"
    )
    assert cmd is not None
    assert cmd["kind"] == "start"
    assert cmd["activity_type"] == "conversation"


def test_stop_command():
    cmd = parse_activity_command(
        "выключи, хватит на сегодня"
    )
    assert cmd is not None
    assert cmd["kind"] == "stop"


def test_plain_message_returns_none():
    assert (
        parse_activity_command("как дела?") is None
    )
    assert (
        parse_activity_command("привет") is None
    )


def test_film_synonym():
    cmd = parse_activity_command(
        "включи кино"
    )
    assert cmd is not None
    assert cmd["activity_type"] == "movie"


def test_title_extraction_keeps_words():
    cmd = parse_activity_command(
        "запусти фильм Простые истины"
    )
    assert cmd["title"] == "Простые истины"