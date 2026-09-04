from unittest.mock import MagicMock

from identity.sense_listener import SenseListener


def _make():
    class Agent:
        memory = MagicMock()

        def respond(self, text):
            return "ответ"

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
    sl._handle_spoken("привет")
    assert sl._server.msgs
    assert "привет" in sl._server.msgs[0]["text"]
    assert "ответ" in sl._server.msgs[0]["text"]


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
    assert len(sl._threads) == 2
    sl.stop()