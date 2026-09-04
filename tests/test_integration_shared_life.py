import pytest


class _FakeSelfState:
    def __init__(self):
        self._data = {}
    def get(self, key, default=None):
        return self._data.get(key, default)
    def set(self, key, value):
        self._data[key] = value


def test_self_model_has_shared_section():
    from identity.self_model import SelfModel
    fs = _FakeSelfState()
    sm = SelfModel(fs)
    sm.build(
        [],
        agent=None,
        shared_life={
            "events_count": 3,
            "last_activity": "просмотр фильма",
        },
    )
    text = sm.render()
    assert "совместн" in text.lower() or "shared" in text.lower()


def test_screen_perceiver_can_be_imported():
    from identity.shared_life import SharedLife
    sl = SharedLife()
    assert hasattr(sl, 'observe')
    assert hasattr(sl, 'record')
    assert hasattr(sl, 'build_feed')


def test_shared_appraisal_can_be_imported():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal()
    assert hasattr(sa, 'appraise')
    assert hasattr(sa, 'appraise_relationship')


def test_shared_life_observe_returns_dict():
    from identity.shared_life import SharedLife
    sl = SharedLife()
    result = sl.observe("test screen", eddie_present=False)
    assert isinstance(result, dict)
    assert result["is_shared"] is False


def test_shared_appraise_no_shared():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal()
    result = sa.appraise({"is_shared": False})
    assert result == []


def test_shared_appraise_relationship_no_shared():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal()
    result = sa.appraise_relationship({"is_shared": False})
    assert result["intimacy_delta"] == 0.0
    assert result["trust_delta"] == 0.0
