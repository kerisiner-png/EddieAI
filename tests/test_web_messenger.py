from fastapi.testclient import TestClient

from communication.web_messenger import WebMessenger


class _StubServer:
    def __init__(self, history):
        self.history = history

    def handle_user_message(self, text):
        return None


class _StubHistory:
    def __init__(self):
        self.rows = [
            {
                "id": 1,
                "sender": "Eddie",
                "text": "Salve, EddieAI!",
                "ts": "2026-09-06T18:00:00+00:00",
            }
        ]

    def chat_recent(self, limit=50):
        return self.rows[-limit:]


def test_index_is_roman():
    web = WebMessenger(
        server=_StubServer(_StubHistory()),
        history=_StubHistory(),
    )
    client = TestClient(web.app)

    r = client.get("/")

    assert r.status_code == 200
    assert "EDDIE" in r.text
    assert "Tabula" in r.text


def test_history_endpoint():
    history = _StubHistory()
    web = WebMessenger(
        server=_StubServer(history), history=history
    )
    client = TestClient(web.app)

    r = client.get("/api/history")

    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["sender"] == "Eddie"


if __name__ == "__main__":
    test_index_is_roman()
    test_history_endpoint()
    print("ALL OK")
