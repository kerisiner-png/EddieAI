from core.agent import Agent


def main():
    agent = Agent()

    print("=" * 60)
    print("EddieAI v0.1")
    print("=" * 60)
    print("Первичная стадия развития.")
    print("Для выхода напиши: exit")
    print()

    try:
        while True:
            user_message = input("Эдди > ").strip()

            if user_message.lower() == "exit":
                break

            if not user_message:
                continue

            try:
                answer = agent.respond(user_message)
                print(f"\nEddieAI > {answer}\n")
            except Exception as exc:
                print(f"\nОшибка агента: {exc}\n")

    finally:
        agent.close()


if __name__ == "__main__":
    main()
