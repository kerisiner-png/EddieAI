from core.eddie_server import EddieServer
from identity.shared_activity_manager import (
    SharedActivityManager,
)


class FakeHistory:
    def __init__(self):
        self.next_id = 1

    def chat_add(self, sender, text):
        msg_id = self.next_id
        self.next_id += 1
        return msg_id

    def chat_mark_eddie_read(self, msg_id):
        return None


class FakeMemory:
    def remember(self, event):
        return None


class FakeSharedLife:
    def __init__(self):
        self.records = []

    def record(self, content, activity_type, mood):
        self.records.append(
            (content, activity_type)
        )


class FakeAgent:
    def __init__(self):
        self.shared_activity = SharedActivityManager()
        self.shared_life = FakeSharedLife()
        self.memory = FakeMemory()


def _make_server():
    agent = FakeAgent()
    server = EddieServer(agent)
    server.history = FakeHistory()
    return server, agent


def test_server_starts_shared_activity():
    server, agent = _make_server()
    server._apply_shared_activity_command(
        "давай посмотрим Интерстеллар"
    )
    current = agent.shared_activity.get_current()
    assert current is not None
    assert current["type"] == "movie"
    assert current["title"] == "Интерстеллар"
    assert current["source"] == "chat"


def test_server_stops_shared_activity():
    server, agent = _make_server()
    server._apply_shared_activity_command(
        "давай посмотрим фильм"
    )
    assert agent.shared_activity.is_active()
    server._apply_shared_activity_command(
        "выключи, хватит"
    )
    assert not agent.shared_activity.is_active()


def test_server_records_shared_event():
    server, agent = _make_server()
    server._apply_shared_activity_command(
        "включи музыку"
    )
    assert len(agent.shared_life.records) >= 1
    recorded_type = agent.shared_life.records[-1][1]
    assert recorded_type == "music"


def test_server_plain_message_ignored():
    server, agent = _make_server()
    server._apply_shared_activity_command(
        "как дела?"
    )
    assert agent.shared_activity.get_current() is None


def test_handle_user_message_applies_command():
    server, agent = _make_server()
    server.handle_user_message(
        "поиграем в шахматы"
    )
    current = agent.shared_activity.get_current()
    assert current is not None
    assert current["type"] == "game"