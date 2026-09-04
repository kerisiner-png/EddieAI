from identity.shared_activity_manager import (
    SharedActivityManager,
    ACTIVITY_TYPES,
    MOOD_ACTIVITY_MAP,
)


def test_start_and_stop_activity():
    mgr = SharedActivityManager()
    result = mgr.start_activity("movie", "Интерстеллар")
    assert result["type"] == "movie"
    assert result["title"] == "Интерстеллар"
    assert result["status"] == "active"
    assert mgr.is_active()
    ended = mgr.stop_activity()
    assert ended["status"] == "ended"
    assert ended["end_reason"] == "user"
    assert not mgr.is_active()


def test_invalid_type_becomes_other():
    mgr = SharedActivityManager()
    result = mgr.start_activity("dancing")
    assert result["type"] == "other"


def test_get_current_returns_active():
    mgr = SharedActivityManager()
    assert mgr.get_current() is None
    mgr.start_activity("game")
    current = mgr.get_current()
    assert current is not None
    assert current["type"] == "game"


def test_stop_returns_none_when_no_activity():
    mgr = SharedActivityManager()
    assert mgr.stop_activity() is None


def test_activity_summary_no_activity():
    mgr = SharedActivityManager()
    assert "нет" in mgr.activity_summary()


def test_activity_summary_with_activity():
    mgr = SharedActivityManager()
    mgr.start_activity("music", "Плейлист")
    summary = mgr.activity_summary()
    assert "music" in summary
    assert "Плейлист" in summary


def test_persistence_via_self_state():
    state = {}
    mgr1 = SharedActivityManager(self_state=state)
    mgr1.start_activity("coding", "Проект EddieAI")
    assert state["current_shared_activity"]["status"] == "active"
    mgr2 = SharedActivityManager(self_state=state)
    assert mgr2.is_active()
    assert mgr2.get_current()["title"] == "Проект EddieAI"


def test_stop_clears_self_state():
    state = {}
    mgr = SharedActivityManager(self_state=state)
    mgr.start_activity("movie")
    mgr.stop_activity()
    assert "current_shared_activity" not in state


def test_suggest_activity_by_mood():
    class FakeAffective:
        emotions = {"joy": 0.5, "curiosity": 0.1}
    mgr = SharedActivityManager()
    suggestion = mgr.suggest_activity(
        affective_state=FakeAffective()
    )
    assert suggestion is not None
    assert suggestion["activity_type"] in ("movie", "music", "game")


def test_suggest_activity_by_interest():
    mgr = SharedActivityManager()
    suggestion = mgr.suggest_activity(
        interests=[{"name": "астрофизика"}]
    )
    assert suggestion is not None
    assert suggestion["activity_type"] == "reading"


def test_suggest_activity_dampens_recent():
    mgr = SharedActivityManager()
    suggestion = mgr.suggest_activity(
        interests=[{"name": "космос"}],
        recent_history=[
            {"activity_type": "reading"},
            {"activity_type": "reading"},
        ],
    )
    assert suggestion is not None
    reading_score = suggestion["reason_score"]
    suggestion_no_history = mgr.suggest_activity(
        interests=[{"name": "космос"}]
    )
    assert suggestion_no_history["reason_score"] >= reading_score


def test_suggest_returns_none_when_no_signals():
    mgr = SharedActivityManager()
    assert mgr.suggest_activity() is None


def test_start_activity_source_default():
    mgr = SharedActivityManager()
    result = mgr.start_activity("movie")
    assert result["source"] == "chat"


def test_start_activity_custom_source():
    mgr = SharedActivityManager()
    result = mgr.start_activity(
        "game", source="initiative"
    )
    assert result["source"] == "initiative"
