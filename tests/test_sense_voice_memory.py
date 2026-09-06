from memory.events import Event


class _FakeHistory:
    def __init__(self):
        self.rows = [
            {"sender": "Eddie", "text": "сообщение из мессенджера"},
        ]

    def chat_recent(self, limit):
        return self.rows


class _FakeServer:
    def __init__(self):
        self.history = _FakeHistory()


class _FakeAgent:
    def __init__(self, memory):
        self.memory = memory
        self.answers = []
        self.last_conversation = ""

    def respond_call_fast(self, conversation, text):
        self.last_conversation = conversation
        self.answers.append(text)
        return "Привет, Эдди!"


def test_recent_dialogue_returns_voice_and_agent(tmp_path):
    from memory.database import Memory
    db = Memory(tmp_path / "m.db")
    db.remember(Event.create(
        content="доброе утро",
        event_type="CONVERSATION",
        source_type="VOICE",
        source="Eddie",
    ))
    db.remember(Event.create(
        content="Доброе утро, Эдди!",
        event_type="CONVERSATION",
        source_type="SELF_OUTPUT",
        source="EddieAI",
    ))
    items = db.recent_dialogue(6)
    assert len(items) == 2
    assert items[0]["label"] == "Эдди"
    assert items[0]["text"] == "доброе утро"
    assert items[1]["label"] == "EddieAI"
    assert items[1]["text"] == "Доброе утро, Эдди!"


def test_recent_dialogue_skips_empty_and_orders_desc(tmp_path):
    from memory.database import Memory
    db = Memory(tmp_path / "m.db")
    db.remember(Event.create(
        content="",
        event_type="CONVERSATION",
        source_type="VOICE",
        source="Eddie",
    ))
    db.remember(Event.create(
        content="первый",
        event_type="CONVERSATION",
        source_type="VOICE",
        source="Eddie",
    ))
    db.remember(Event.create(
        content="второй",
        event_type="CONVERSATION",
        source_type="VOICE",
        source="Eddie",
    ))
    items = db.recent_dialogue(6)
    assert len(items) == 2
    assert items[0]["text"] == "первый"
    assert items[1]["text"] == "второй"


def test_sense_uses_voice_memory_not_messenger(tmp_path):
    from identity.sense_listener import SenseListener
    from memory.database import Memory

    db = Memory(tmp_path / "m.db")
    db.remember(Event.create(
        content="что делал сегодня",
        event_type="CONVERSATION",
        source_type="VOICE",
        source="Eddie",
    ))
    db.remember(Event.create(
        content="Я смотрел на экран",
        event_type="CONVERSATION",
        source_type="SELF_OUTPUT",
        source="EddieAI",
    ))
    agent = _FakeAgent(memory=db)
    sl = SenseListener.__new__(SenseListener)
    sl._agent = agent
    sl._server = _FakeServer()

    conversation = sl._recent_conversation()

    assert "что делал сегодня" in conversation
    assert "Я смотрел на экран" in conversation
    assert "мессенджера" not in conversation


def test_sense_fallback_to_messenger_when_no_voice(tmp_path):
    from identity.sense_listener import SenseListener
    from memory.database import Memory

    db = Memory(tmp_path / "m.db")
    agent = _FakeAgent(memory=db)
    sl = SenseListener.__new__(SenseListener)
    sl._agent = agent
    sl._server = _FakeServer()

    conversation = sl._recent_conversation()

    assert "мессенджера" in conversation


def test_sense_records_voice_exchange(tmp_path):
    from identity.sense_listener import SenseListener
    from memory.database import Memory

    db = Memory(tmp_path / "m.db")
    agent = _FakeAgent(memory=db)
    sl = SenseListener.__new__(SenseListener)
    sl._agent = agent
    sl._server = _FakeServer()

    sl._handle_spoken("привет")

    items = db.recent_dialogue(6)
    texts = [item["text"] for item in items]
    assert any("привет" in t for t in texts)
    assert any("Привет, Эдди!" in t for t in texts)