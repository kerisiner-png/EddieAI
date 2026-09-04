from unittest.mock import patch

from status_overlay import build_status


@patch("status_overlay._read_json")
def test_asleep_status(mock_read):
    mock_read.side_effect = [
        {"state": "IDLE", "asleep": True},
        {"state": "IDLE"},
        {
            "life_state": {
                "asleep": True,
                "fatigue": 0.95,
            },
            "goals_state": {},
        },
    ]
    st = build_status()
    assert st["main"] == "СПИТ"
    assert st["color"] == "#3344cc"
    assert st["fatigue"] == 95


@patch("status_overlay._read_json")
def test_working_status(mock_read):
    mock_read.side_effect = [
        {"state": "ACTING", "asleep": False},
        {"state": "ACTING"},
        {
            "life_state": {"asleep": False},
            "goals_state": {
                "g1": {
                    "status": "ACTIVE",
                    "value": "исследовать космос",
                }
            },
        },
    ]
    st = build_status()
    assert st["main"] == "РАБОТАЕТ"
    assert st["detail"] == "исследовать космос"


@patch("status_overlay._read_json")
def test_idle_with_research(mock_read):
    mock_read.side_effect = [
        {"state": "IDLE", "asleep": False},
        {"state": "IDLE"},
        {
            "life_state": {"asleep": False},
            "goals_state": {},
            "current_research": {
                "topic": "чёрные дыры"
            },
        },
    ]
    st = build_status()
    assert st["main"] == "БОДРСТВУЕТ"
    assert "чёрные дыры" in st["detail"]


@patch("status_overlay._read_json")
def test_missing_files_fallback(mock_read):
    mock_read.side_effect = [None, None, None]
    st = build_status()
    assert st["main"] == "БОДРСТВУЕТ"