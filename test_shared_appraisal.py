from unittest.mock import MagicMock


def test_appraise_returns_changes():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal.__new__(SharedAppraisal)
    sa._affective = MagicMock()
    changes = sa.appraise({"activity_type": "movie", "description": "funny scene", "is_shared": True})
    assert isinstance(changes, list)
    assert len(changes) > 0


def test_movie_increases_joy():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal.__new__(SharedAppraisal)
    sa._affective = MagicMock()
    changes = sa.appraise({"activity_type": "movie", "description": "funny comedy", "is_shared": True})
    joy_changes = [c for c in changes if c["name"] == "joy"]
    assert len(joy_changes) > 0
    assert joy_changes[0]["delta"] > 0


def test_appraise_relationship_returns_dict():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal.__new__(SharedAppraisal)
    result = sa.appraise_relationship({"activity_type": "movie", "is_shared": True})
    assert isinstance(result, dict)
    assert "intimacy_delta" in result


def test_appraise_not_shared_returns_empty():
    from identity.shared_appraisal import SharedAppraisal
    sa = SharedAppraisal.__new__(SharedAppraisal)
    sa._affective = MagicMock()
    changes = sa.appraise({"is_shared": False})
    assert changes == []


def test_appraise_applies_relationship_delta():
    from identity.shared_appraisal import SharedAppraisal

    class FakeSelfState:
        def __init__(self, data):
            self._data = data

        def get(self, key, default=None):
            return self._data.get(key, default)

        def set(self, key, value):
            self._data[key] = value

    state = {}
    sa = SharedAppraisal.__new__(SharedAppraisal)
    sa._affective = MagicMock()
    sa._self_state = FakeSelfState(state)
    sa.appraise({"activity_type": "movie", "description": "film", "is_shared": True})
    rels = state["relationships"]
    assert "intimacy" in rels["Eddie"]
    assert "trust" in rels["Eddie"]
    assert rels["Eddie"]["intimacy"] > 0


def test_appraise_relationship_caps_at_one():
    from identity.shared_appraisal import SharedAppraisal

    class FakeSelfState:
        def __init__(self, data):
            self._data = data

        def get(self, key, default=None):
            return self._data.get(key, default)

        def set(self, key, value):
            self._data[key] = value

    state = {
        "relationships": {
            "Eddie": {"intimacy": 0.99, "trust": 0.99}
        }
    }
    sa = SharedAppraisal.__new__(SharedAppraisal)
    sa._affective = MagicMock()
    sa._self_state = FakeSelfState(state)
    sa.appraise({"activity_type": "movie", "description": "film", "is_shared": True})
    rels = state["relationships"]["Eddie"]
    assert rels["intimacy"] <= 1.0
    assert rels["trust"] <= 1.0
