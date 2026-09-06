import time

from identity.body import (
    Body,
    novelty_label,
    social_label,
)


class _State:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def test_social_need_grows_with_time():
    state = _State()
    body = Body(state)

    body.update(1000.0, seconds_since_contact=0.0)
    assert body.social_need == 0.0

    body.update(
        1000.0 + 3600, seconds_since_contact=3600.0
    )
    assert 0.3 <= body.social_need <= 0.4


def test_social_need_saturates():
    state = _State()
    body = Body(state)

    body.update(
        1000.0,
        seconds_since_contact=10 * 3600,
    )
    assert body.social_need == 1.0
    assert (
        social_label(body.social_need)
        == "скучаю по Эдди"
    )


def test_satisfy_social_resets():
    state = _State()
    body = Body(state)
    body.update(
        1000.0,
        seconds_since_contact=10 * 3600,
    )

    body.satisfy_social(now=1001.0)

    assert body.social_need == 0.0
    assert (
        social_label(body.social_need)
        == "сыт общением"
    )


def test_novelty_from_screen_staleness():
    state = _State()
    body = Body(state)

    body.update(1000.0, screen_stale_sec=0.0)
    assert body.novelty_need == 0.0

    body.update(
        1000.0 + 3600, screen_stale_sec=3600.0
    )
    assert body.novelty_need >= 0.4
    assert (
        novelty_label(body.novelty_need)
        == "хочется чего-то нового"
    )


def test_urgency_contribution():
    state = _State()
    body = Body(state)
    body.update(
        1000.0,
        seconds_since_contact=10 * 3600,
        screen_stale_sec=10 * 3600,
    )

    assert (
        body.urgency_contribution() == 3.0
    )


def test_body_persists():
    state = _State()
    body = Body(state)
    body.update(
        1000.0,
        seconds_since_contact=3600.0,
    )

    restored = Body(state)

    assert (
        abs(
            restored.social_need
            - body.social_need
        )
        < 0.01
    )


def test_body_state_snapshot_labels():
    state = _State()
    body = Body(state)
    body.update(
        1000.0,
        seconds_since_contact=2.0 * 3600,
    )

    snap = body.snapshot()

    assert snap["social_label"] == (
        "хочется болтать"
    )


if __name__ == "__main__":
    test_social_need_grows_with_time()
    test_social_need_saturates()
    test_satisfy_social_resets()
    test_novelty_from_screen_staleness()
    test_urgency_contribution()
    test_body_persists()
    test_body_state_snapshot_labels()
    print("ALL OK")
