from identity.inner_stream import (
    InnerStream,
    Mood,
    affect_energy,
    affect_valence,
    mood_label,
)


def test_valence_positive_vs_negative():
    positive = {"joy": 0.5}
    negative = {"frustration": 0.6}

    assert (
        affect_valence(positive) > 0
    )
    assert (
        affect_valence(negative) < 0
    )


def test_energy_curiosity_raises():
    assert (
        affect_energy({"curiosity": 0.8})
        > affect_energy({"sadness": 0.8})
    )


def test_mood_labels():
    assert mood_label(-0.6, 0.2) == "мрачно"
    assert (
        mood_label(-0.6, 0.8) == "раздражённо"
    )
    assert (
        mood_label(0.6, 0.7) == "оживлённо"
    )
    assert (
        mood_label(0.6, 0.1) == "тепло и вяло"
    )
    assert mood_label(0.0, 0.3) == "ровно"
    assert (
        mood_label(0.0, 0.8)
        == "настороженно-бодро"
    )


class _State:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def test_mood_drifts_toward_affect():
    state = _State()
    mood = Mood(state)

    mood.update(
        {"joy": 0.8}, 1000.0
    )
    early = mood.snapshot()

    mood.update(
        {"joy": 0.8}, 1000.0 + 3600 * 6
    )
    late = mood.snapshot()

    assert early["valence"] <= late["valence"]
    assert late["valence"] > 0.2
    assert "mood_state" in state._data


def test_mood_persists_and_restores():
    state = _State()
    mood = Mood(state)
    mood.update({"joy": 0.9}, 1000.0)

    restored = Mood(state)

    assert (
        abs(
            restored.valence
            - mood.valence
        )
        < 0.05
    )


def test_stream_urgency_accumulates():
    stream = InnerStream()

    stream.add("sense", "экран сменился", 1.0, 1000.0)
    stream.add("hear", "речь из видео", 1.2, 1020.0)
    stream.add("message", "привет", 1.5, 1040.0)

    assert stream.urgency(1041.0) >= 3.0


def test_stream_decay_lowers_urgency():
    stream = InnerStream()

    stream.add("sense", "событие", 2.0, 1000.0)
    high = stream.urgency(1010.0)

    low = stream.urgency(
        1000.0 + 3600 * 2
    )

    assert high > 0
    assert low < high


def test_should_speak_threshold_and_interval():
    stream = InnerStream(
        speak_threshold=3.0,
        speak_min_interval=900.0,
    )

    stream.add("sense", "событие", 5.0, 1000.0)
    assert (
        stream.should_speak(1001.0) is True
    )

    stream.mark_spoke(1001.0)
    assert (
        stream.should_speak(1100.0) is False
    )
    assert (
        stream.should_speak(2000.0) is False
    )

    stream.add("message", "новое", 5.0, 2100.0)
    assert (
        stream.should_speak(2101.0) is True
    )


def test_note_event_dedupes_same_key():
    stream = InnerStream()

    assert (
        stream.note_event(
            "sense", "yt-видео", "описание", 1.0, 1000.0
        )
        is True
    )
    assert (
        stream.note_event(
            "sense", "yt-видео", "описание", 1.0, 1010.0
        )
        is False
    )
    assert (
        stream.note_event(
            "sense", "vscode", "другое", 1.0, 1020.0
        )
        is True
    )


def test_render_context_lines():
    stream = InnerStream()
    stream.add("sense", "экран: youtube", 1.0, 1000.0)
    stream.add("message", "привет", 1.0, 1010.0)

    rendered = stream.render_context()

    assert "экран: youtube" in rendered
    assert "привет" in rendered


def test_compose_micro_thought_priority():
    from identity.inner_stream import (
        compose_micro_thought,
    )

    assert "вспоминаю" in (
        compose_micro_thought(
            {
                "memory_line": "утром изучал волны",
                "goal": "дело",
            }
        )
    )
    assert "Эдди нет" in (
        compose_micro_thought(
            {
                "minutes_since_contact": 45,
                "goal": "дело",
            }
        )
    )
    assert "продолжаю" in (
        compose_micro_thought(
            {"goal": "изучить космос"}
        )
    )
    assert "настроение" in (
        compose_micro_thought({"mood": "ровно"})
    )
    assert (
        compose_micro_thought({}) is None
    )


def test_think_rhythm_gate_and_weight():
    from identity.inner_stream import (
        InnerStream,
        ThinkRhythm,
    )

    stream = InnerStream()
    rhythm = ThinkRhythm(
        think_interval=180.0, weight=0.2
    )

    first = rhythm.maybe_think(
        stream,
        1000.0,
        {"mood": "ровно"},
    )
    assert first is not None
    before = stream.urgency(1000.0)

    again = rhythm.maybe_think(
        stream,
        1100.0,
        {"mood": "ровно"},
    )
    assert again is None

    third = rhythm.maybe_think(
        stream,
        1200.0,
        {"mood": "ровно"},
    )
    assert third is not None
    assert (
        stream.urgency(1200.0) > before
    )
