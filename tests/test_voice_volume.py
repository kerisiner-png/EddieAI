import numpy as np


def _tone(freq_hz, rate=22050, seconds=1.0, amp=0.1):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def test_normalize_volume_raises_to_target_rms():
    from voice_repl import normalize_volume

    pcm = _tone(180, amp=0.05)
    out = normalize_volume(pcm, target_rms=0.25, peak_limit=0.95)
    rms = float(np.sqrt((out**2).mean()))
    assert abs(rms - 0.25) < 0.01
    assert float(np.abs(out).max()) <= 0.96


def test_normalize_volume_respects_peak_limit():
    from voice_repl import normalize_volume

    pcm = _tone(180, amp=0.2)
    pcm[0 : 100] = 2.0
    out = normalize_volume(pcm, target_rms=0.3, peak_limit=0.9)
    assert float(np.abs(out).max()) <= 0.91


def test_normalize_volume_does_not_clip_quiet():
    from voice_repl import normalize_volume

    pcm = _tone(180, amp=0.5)
    out = normalize_volume(pcm, target_rms=0.1, peak_limit=0.95)
    rms = float(np.sqrt((out**2).mean()))
    assert 0.05 < rms <= 0.11


def test_equalize_keeps_low_frequency_energy():
    from voice_repl import equalize

    low = _tone(400, amp=0.5)
    out = equalize(low, 22050)
    rms_out = float(np.sqrt((out**2).mean()))
    assert rms_out > 0.01