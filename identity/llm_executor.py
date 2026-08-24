from core.model_orchestrator import ModelOrchestrator


class LLMExecutor:
    """
    Внутренний исполнитель THINK / RESEARCH / WRITE.

    Выбор модели делегируется ModelOrchestrator.
    """

    def __init__(
        self,
        model_orchestrator: ModelOrchestrator,
    ):
        self.model_orchestrator = (
            model_orchestrator
        )

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

        return self.model_orchestrator.execute(
            task=target,
            context=context,
            system=(
                "Ты внутренний исполнитель THINK. "
                "Не выдумывай внешние действия."
            ),
            user=prompt,
        )

    def research(
        self,
        target: str,
        context: str = "",
    ):
        return self.model_orchestrator.execute(
            task=target,
            context=context,
            system=(
                "Ты внутренний исполнитель RESEARCH. "
                "Не утверждай, что получил данные "
                "из внешнего источника, если инструмент "
                "не был реально использован."
            ),
            user=target,
        )

    def write(
        self,
        target: str,
        context: str = "",
    ):
        return self.model_orchestrator.execute(
            task=target,
            context=context,
            system=(
                "Ты внутренний исполнитель WRITE."
            ),
            user=target,
        )

