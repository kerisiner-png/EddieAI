from unittest.mock import MagicMock

import time

from identity.sense_listener import SenseListener


def _make():
    class Agent:
        memory = MagicMock()
        self_state = MagicMock()

        def respond_call_fast(self, conversation, text):
            return "ответ голосом"

        def respond(self, text):
            return "ответ голосом"

    class Server:
        def __init__(self):
            self.msgs = []

        def broadcast(self, msg):
            self.msgs.append(msg)

    return SenseListener(
        agent=Agent(),
        server=Server(),
        screen_perceiver=None,
    )


def test_mic_handles_spoken_text():
    sl = _make()
    spoken = []
    sl._speak = lambda text: spoken.append(text)
    sl._handle_spoken("привет")
    assert spoken and "ответ голосом" in spoken[0]
    assert sl._server.msgs == []


def test_cam_pass_records_event():
    from identity.sense_listener import SenseListener

    class Agent:
        memory = MagicMock()
        respond = MagicMock(return_value="x")

    class FakeScreen:
        def webcam_describe(self):
            return "вижу человека"

    sl = SenseListener(
        agent=Agent(),
        server=None,
        screen_perceiver=FakeScreen(),
    )
    sl._cam_pass()
    assert sl._agent.memory.remember.called


def test_cam_pass_skips_empty_desc():
    from identity.sense_listener import SenseListener

    class Agent:
        memory = MagicMock()
        respond = MagicMock(return_value="x")

    class FakeScreen:
        def webcam_describe(self):
            return ""

    sl = SenseListener(
        agent=Agent(),
        server=None,
        screen_perceiver=FakeScreen(),
    )
    sl._cam_pass()
    assert not sl._agent.memory.remember.called


def test_start_and_stop():
    sl = _make()
    sl.start()
    assert len(sl._threads) == 3
    sl.stop()


def test_speak_pipered_answer():
    sl = _make()
    spoken = []
    sl._speak = lambda text: spoken.append(text)
    sl._handle_spoken("расскажи что-нибудь")
    assert spoken and "ответ голосом" in spoken[0]


def test_initiative_pass_speaks_when_idle():
    from identity.sense_listener import SenseListener

    class Agent:
        memory = MagicMock()
        self_state = MagicMock()

        class _SS:
            def get(self, key, default=None):
                return [{"name": "астрофизика"}]

        self_state = _SS()

        def respond(self, text):
            return "x"

    class Server:
        def __init__(self):
            self.msgs = []

        def broadcast(self, msg):
            self.msgs.append(msg)

    sl = SenseListener(
        agent=Agent(),
        server=Server(),
        screen_perceiver=None,
        initiative_interval=3600,
    )
    sl._last_spoken_at = time.time() - 9999
    spoken = []
    sl._speak = lambda text: spoken.append(text)
    sl._initiative_pass()
    assert spoken and "хочешь" in spoken[0]
    assert sl._server.msgs == []


def test_finish_phrase_emits_spoken():
    import json

    from identity.sense_listener import SenseListener

    class Agent:
        def __init__(self):
            self.calls = []

        def respond_call_fast(self, conversation, text):
            self.calls.append(text)
            return "ответ"

    sl = SenseListener(
        agent=Agent(),
        server=None,
        screen_perceiver=None,
    )
    spoken = []
    sl._speak = lambda text: spoken.append(text)

    class FakeRec:
        def __init__(self):
            self.text = "привет как дела"

        def AcceptWaveform(self, data):
            pass

        def FinalResult(self):
            return json.dumps(
                {"text": self.text}
            )

        def Reset(self):
            pass

    sl._finish_phrase(FakeRec(), b"some-bytes")
    assert sl._agent.calls == ["привет как дела"]
    assert spoken and "ответ" in spoken[0]


def test_finish_phrase_skips_short():
    import json

    from identity.sense_listener import SenseListener

    class Agent:
        def __init__(self):
            self.calls = []

        def respond_call_fast(self, conversation, text):
            self.calls.append(text)
            return "x"

    sl = SenseListener(
        agent=Agent(),
        server=None,
        screen_perceiver=None,
    )
    sl._speak = lambda text: None

    class FakeRec:
        def AcceptWaveform(self, data):
            pass

        def FinalResult(self):
            return json.dumps({"text": "да"})

        def Reset(self):
            pass

    sl._finish_phrase(FakeRec(), b"x")
    assert sl._agent.calls == []


def test_finish_phrase_wakes_when_asleep():
    import json

    from identity.sense_listener import SenseListener

    class Life:
        def __init__(self):
            self.woken = False

        def is_asleep(self):
            return True

        def force_wake(self):
            self.woken = True

    class Agent:
        def __init__(self):
            self.calls = []
            self.life_cycle = Life()

        def respond_call_fast(self, conversation, text):
            self.calls.append(text)
            return "ответ"

    sl = SenseListener(
        agent=Agent(),
        server=None,
        screen_perceiver=None,
    )
    spoken = []
    sl._speak = lambda text: spoken.append(text)

    class FakeRec:
        def AcceptWaveform(self, data):
            pass

        def FinalResult(self):
            return json.dumps({"text": "эдди просыпайся"})

        def Reset(self):
            pass

    sl._finish_phrase(FakeRec(), b"some-bytes")
    assert sl._agent.life_cycle.woken is True, (
        "обращение к спящему EddieAI будит его"
    )
    assert sl._agent.calls == ["эдди просыпайся"]
    assert spoken and "ответ" in spoken[0]