import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity.self_state import SelfState
from identity.goal_manager import GoalManager


def _key(value):
    return value.strip().lower()


def _mk_manager(tmpdir, name):
    state = SelfState(Path(tmpdir) / f"{name}_self.json")
    return GoalManager(state)


def _fill_active(manager, names_prio):
    for name, prio in names_prio:
        g = manager.add_candidate(
            value=name,
            motivation=0.5,
            priority=prio,
            confidence=0.5,
        )
        r = manager.activate(g.value)
        assert r["status"] == "ACTIVATED"


def test_high_priority_new_evicts_low_active(tmpdir):
    manager = _mk_manager(tmpdir, "g_evict")

    _fill_active(manager, [("a", 0.2), ("b", 0.3), ("c", 0.9)])

    cand = manager.add_candidate(
        value="d",
        motivation=0.5,
        priority=0.99,
        confidence=0.5,
    )

    result = manager.activate_with_preemption(cand.value)

    assert result["status"] == "ACTIVATED"
    # Самый слабый активный ("a", prio 0.2) вытеснен в PAUSED.
    evicted = manager.get("a")
    assert evicted.status == "PAUSED"
    assert manager.get("b").status == "ACTIVE"
    assert manager.get("c").status == "ACTIVE"
    assert manager.get("d").status == "ACTIVE"
    assert len(manager.active()) == 3


def test_low_priority_new_is_deferred(tmpdir):
    manager = _mk_manager(tmpdir, "g_def")

    _fill_active(manager, [("a", 0.5), ("b", 0.6), ("c", 0.9)])

    cand = manager.add_candidate(
        value="d",
        motivation=0.5,
        priority=0.1,
        confidence=0.5,
    )

    result = manager.activate_with_preemption(cand.value)

    assert result["status"] == "DEFERRED"
    assert manager.get("d").status == "CANDIDATE"
    # Никто не вытеснен.
    assert len(manager.active()) == 3


def test_full_slot_equal_no_evict(tmpdir):
    manager = _mk_manager(tmpdir, "g_eq")

    _fill_active(manager, [("a", 0.5), ("b", 0.5), ("c", 0.5)])

    cand = manager.add_candidate(
        value="d",
        motivation=0.5,
        priority=0.5,
        confidence=0.5,
    )

    result = manager.activate_with_preemption(cand.value)

    assert result["status"] == "DEFERRED"


def test_free_slot_activates_without_evict(tmpdir):
    manager = _mk_manager(tmpdir, "g_free")

    _fill_active(manager, [("a", 0.5)])

    cand = manager.add_candidate(
        value="d",
        motivation=0.5,
        priority=0.9,
        confidence=0.5,
    )

    result = manager.activate_with_preemption(cand.value)

    assert result["status"] == "ACTIVATED"
    assert manager.get("a").status == "ACTIVE"
    assert len(manager.active()) == 2


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="goal_preempt_")
    test_high_priority_new_evicts_low_active(tmpdir)
    test_low_priority_new_is_deferred(tmpdir)
    test_full_slot_equal_no_evict(tmpdir)
    test_free_slot_activates_without_evict(tmpdir)
    print("ALL OK")
