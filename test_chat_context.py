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

    # Непрочитанные сообщения Эдди
    unread = db.chat_unread_context()

    lines = unread.split("\n")

    assert all(
        l.startswith("Эдди (непрочитано): ")
        for l in lines
    ), lines

    # После отметки прочитанным непрочитанных нет
    for row in db.connection.execute(
        "SELECT id FROM chat_history "
        "WHERE sender='Eddie'"
    ).fetchall():
        db.chat_mark_eddie_read(row["id"])

    assert db.chat_unread_context() == ""

    print("CTX:", ctx.replace("\n", " | "))
    print("UNREAD:", unread.replace("\n", " | "))
    print("ALL PASS")

    db.close()
