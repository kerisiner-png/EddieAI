from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from core.eddie_server import EddieServer
from memory.chat_history import ChatHistory
from memory.database import Memory


class _FakeLifeCycle:
    def __init__(self, asleep):
        self._asleep = asleep
        self.woken = False

    def is_asleep(self):
        return self._asleep

    def force_wake(self):
        self.woken = True


class _FakeAgent:
    def __init__(self, life_cycle=None):
        self.responded_with = None
        self.life_cycle = life_cycle

    def respond(self, text):
        self.responded_with = text
        return "Ответ EddieAI"


@contextmanager
def _server(life_cycle=None):
    temp = TemporaryDirectory()
    db = None
    history = None
    try:
        db = Memory(
            db_path=Path(temp.name) / "chat.db"
        )
        history = ChatHistory(db)
        agent = _FakeAgent(life_cycle)
        server = EddieServer(
            agent=agent,
            history_store=history,
        )
        yield server, agent
    finally:
        if history is not None:
            try:
                history.close()
            except Exception:
                pass
        temp.cleanup()


@contextmanager
def _bare_history():
    temp = TemporaryDirectory()
    db = None
    history = None
    try:
        db = Memory(
            db_path=Path(temp.name) / "chat.db"
        )
        history = ChatHistory(db)
        yield history
    finally:
        if history is not None:
            try:
                history.close()
            except Exception:
                pass
        temp.cleanup()


def test_chat_history_delegates_to_memory():
    with _bare_history() as history:
        msg_id = history.chat_add(
            "Eddie", "Привет, EddieAI!"
        )
        assert isinstance(msg_id, int)

        unread = history.chat_unread_eddie()
        assert len(unread) == 1
        assert unread[0]["text"] == (
            "Привет, EddieAI!"
        )

        history.chat_mark_eddie_read(
            unread[0]["id"]
        )
        assert (
            history.chat_unread_eddie() == []
        )

        history.chat_add("EddieAI", "Ответ")
        recent = history.chat_recent(10)
        assert [
            item["sender"] for item in recent
        ] == [
            "Eddie",
            "EddieAI",
        ]


def test_user_message_stored_as_unread():
    with _server() as (server, _):
        server.handle_user_message(
            "Привет, EddieAI!"
        )

        unread = (
            server.history.chat_unread_eddie()
        )
        assert len(unread) == 1
        assert unread[0]["text"] == (
            "Привет, EddieAI!"
        )


def test_respond_and_deliver_answers_latest():
    with _server() as (server, agent):
        server.handle_user_message("Как дела?")
        answer = server.respond_and_deliver()

        assert answer == "Ответ EddieAI"
        assert agent.responded_with == "Как дела?"

        recent = server.history.chat_recent(5)
        assert [
            item["sender"] for item in recent
        ] == ["Eddie", "EddieAI"]


def test_respond_and_deliver_without_unread_is_silent():
    with _server() as (server, agent):
        assert (
            server.respond_and_deliver() is None
        )
        assert agent.responded_with is None


def test_handle_user_message_without_history_is_safe():
    temp = TemporaryDirectory()
    try:
        server = EddieServer(
            agent=_FakeAgent(),
            history_store=None,
        )
        assert (
            server.handle_user_message(
                "Привет"
            )
            is None
        )
    finally:
        temp.cleanup()


def test_message_wakes_sleeping_eddieai():
    life = _FakeLifeCycle(asleep=True)
    with _server(life) as (server, _):
        server.handle_user_message("Эдди?")
        assert life.woken is True


def test_message_does_not_wake_awake_eddieai():
    life = _FakeLifeCycle(asleep=False)
    with _server(life) as (server, _):
        server.handle_user_message("Привет")
        assert life.woken is False


if __name__ == "__main__":
    test_chat_history_delegates_to_memory()
    test_user_message_stored_as_unread()
    test_respond_and_deliver_answers_latest()
    test_respond_and_deliver_without_unread_is_silent()
    test_handle_user_message_without_history_is_safe()
    test_message_wakes_sleeping_eddieai()
    test_message_does_not_wake_awake_eddieai()
    print("ALL OK")
