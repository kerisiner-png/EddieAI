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