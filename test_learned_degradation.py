from pathlib import Path
from tempfile import TemporaryDirectory

from core.dialogue_memory import DialogueMemory
from memory.database import Memory


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")
    memory = DialogueMemory(memory=db)

    # Известный маркер -> отказ + обучение
    recorded = memory.record_agent_answer(
        "Я не могу думать сейчас, ресурсы исчерпаны."
    )

    assert recorded is False

    # Новое слово дообучается из контекста известного маркера
    for _ in range(2):
        memory.record_agent_answer(
            "Не могу думать, ресурсы исчерпаны полностью."
        )

    assert any(
        row["marker"] == "исчерпаны"
        for row in db.learned_get("degradation")
    ), db.learned_get("degradation")

    # Выученное слово распознаётся само
    recorded = memory.record_agent_answer(
        "Ресурсы исчерпаны."
    )

    assert recorded is False, (
        "выученный маркер должен распознаваться"
    )

    # Обычный ответ записывается
    recorded = memory.record_agent_answer(
        "Привет, я в порядке."
    )

    assert recorded is True

    print("LEARNED degradation:", [
        row["marker"]
        for row in db.learned_get("degradation")
    ][:6])
    print("ALL PASS")

    db.close()
