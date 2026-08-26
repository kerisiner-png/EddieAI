from pathlib import Path
from tempfile import TemporaryDirectory

from core.speech_habits import SpeechHabits
from memory.database import Memory
from memory.events import Event


with TemporaryDirectory() as temp:
    db = Memory(Path(temp) / "memory.db")

    habits = SpeechHabits(db)

    # Прямое наблюдение за фразой
    habits.observe_text(
        "Ну, вот кстати, я люблю ритм, "
        "и ритм для меня очень важен."
    )

    stats = db.speech_stats()

    assert stats["markers"] >= 3, stats

    profile = habits.profile(limit=20)

    assert "ну" in profile["filler_words"]
    assert "вот" in profile["filler_words"]
    assert "кстати" in profile["filler_words"]
    assert "ритм" in profile["favorite_words"], profile

    # Наблюдение из памяти: реплики EddieAI
    db.remember(Event.create(
        content=(
            "Ну, космос меня интересует, "
            "космос для меня очень важен."
        ),
        event_type="CONVERSATION",
        source_type="SELF",
        source="self",
        personal_experience=True,
        confidence=1.0,
        verified=True,
    ))

    db.remember(Event.create(
        content=(
            "Кстати, надо изучить звёзды, "
            "звёзды очень интересны."
        ),
        event_type="CONVERSATION",
        source_type="SELF",
        source="self",
        personal_experience=True,
        confidence=1.0,
        verified=True,
    ))

    processed = habits.learn_from_memory(limit=50)

    assert processed == 2, processed

    # Идемпотентность: повторный проход не должен
    # удваивать счётчики (каждая реплика один раз)
    again = habits.learn_from_memory(limit=50)

    assert again == 0, again

    profile = habits.profile(limit=20)

    assert "ну" in profile["filler_words"]
    assert "кстати" in profile["filler_words"]
    assert "космос" in profile["favorite_words"], profile
    assert "звёзды" in profile["favorite_words"], profile

    stats = db.speech_stats()

    assert stats["total"] == 8, (
        "повторный проход не должен расти счётчики"
    )

    # Зачаток НЕ хранит целые ответы — только маркеры
    top = db.speech_top(limit=50)

    for record in top:
        assert "изучать звёзды" not in record["marker"]
        assert "интересует" not in record["marker"]

    stats = db.speech_stats()

    print("STATS:", stats)
    print("PROFILE:", profile)
    print("ALL PASS")

    db.close()
