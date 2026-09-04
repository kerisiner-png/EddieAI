import json
import socket
import threading
import time

from core.eddie_server import EddieServer


class FakeLifeCycle:
    def __init__(self):
        self.asleep = True

    def is_asleep(self):
        return self.asleep

    def force_wake(self):
        self.asleep = False
        return {"asleep": False}

    def force_sleep(self):
        self.asleep = True
        return {"asleep": True}


class FakeAgent:
    def __init__(self):
        self.life_cycle = FakeLifeCycle()


def _start_server():
    agent = FakeAgent()
    server = EddieServer(
        agent, host="127.0.0.1", port=7780
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    time.sleep(0.5)
    return server, agent


def _send(payload):
    s = socket.create_connection(
        ("127.0.0.1", 7780), timeout=3
    )
    s.sendall(
        (
            json.dumps(payload) + "\n"
        ).encode("utf-8")
    )
    s.close()


def test_wake_command():
    server, agent = _start_server()
    try:
        assert agent.life_cycle.asleep is True
        _send({"type": "life_control", "action": "wake"})
        time.sleep(0.5)
        assert agent.life_cycle.asleep is False
    finally:
        pass


def test_sleep_command():
    import json as _json
    import socket as _socket

    agent = FakeAgent()
    server = EddieServer(
        agent, host="127.0.0.1", port=7781
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    time.sleep(0.5)
    try:
        agent.life_cycle.force_wake()
        s = _socket.create_connection(
            ("127.0.0.1", 7781), timeout=3
        )
        s.sendall(
            (
                _json.dumps(
                    {
                        "type": "life_control",
                        "action": "sleep",
                    }
                )
                + "\n"
            ).encode("utf-8")
        )
        s.close()
        time.sleep(0.5)
        assert agent.life_cycle.asleep is True
    finally:
        pass