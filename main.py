from identity.identity_seed import IDENTITY_SEED
from memory.database import Memory


def first_boot():
    memory = Memory()

    print("=" * 60)
    print("EddieAI — FIRST BOOT")
    print("=" * 60)
    print()

    print("Начальная идентичность загружена.")
    print(f"Пол: {IDENTITY_SEED['gender']}")
    print(f"Стартовый внутренний возраст: {IDENTITY_SEED['starting_age']}")
    print(f"Имя: {IDENTITY_SEED['name']}")
    print()

    print("Базовые ценности:")
    for value in IDENTITY_SEED["values"]:
        print(f"  - {value}")

    print()
    print("Первоначальные интересы: отсутствуют.")
    print("Первоначальные привычки: отсутствуют.")
    print("Первоначальные предпочтения: отсутствуют.")
    print("Первоначальные убеждения: отсутствуют.")
    print()

    memory.add(
        content="Первый запуск EddieAI.",
        source_type="SYSTEM_EVENT",
        source="first_boot",
        confidence=1.0,
        personal_experience=True,
        verified=True,
    )

    memory.close()

    print("Событие первого запуска сохранено в автобиографической памяти.")
    print()
    print("EddieAI пока не знает, кем он станет.")
    print("Это его отправная точка.")


if __name__ == "__main__":
    first_boot()
