from core.power_mode import (
    PowerMode,
    read_power_status,
)


def _provider(sequence):
    calls = {"i": 0}

    def provider():
        i = calls["i"]
        calls["i"] += 1
        return sequence[min(i, len(sequence) - 1)]

    return provider


ONLINE = {
    "known": True,
    "ac_online": True,
    "has_battery": True,
    "percent": 80,
}
OFFLINE_60 = {
    "known": True,
    "ac_online": False,
    "has_battery": True,
    "percent": 60,
}
OFFLINE_10 = {
    "known": True,
    "ac_online": False,
    "has_battery": True,
    "percent": 10,
}
OFFLINE_5 = {
    "known": True,
    "ac_online": False,
    "has_battery": True,
    "percent": 5,
}


def test_online_stays_normal():
    mode = PowerMode(
        status_provider=_provider([ONLINE])
    )
    assert mode.poll(1000.0) is None
    assert mode.mode == "normal"
    assert mode.on_battery() is False


def test_power_loss_announces_save_once():
    mode = PowerMode(
        status_provider=_provider(
            [ONLINE, OFFLINE_60, OFFLINE_60]
        )
    )
    mode.poll(1000.0)

    transition = mode.poll(1010.0)
    assert transition["to"] == "save"
    assert transition["percent"] == 60

    assert mode.poll(1020.0) is None


def test_ac_back_announces_normal():
    mode = PowerMode(
        status_provider=_provider(
            [ONLINE, OFFLINE_60, ONLINE]
        )
    )
    mode.poll(1000.0)
    mode.poll(1010.0)

    transition = mode.poll(1020.0)

    assert transition["to"] == "normal"
    assert mode.on_battery() is False


def test_low_battery_goes_critical():
    mode = PowerMode(
        status_provider=_provider(
            [OFFLINE_60, OFFLINE_10, OFFLINE_5]
        )
    )
    mode.poll(1000.0)

    transition = mode.poll(1010.0)
    assert transition["to"] == "critical"
    assert mode.on_battery() is True

    assert mode.poll(1020.0) is None


def test_start_on_battery_announces_save():
    mode = PowerMode(
        status_provider=_provider([OFFLINE_60])
    )
    transition = mode.poll(1000.0)

    assert transition is not None
    assert transition["to"] == "save"


def test_read_status_returns_dict():
    status = read_power_status()
    assert isinstance(status, dict)
    assert "known" in status
