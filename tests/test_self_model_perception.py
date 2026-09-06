from identity.self_model import SelfModel


class _FakeState:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def get_all(self):
        return dict(self._data)


class _Agent:
    def __init__(
        self,
        pc_audio=None,
        sense_listener=None,
        screen_perceiver=None,
        goals=(),
    ):
        self.pc_audio = pc_audio
        self.sense_listener = sense_listener
        self.screen_perceiver = screen_perceiver
        self.self_state = _FakeState()

        self.goal_manager = type(
            "G",
            (),
            {"active": lambda self: list(goals)},
        )()


def _limitations_for(agent):
    model = SelfModel(_FakeState())
    built = model.build(
        [
            {
                "name": "web",
                "description": "web",
                "enabled": True,
            }
        ],
        agent=agent,
    )
    return built.get("limitations", [])


def test_full_senses_no_perceptual_limits():
    limits = _limitations_for(
        _Agent(
            pc_audio=object(),
            sense_listener=object(),
            screen_perceiver=object(),
        )
    )
    ids = [item["id"] for item in limits]
    assert "no_audio" not in ids
    assert "no_vision" not in ids


def test_deaf_agent_keeps_no_audio():
    limits = _limitations_for(
        _Agent(screen_perceiver=object())
    )
    ids = [item["id"] for item in limits]
    assert "no_audio" in ids
    assert "no_vision" not in ids


def test_blind_agent_keeps_no_vision():
    limits = _limitations_for(
        _Agent(sense_listener=object())
    )
    ids = [item["id"] for item in limits]
    assert "no_vision" in ids
    assert "no_audio" not in ids


def test_unknown_agent_conservative_defaults():
    limits = _limitations_for(None)
    ids = [item["id"] for item in limits]
    assert "no_audio" in ids
    assert "no_vision" in ids


if __name__ == "__main__":
    test_full_senses_no_perceptual_limits()
    test_deaf_agent_keeps_no_audio()
    test_blind_agent_keeps_no_vision()
    test_unknown_agent_conservative_defaults()
    print("ALL OK")
