from fastapi.testclient import TestClient

from communication.web_messenger import WebMessenger

import tempfile


class _StubServer:
    def __init__(self, history):
        self.history = history

    def handle_user_message(self, text):
        return None


from pathlib import Path
from tempfile import TemporaryDirectory

from memory.database import Memory


def _history():
    mem = Memory(Path(tempfile.mkdtemp()) / "h.db")
    mem.chat_add("Eddie", "Salve, EddieAI!")
    mem.chat_add("EddieAI", "Salve, Eddie.")
    return mem


def test_index_is_roman():
    web = WebMessenger(
        server=_StubServer(_history()),
        history=_history(),
    )
    client = TestClient(web.app)

    r = client.get("/")

    assert r.status_code == 200
    assert "EDDIE" in r.text
    assert "Tabula" in r.text


def test_history_endpoint():
    history = _history()
    web = WebMessenger(
        server=_StubServer(history), history=history
    )
    client = TestClient(web.app)

    r = client.get("/api/history")

    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["sender"] == "Eddie"
    assert items[1]["sender"] == "EddieAI"

    r2 = client.get("/api/history?before_id=2")
    items2 = r2.json()["items"]
    assert len(items2) == 1

    r3 = client.get("/api/search?q=salve")
    found = r3.json()["items"]
    assert len(found) == 2


if __name__ == "__main__":
    test_index_is_roman()
    test_history_endpoint()
    print("ALL OK")
