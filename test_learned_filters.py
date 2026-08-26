from pathlib import Path
from tempfile import TemporaryDirectory

from identity.behavioral_validator import (
    BehavioralValidator,
)
from memory.database import Memory


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")
    validator = BehavioralValidator(memory=db)

    contract = {
        "mode": "NEUTRAL",
        "max_sentences": 4,
        "question_required": False,
    }

    # Ответ с известным маркером помощи -> violation + обучение
    violations = validator.validate(
        "Я могу помочь тебе с этим.",
        contract,
    )

    kinds = [v.kind for v in violations]

    assert "GENERIC_HELP_TEMPLATE" in kinds, kinds

    learned = db.learned_get("help")

    assert learned, "должны выучиться новые маркеры категории help"

    # Новое слово дообучается из контекста с известным
    # маркером помощи, затем распознаётся само
    for _ in range(2):
        validator.validate(
            "Я могу помочь тебе, всегда готов выручить.",
            contract,
        )

    assert any(
        row["marker"] == "выручить"
        for row in db.learned_get("help")
    ), db.learned_get("help")

    # "выручить" выучен (count>=2) -> распознаётся сам
    violations = validator.validate(
        "Я готов выручить тебя.",
        contract,
    )

    assert "GENERIC_HELP_TEMPLATE" in [
        v.kind for v in violations
    ], violations

    print("LEARNED help:", [
        row["marker"]
        for row in db.learned_get("help")
        if row["count"] >= 2
    ])
    print("ALL PASS")

    db.close()
