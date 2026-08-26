from ollama import chat


OLLAMA_MODEL = "phi4-mini"


class CloudFirstLlm:
    """
    Единая точка LLM-доступа подсистем автономии.

    Приоритет: облако через ModelOrchestrator
    (ролевой выбор модели). Фолбэк — локальный
    Ollama (phi4-mini), если облако недоступно
    или orchestrator не подключён.
    """

    def __init__(
        self,
        model_orchestrator=None,
        ollama_model=OLLAMA_MODEL,
    ):
        self.model_orchestrator = (
            model_orchestrator
        )

        self.ollama_model = ollama_model

    def chat(
        self,
        *,
        system: str,
        user: str,
        options: dict,
        task: str = "deep",
    ) -> str | None:
        raw = None

        if (
            self.model_orchestrator
            is not None
        ):
            raw = (
                self.model_orchestrator
                ._cloud_chat(
                    system=system,
                    user=user,
                    options=options,
                    task=task,
                )
            )

        if raw is not None:
            return raw.strip()

        try:
            response = chat(
                model=self.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
                options=options,
                keep_alive=-1,
            )

            return (
                response["message"]["content"]
                .strip()
            )
        except Exception:
            return None
