from unittest.mock import MagicMock

from memory.events import Event


def test_observe_returns_dict():
    from identity.shared_life import SharedLife
    sl = SharedLife.__new__(SharedLife)
    sl._orchestrator = MagicMock()
    sl._orchestrator.execute.return_value = {"text": "YES: Эдди смотрит видео"}
    sl._memory = MagicMock()
    sl._retrieval = MagicMock()
    result = sl.observe("YouTube open, video playing", eddie_present=True)
    assert isinstance(result, dict)
    assert "is_shared" in result
    assert "description" in result


def test_record_creates_event():
    from identity.shared_life import SharedLife
    sl = SharedLife.__new__(SharedLife)
    sl._memory = MagicMock()
    sl._retrieval = MagicMock()
    sl.record("Смотрели фильм вместе", activity_type="movie", mood="joy")
    sl._memory.remember.assert_called_once()
    call_args = sl._memory.remember.call_args[0][0]
    assert isinstance(call_args, Event)
    assert call_args.event_type == "SHARED_EXPERIENCE"


def test_build_feed_returns_string():
    from identity.shared_life import SharedLife
    sl = SharedLife.__new__(SharedLife)
    sl._memory = MagicMock()
    sl._retrieval = MagicMock()
    sl._retrieval.shared_events.return_value = []
    feed = sl.build_feed(limit=5)
    assert isinstance(feed, str)


def test_observe_skips_if_not_eddie_present():
    from identity.shared_life import SharedLife
    sl = SharedLife.__new__(SharedLife)
    sl._orchestrator = MagicMock()
    sl._memory = MagicMock()
    sl._retrieval = MagicMock()
    result = sl.observe("screen desc", eddie_present=False)
    assert result["is_shared"] is False
    sl._orchestrator.execute.assert_not_called()
