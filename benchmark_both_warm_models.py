from time import perf_counter

from core.agent import Agent


agent = Agent()

try:
    tests = [
        (
            "phi4-mini:latest",
            {
                "task": "conversation",
                "context": "",
                "system": (
                    "Ты — EddieAI. "
                    "Ответь кратко и естественно на русском языке."
                ),
                "user": (
                    "Одним предложением объясни, "
                    "почему астрофизика может быть интересной."
                ),
                "metadata": {
                    "fast": True,
                    "mode": "warm_benchmark",
                },
                "options": {
                    "temperature": 0.2,
                    "num_predict": 64,
                },
            },
        ),
        (
            "qwen3.5:4b",
            {
                "task": "reasoning",
                "context": "",
                "system": (
                    "Ты — когнитивный модуль EddieAI. "
                    "Ответь кратко и по существу."
                ),
                "user": (
                    "Сделай краткий причинный анализ: "
                    "почему сохранённое убеждение стоит "
                    "пересматривать только при наличии "
                    "нового противоречащего evidence?"
                ),
                "metadata": {
                    "fast": False,
                    "mode": "warm_benchmark",
                },
                "options": {
                    "temperature": 0.2,
                    "num_predict": 128,
                },
            },
        ),
    ]

    for expected_model, kwargs in tests:
        print()
        print("=" * 80)
        print("EXPECTED MODEL:", expected_model)

        if not hasattr(agent, "model_orchestrator") or not hasattr(
            agent.model_orchestrator, "execute"
        ):
            print("SKIP: model_orchestrator.execute() недоступен")
            continue

        started = perf_counter()

        result = agent.model_orchestrator.execute(
            **kwargs
        )

        elapsed = perf_counter() - started

        print(
            "ACTUAL MODEL:",
            result["model"],
        )
        print(
            "TIME:",
            round(elapsed, 3),
            "sec",
        )
        print(
            "ANSWER:",
            result["content"],
        )

finally:
    agent.close()
