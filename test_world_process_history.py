import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.world_process_history import WorldProcessHistory


def _snap(procs):
    return {
        "status": "OK",
        "top_processes": procs,
    }


def test_frequency_counts_repeated_procs():
    hist = WorldProcessHistory(window=5)
    hist.record(_snap([{"name": "chrome.exe"}, {"name": "python.exe"}]))
    hist.record(_snap([{"name": "chrome.exe"}, {"name": "msedge.exe"}]))
    hist.record(_snap([{"name": "chrome.exe"}]))

    freq = hist.frequency()
    assert freq["chrome.exe"] == 3
    assert freq["python.exe"] == 1
    assert freq["msedge.exe"] == 1


def test_frequent_processes_top():
    hist = WorldProcessHistory(window=10)
    hist.record(_snap([{"name": "a.exe"}]))
    hist.record(_snap([{"name": "a.exe"}, {"name": "b.exe"}]))
    hist.record(_snap([{"name": "a.exe"}]))
    hist.record(_snap([{"name": "b.exe"}]))

    top = hist.frequent_processes(top=2)
    assert top[0][0] == "a.exe"
    assert top[1][0] == "b.exe"


def test_window_drops_old_records():
    hist = WorldProcessHistory(window=3)
    hist.record(_snap([{"name": "a.exe"}]))
    hist.record(_snap([{"name": "a.exe"}]))
    hist.record(_snap([{"name": "a.exe"}]))
    hist.record(_snap([{"name": "b.exe"}]))

    # В окне из 3 последних снимков остались a, a, b:
    # первый a выпал, значит a встречается теперь 2 раза, а не 3.
    freq = hist.frequency()
    assert freq["a.exe"] == 2
    assert freq["b.exe"] == 1


def test_summary_empty_and_nonempty():
    hist = WorldProcessHistory(window=10)
    assert hist.summary_text() is not None
    assert hist.summary_text() == ""

    hist.record(_snap([{"name": "python.exe"}, {"name": "chrome.exe"}]))
    s = hist.summary_text()
    assert "python.exe" in s
    assert "chrome.exe" in s


def test_snapshot_skipped_if_not_ok():
    hist = WorldProcessHistory(window=10)
    hist.record({"status": "THROTTLED", "top_processes": []})
    assert len(hist.snapshots) == 0


if __name__ == "__main__":
    test_frequency_counts_repeated_procs()
    test_frequent_processes_top()
    test_window_drops_old_records()
    test_summary_empty_and_nonempty()
    test_snapshot_skipped_if_not_ok()
    print("ALL OK")
