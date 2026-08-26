from pathlib import Path
from tempfile import TemporaryDirectory

from identity.appraisal_engine import AppraisalEngine
from memory.database import Memory


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")
    engine = AppraisalEngine(memory=db)

    # 1-й раз: похвала со словом, которого НЕТ в словаре
    result = engine.appraise_interaction(
        message="молодец, ты бесподобный"
    )

    assert result["trigger"] == "positive_social_feedback", result

    # 2-й раз: слово снова в контексте похвалы -> накапливается
    result = engine.appraise_interaction(
        message="ты бесподобный, спасибо"
    )

    assert result["trigger"] == "positive_social_feedback", result

    learned = db.learned_get("praise")

    assert any(
        row["marker"] == "бесподобный"
        for row in learned
    ), learned

    # 3-й раз: слово САМО (без известного маркера) -> распознаётся
    result = engine.appraise_interaction(
        message="бесподобный"
    )

    assert result["trigger"] == "positive_social_feedback", result
    assert result["changes"].get("joy", 0) > 0

    print("LEARNED praise:", [
        row["marker"]
        for row in db.learned_get("praise")
    ])
    print("ALL PASS")

    db.close()
