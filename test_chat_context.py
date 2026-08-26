from pathlib import Path
from tempfile import TemporaryDirectory

from memory.database import Memory


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")

    empty = db.chat_context(limit=4)

    assert empty == "", "пустой чат не должен давать контекст"

    db.chat_add("Eddie", "привет")
    db.chat_add("EddieAI", "здравствуй")
    db.chat_add("Eddie", "как дела?")

    ctx = db.chat_context(limit=3)

    lines = ctx.split("\n")

    assert lines[0] == "Эдди: привет", lines
    assert lines[1] == "EddieAI: здравствуй", lines
    assert lines[2] == "Эдди: как дела?", lines

    limited = db.chat_context(limit=1)

    assert limited.split("\n") == ["Эдди: как дела?"]

    print("CTX:", ctx.replace("\n", " | "))
    print("ALL PASS")

    db.close()
