from ollama import chat


class LLMExecutor:
    """
    Внутренний исполнитель THINK / RESEARCH / WRITE.

    Внешние действия он не выполняет и не имитирует.
    """

    def __init__(
        self,
        model: str = "phi4-mini",
    ):
        self.model = model

    def think(
        self,
        target: str,
        context: str = "",
    ):
        prompt = f"""
Ты выполняешь внутреннюю задачу автономного агента.

Задача:
{target}

Контекст:
{context}

Дай конкретный результат, который можно использовать
для следующего шага.

Не утверждай, что выполнял внешний инструмент,
если его не было.
"""

        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты внутренний исполнитель THINK. "
                        "Не выдумывай внешние действия."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "num_ctx": 2048,
                "num_predict": 256,
                "temperature": 0.4,
            },
            keep_alive=-1,
        )

        return {
            "status": "OK",
            "content": (
                response["message"]["content"]
                .strip()
            ),
        }

    def research(
        self,
        target: str,
        context: str = "",
    ):
        return self.think(
            target,
            context,
        )

    def write(
        self,
        target: str,
        context: str = "",
    ):
        return self.think(
            target,
            context,
        )
