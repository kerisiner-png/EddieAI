class _FakePerceiver:
    def webcam_describe(self, camera="face"):
        return "Рядом сидит Эдди за ноутбуком."

    def capture_now(self):
        return {"description": "Открыт браузер с поиском."}


class _FakeAgentWithSenses:
    def __init__(self):
        self.screen_perceiver = _FakePerceiver()

    def _sensory_intent_snapshot(self, text):
        from core.agent import Agent
        a = Agent.__new__(Agent)
        a.screen_perceiver = self.screen_perceiver
        return a._sensory_intent_snapshot(text)


def test_sense_capabilities_block_mentions_senses():
    from core.prompt_builder import build_sense_capabilities_block
    block = build_sense_capabilities_block()
    assert "камера" in block
    assert "экран" in block
    assert "микрофон" in block
    assert "ПК" in block


def test_sense_capabilities_block_has_no_assistant_words():
    from core.prompt_builder import build_sense_capabilities_block
    block = build_sense_capabilities_block().lower()
    assert "ассистент" not in block
    assert "помощник" not in block


def test_sensory_snapshot_response_to_capability_question():
    agent = _FakeAgentWithSenses()
    out = agent._sensory_intent_snapshot(
        "у тебя есть функция смотреть на экран?"
    )
    assert "экран" in out
    assert "браузер" in out


def test_sensory_snapshot_response_to_camera_capability():
    agent = _FakeAgentWithSenses()
    out = agent._sensory_intent_snapshot(
        "ты умеешь видеть камерой что вокруг?"
    )
    assert "камеры" in out
    assert "сидит Эдди" in out


def test_sensory_snapshot_mentions_tools_when_asked():
    agent = _FakeAgentWithSenses()
    out = agent._sensory_intent_snapshot(
        "можешь ли ты нажать кнопку мышкой?"
    )
    assert "мышь" in out or "клик" in out