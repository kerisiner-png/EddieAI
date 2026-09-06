import numpy as np

from identity.pc_audio_listener import (
    pick_device_index,
    pick_loopback_device,
    rms_level,
    should_store,
    text_worth_storing,
)


def test_text_needs_enough_words():
    assert text_worth_storing("") is False
    assert text_worth_storing("музыка") is False
    assert (
        text_worth_storing(
            "добро пожаловать на борт корабля"
        )
        is True
    )


def test_should_store_respects_cooldown():
    assert (
        should_store(
            now=100.0, last_ts=40.0, cooldown=45.0
        )
        is True
    )
    assert (
        should_store(
            now=100.0, last_ts=80.0, cooldown=45.0
        )
        is False
    )


def test_rms_level_distinguishes_silence():
    silence = np.zeros(4000, dtype=np.float32)
    loud = (
        np.sin(
            np.linspace(0, 400, 4000)
        ).astype(np.float32)
        * 0.5
    )
    assert rms_level(silence) == 0.0
    assert rms_level(loud) > 0.01


def test_pick_device_by_candidate_name():
    devices = [
        {"name": "Microphone", "max_input_channels": 1},
        {
            "name": "Voicemeeter Out B1 (VB-Audio)",
            "max_input_channels": 8,
        },
        {"name": "Headset", "max_input_channels": 1},
    ]
    assert pick_device_index(devices) == 1


def test_pick_device_none_when_absent():
    devices = [
        {"name": "Microphone", "max_input_channels": 1},
    ]
    assert pick_device_index(devices) is None


def test_pick_loopback_by_default_output_name():
    devices = [
        {
            "name": "Headphones (2- MAJOR V) [Loopback]",
            "isLoopbackDevice": 1,
        },
        {
            "name": "Voicemeeter Out A4 [Loopback]",
            "isLoopbackDevice": 1,
        },
    ]
    assert (
        pick_loopback_device(
            devices, "Headphones (2- MAJOR V)"
        )
        == 0
    )


def test_pick_loopback_by_prefix_fallback():
    devices = [
        {
            "name": "Speakers [Loopback]",
            "isLoopbackDevice": 1,
        },
    ]
    assert (
        pick_loopback_device(
            devices,
            "Speakers (Realtek High Definition)",
        )
        == 0
    )


def test_pick_loopback_none_without_match():
    devices = [
        {
            "name": "Voicemeeter Out A4 [Loopback]",
            "isLoopbackDevice": 1,
        },
    ]
    assert (
        pick_loopback_device(
            devices, "Headphones (2- MAJOR V)"
        )
        is None
    )


if __name__ == "__main__":
    test_text_needs_enough_words()
    test_should_store_respects_cooldown()
    test_rms_level_distinguishes_silence()
    test_pick_device_by_candidate_name()
    test_pick_device_none_when_absent()
    print("ALL OK")
