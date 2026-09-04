from pathlib import Path
from tempfile import TemporaryDirectory

from identity.personality_lifecycle import (
    PersonalityLifecycle,
)
from identity.self_state import SelfState


class LifecycleFixture:
    def __init__(self):
        self.temp = TemporaryDirectory()
        path = Path(self.temp.name) / "state.json"
        self.state = SelfState(path)
        self.lifecycle = PersonalityLifecycle(self.state)


def _make_lifecycle():
    return LifecycleFixture()


def test_thresholds_shift_with_evidence():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    maturity = 6 // 3
    active_mature = max(0.72, 0.80 - 0.02 * maturity)
    # по matured-порогу зрелая черта держится в ACTIVE при силе 0.78
    assert lc._status_from_strength_ev(0.78, 6) == "ACTIVE"
    # молодая черта (evidence=0) при той же силе ещё EMERGING
    assert lc._status_from_strength_ev(0.78, 0) == "EMERGING"
    assert active_mature < 0.80


def test_backcompat_base_constants():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    # evidence=0 -> исходные пороги, поведение не меняется
    assert lc._status_from_strength_ev(0.79, 0) == "EMERGING"
    assert lc._status_from_strength_ev(0.80, 0) == "ACTIVE"
    assert lc._status_from_strength_ev(0.55, 0) == "EMERGING"
    assert lc._status_from_strength_ev(0.35, 0) == "WEAKENING"
    assert lc._status_from_strength_ev(0.10, 0) == "DORMANT"
    # публичный метод без evidence сохраняет прежнее поведение
    assert lc._status_from_strength(0.79) == "EMERGING"
    assert lc._status_from_strength(0.80) == "ACTIVE"


def test_weakening_shifts_up_with_evidence():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    # зрелый характер быстрее отпускает слабые черты:
    # при evidence=6 weakening поднимается выше, поэтому
    # сила 0.37 уже DORMANT для зрелой черты
    assert lc._status_from_strength_ev(0.37, 6) == "DORMANT"
    # молодая черта той же силы ещё WEAKENING
    assert lc._status_from_strength_ev(0.37, 0) == "WEAKENING"


def test_promote_uses_mature_thresholds():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    lc.promote(
        "value",
        "усидчивость",
        strength=0.78,
        confidence=0.9,
        evidence_count=6,
    )
    trait = lc.get("value", "усидчивость")
    assert trait.status == "ACTIVE"


def test_promote_young_stays_emerging():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    lc.promote(
        "value",
        "юный_отклик",
        strength=0.78,
        confidence=0.9,
        evidence_count=0,
    )
    trait = lc.get("value", "юный_отклик")
    assert trait.status == "EMERGING"


def test_decay_mature_slower():
    fix = _make_lifecycle()
    lc = fix.lifecycle
    lc.promote(
        "value",
        "mature",
        strength=0.60,
        confidence=0.8,
        evidence_count=9,
    )
    lc.promote(
        "value",
        "young",
        strength=0.60,
        confidence=0.8,
        evidence_count=0,
    )
    # у mature evidence_count хранится как есть; после decay
    # mature-черта должна затухнуть слабее, чем young
    lc.decay(amount=0.10)
    mature = lc.get("value", "mature")
    young = lc.get("value", "young")
    assert mature.strength > young.strength


if __name__ == "__main__":
    test_thresholds_shift_with_evidence()
    test_backcompat_base_constants()
    test_weakening_shifts_up_with_evidence()
    test_promote_uses_mature_thresholds()
    test_promote_young_stays_emerging()
    test_decay_mature_slower()
    print("ALL OK")
