import numpy as np


def _fake_voice():
    from communication.voice_io import VoiceIO

    v = VoiceIO.__new__(VoiceIO)
    v._stream_on_phrase = None
    v._stream_last_emitted = ""
    return v


def test_emit_text_forwards_speaker_to_callback():
    v = _fake_voice()
    got = []
    v._stream_on_phrase = lambda text, speaker=None: got.append(
        (text, speaker)
    )
    v._emit_text("привет", "Eddie")
    assert got == [("привет", "Eddie")]


def test_emit_text_speaker_defaults_none():
    v = _fake_voice()
    got = []
    v._stream_on_phrase = lambda text, speaker=None: got.append(
        (text, speaker)
    )
    v._emit_text("привет")
    assert got == [("привет", None)]


def test_emit_text_skips_empty():
    v = _fake_voice()
    got = []
    v._stream_on_phrase = lambda text, speaker=None: got.append(
        (text, speaker)
    )
    v._emit_text("")
    assert got == []


def test_emit_text_skips_duplicate():
    v = _fake_voice()
    got = []
    v._stream_on_phrase = lambda text, speaker=None: got.append(
        (text, speaker)
    )
    v._emit_text("дубль", "Eddie")
    v._emit_text("дубль", "Eddie")
    assert got == [("дубль", "Eddie")]


def test_identify_speaker_unknown_when_no_profiles(tmp_path):
    from communication.voice_io import VoiceIO
    from identity.speaker_id import SpeakerIdentifier

    v = VoiceIO.__new__(VoiceIO)
    v._speaker_id = SpeakerIdentifier(
        profiles_path=str(tmp_path / "p.json"),
        embed_fn=lambda s, r: np.zeros(8, dtype=np.float32)
        if len(s) else None,
    )
    tone = np.sin(
        np.linspace(0, 50, 16000) * 0.1
    ).astype(np.float32)
    assert v._identify_speaker(tone) is None


def test_identify_speaker_eddie_when_profile_matches(tmp_path):
    from communication.voice_io import VoiceIO
    from identity.speaker_id import SpeakerIdentifier

    def emb(s, r):
        if len(s) > 8000:
            return np.array([1.0, 0.0], dtype=np.float32)
        return np.zeros(2, dtype=np.float32)

    v = VoiceIO.__new__(VoiceIO)
    v._speaker_id = SpeakerIdentifier(
        profiles_path=str(tmp_path / "p.json"),
        embed_fn=emb,
        threshold=0.5,
    )
    v._speaker_id.enroll(
        "Eddie", np.zeros(16000, dtype=np.float32)
    )
    assert (
        v._identify_speaker(
            np.zeros(16000, dtype=np.float32)
        )
        == "Eddie"
    )


def test_on_phrase_unknown_speaker_not_sent():
    from communication.chat_app import _is_accepted_speaker

    assert _is_accepted_speaker(None) is True
    assert _is_accepted_speaker("Eddie") is True
    assert _is_accepted_speaker("Other") is False