import math

import numpy as np


def _tone(freq, seconds=1.5, rate=16000):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    return 0.3 * np.sin(2 * math.pi * freq * t).astype(np.float32)


def _fft_embed(pcm, rate):
    n = 512
    seg = pcm[: len(pcm) - (len(pcm) % n)]
    if len(seg) < n:
        seg = np.resize(seg, n)
    spec = np.abs(np.fft.rfft(seg[:n])).astype(np.float32)
    spec /= (spec.sum() + 1e-9)
    return spec


def _make_identifier(tmp_path):
    from identity.speaker_id import SpeakerIdentifier

    return SpeakerIdentifier(
        profiles_path=str(tmp_path / "profiles.json"),
        embed_fn=lambda pcm, rate: _fft_embed(pcm, rate),
        threshold=0.85,
    )


def test_enroll_and_identify_eddie(tmp_path):
    ident = _make_identifier(tmp_path)
    ok = ident.enroll("Eddie", _tone(200))
    assert ok is True
    assert ident.identify(_tone(200)) == "Eddie"


def test_identify_unknown_voice_returns_none(tmp_path):
    ident = _make_identifier(tmp_path)
    ident.enroll("Eddie", _tone(200))
    assert ident.identify(_tone(800)) is None


def test_no_profiles_returns_none(tmp_path):
    ident = _make_identifier(tmp_path)
    assert ident.identify(_tone(200)) is None


def test_enroll_missing_extractor_returns_false(tmp_path):
    from identity.speaker_id import SpeakerIdentifier

    ident = SpeakerIdentifier(
        profiles_path=str(tmp_path / "profiles.json"),
        embed_fn=None,
    )
    assert ident.enroll("Eddie", _tone(200)) is False


def test_profiles_persist_across_instances(tmp_path):
    ident1 = _make_identifier(tmp_path)
    ident1.enroll("Eddie", _tone(200))
    ident2 = _make_identifier(tmp_path)
    assert ident2.identify(_tone(200)) == "Eddie"


def test_identify_after_clear_returns_none(tmp_path):
    ident = _make_identifier(tmp_path)
    ident.enroll("Eddie", _tone(200))
    ident.clear()
    assert ident.identify(_tone(200)) is None


def test_profiles_json_contains_eddie_after_enroll(tmp_path):
    ident = _make_identifier(tmp_path)
    ident.enroll("Eddie", _tone(200))
    import json

    data = json.loads(
        (tmp_path / "profiles.json").read_text(encoding="utf-8")
    )
    assert "Eddie" in data


def _synth_piper(text, voice_path):
    from piper import PiperVoice
    import numpy as np

    pcm = []
    for chunk in PiperVoice.load(voice_path).synthesize(text):
        pcm.append(chunk.audio_float_array)
    return np.concatenate(pcm).astype(np.float32)


def _real_identifier(tmp_path, threshold=0.5):
    from identity.speaker_id import (
        SpeakerIdentifier,
        make_sherpa_embed_fn,
    )

    return SpeakerIdentifier(
        profiles_path=str(tmp_path / "profiles.json"),
        embed_fn=make_sherpa_embed_fn(
            r"C:\EddieAI\models\speaker"
            r"\3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
            num_threads=2,
        ),
        threshold=threshold,
    )


def test_real_speakers_eddie_vs_other(tmp_path):
    dmitri = _synth_piper(
        "Привет Эдди, это я, твой голосовой хозяин.",
        r"C:\EddieAI\models\piper\ru_RU-dmitri-medium.onnx",
    )
    irina = _synth_piper(
        "Привет Эдди, это я, твой голосовой хозяин.",
        r"C:\EddieAI\models\piper\ru_RU-irina-medium.onnx",
    )
    assert len(dmitri) > 16000
    assert len(irina) > 16000

    ident = _real_identifier(tmp_path)
    assert ident.enroll("Eddie", dmitri[:16000]) is True
    assert ident.identify(dmitri[8000:24000]) == "Eddie"
    assert ident.identify(irina[8000:24000]) is None