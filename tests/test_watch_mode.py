import time

from identity.watch_mode import (
    WatchMode,
    looks_like_video_title,
)


def test_video_title_markers():
    assert (
        looks_like_video_title(
            "(555) CEHR смотрит базу — YouTube"
        )
        is True
    )
    assert (
        looks_like_video_title(
            "agent.py - Visual Studio Code"
        )
        is False
    )
    assert looks_like_video_title("") is False


def test_self_enter_requires_sustained_title():
    wm = WatchMode()
    t0 = 1000.0

    assert (
        wm.maybe_enter(t0, "видео — YouTube")
        is False
    )
    assert (
        wm.maybe_enter(t0 + 30, "видео — YouTube")
        is False
    )
    assert (
        wm.maybe_enter(t0 + 61, "видео — YouTube")
        is True
    )
    assert wm.active is True
    assert wm.source == "self"


def test_enter_resets_on_non_video_title():
    wm = WatchMode()
    t0 = 1000.0

    wm.maybe_enter(t0, "видео — YouTube")
    wm.maybe_enter(
        t0 + 30, "agent.py — VS Code"
    )
    assert (
        wm.maybe_enter(t0 + 61, "видео — YouTube")
        is False
    )


def test_exit_after_quiet():
    wm = WatchMode(exit_quiet_sec=300.0)
    wm.force_enter(1000.0, "eddie")
    wm.note_motion(1100.0)
    wm.note_audio(1150.0)

    assert (
        wm.maybe_exit(1400.0) is False
    )
    assert wm.maybe_exit(1500.0) is True
    assert wm.active is False


def test_audio_keeps_mode_alive():
    wm = WatchMode(exit_quiet_sec=300.0)
    wm.force_enter(1000.0, "self")
    wm.note_motion(1000.0)
    wm.note_audio(1350.0)

    assert (
        wm.maybe_exit(1400.0) is False
    )


def test_comment_cadence():
    wm = WatchMode(comment_interval=600.0)
    wm.force_enter(1000.0, "self")

    assert (
        wm.should_comment(1200.0) is False
    )
    assert (
        wm.should_comment(1601.0) is True
    )
    wm.mark_commented(1601.0)
    assert (
        wm.should_comment(1700.0) is False
    )


def test_force_exit_from_eddie_command():
    wm = WatchMode()
    wm.force_enter(1000.0, "eddie")
    wm.force_exit(1010.0)
    assert wm.active is False


if __name__ == "__main__":
    test_video_title_markers()
    test_self_enter_requires_sustained_title()
    test_enter_resets_on_non_video_title()
    test_exit_after_quiet()
    test_audio_keeps_mode_alive()
    test_comment_cadence()
    test_force_exit_from_eddie_command()
    print("ALL OK")
