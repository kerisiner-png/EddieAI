import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity.research_tracker import ResearchTracker


def _tracker(tmpdir, name="rt"):
    from identity.self_state import SelfState

    state = SelfState(Path(tmpdir) / f"{name}.json")
    return ResearchTracker(state)


def test_start_creates_current(tmpdir):
    tracker = _tracker(tmpdir, "t1")
    tracker.start("космос", source="curiosity")
    cur = tracker.current()
    assert cur is not None
    assert cur["topic"] == "космос"
    assert cur["source"] == "curiosity"
    assert cur["sources"] == 0
    assert cur["steps"] == 0


def test_start_resumes_same_topic(tmpdir):
    tracker = _tracker(tmpdir, "t2")
    tracker.start("космос")
    tracker.record_findings(num_sources=2)
    tracker.start("космос")
    cur = tracker.current()
    # Тот же политический тема — текущее исследование не обнуляется.
    assert cur["sources"] == 2


def test_start_new_topic_resets(tmpdir):
    tracker = _tracker(tmpdir, "t3")
    tracker.start("космос")
    tracker.record_findings(num_sources=2)
    tracker.start("океан")
    cur = tracker.current()
    assert cur["topic"] == "океан"
    assert cur["sources"] == 0


def test_record_findings_accumulates(tmpdir):
    tracker = _tracker(tmpdir, "t4")
    tracker.start("космос")
    tracker.record_findings(num_sources=3, num_steps=2)
    tracker.record_findings(num_sources=1, num_steps=1)
    cur = tracker.current()
    assert cur["sources"] == 4
    assert cur["steps"] == 3


def test_add_note_stored(tmpdir):
    tracker = _tracker(tmpdir, "t5")
    tracker.start("космос")
    tracker.add_note("найдено подтверждение", finding_type="evidence")
    cur = tracker.current()
    assert len(cur["notes"]) == 1
    assert cur["notes"][0]["text"] == "найдено подтверждение"
    assert cur["notes"][0]["type"] == "evidence"


def test_decide_should_deepen_below_threshold(tmpdir):
    tracker = _tracker(tmpdir, "t6")
    tracker.start("космос")
    assert tracker.should_deepen() is True


def test_decide_stops_at_threshold(tmpdir):
    tracker = _tracker(tmpdir, "t7")
    tracker.start("космос")
    for _ in range(6):
        tracker.record_findings(num_sources=1)
    assert tracker.should_deepen() is False


def test_complete_moves_to_history(tmpdir):
    tracker = _tracker(tmpdir, "t8")
    tracker.start("космос")
    tracker.record_findings(num_sources=5, num_steps=3)
    tracker.complete()
    assert tracker.current() is None
    history = tracker.history()
    assert len(history) == 1
    assert history[0]["topic"] == "космос"
    assert history[0]["sources"] == 5


def test_resume_candidate_returns_pending(tmpdir):
    tracker = _tracker(tmpdir, "t9")
    # Нет текущего исследования — нет кандидата на продолжение.
    assert tracker.resume_candidate() is None

    tracker.start("космос")
    tracker.record_findings(num_sources=1)
    # Есть незавершённое текущее исследование.
    cand = tracker.resume_candidate()
    assert cand is not None
    assert cand["topic"] == "космос"


def test_progress_text_empty_when_none(tmpdir):
    tracker = _tracker(tmpdir, "t10")
    assert tracker.progress_text() == ""


def test_progress_text_shows_topic_and_counts(tmpdir):
    tracker = _tracker(tmpdir, "t11")
    tracker.start("космос")
    tracker.record_findings(num_sources=3, num_steps=2)
    text = tracker.progress_text()
    assert "космос" in text
    assert "3" in text
    assert "2" in text


def test_progress_text_includes_notes_count(tmpdir):
    tracker = _tracker(tmpdir, "t12")
    tracker.start("космос")
    tracker.record_findings(num_sources=2)
    tracker.add_note("найдено", finding_type="evidence")
    text = tracker.progress_text()
    assert "заметок: 1" in text


if __name__ == "__main__":
    _t = tempfile.mkdtemp(prefix="rt_")
    test_start_creates_current(_t)
    test_start_resumes_same_topic(_t)
    test_start_new_topic_resets(_t)
    test_record_findings_accumulates(_t)
    test_add_note_stored(_t)
    test_decide_should_deepen_below_threshold(_t)
    test_decide_stops_at_threshold(_t)
    test_complete_moves_to_history(_t)
    test_resume_candidate_returns_pending(_t)
    test_progress_text_empty_when_none(_t)
    test_progress_text_shows_topic_and_counts(_t)
    test_progress_text_includes_notes_count(_t)
    print("ALL OK")
