from identity.identity_seed import IDENTITY_SEED
from memory.database import Memory
from memory.events import Event


def first_boot():
    memory = Memory()

    event = Event.create(
        content="Первый запуск EddieAI.",
        event_type="SYSTEM_EVENT",
        source_type="DIRECT_EXPERIENCE",
        source="first_boot",
        personal_experience=True,
        confidence=1.0,
        interpretation="Я впервые начал существовать как работающая система.",
        verified=True,
    )

    memory.remember(event)

    print("=" * 60)
    print("EddieAI — MEMORY TEST")
    print("=" * 60)
    print()
    print(f"Стартовый возраст: {IDENTITY_SEED['starting_age']}")
    print(f"Имя: {IDENTITY_SEED['name']}")
    print()
    print("Последние события:")

    for item in memory.recent():
        print()
        print(f"ID: {item['id']}")
        print(f"Событие: {item['content']}")
        print(f"Тип: {item['event_type']}")
        print(f"Источник: {item['source_type']}")
        print(f"Личный опыт: {bool(item['personal_experience'])}")
        print(f"Уверенность: {item['confidence']}")
        print(f"Интерпретация: {item['interpretation']}")

    memory.close()


if __name__ == "__main__":
    first_boot()
