class TaskRevisionPolicy:
    """
    Политика пересмотра плана при неудачном шаге.

    Детерминированно решает: повторить шаг (retry)
    или пересмотреть план (revise — пропустить шаг
    и перейти к следующему выполнимому).

    Консервативна по умолчанию: пересмотр только
    когда ошибка явно указывает, что инструмент/
    действие для шага недоступно. Транзиентные
    ошибки (timeout и т.п.) — повтор, как раньше.
    """

    UNAVAILABLE_HINTS = (
        "нет инструмента",
        "недоступен",
        "недоступна",
        "unavailable",
        "не установлен",
        "не установлена",
        "не найден",
        "не найдена",
        "не существует",
        "not found",
        "no such tool",
        "неизвестный инструмент",
    )

    def decide(
        self,
        goal: str,
        task: str,
        result: dict,
    ):
        if result.get("status") == "OK":
            return {
                "action": "retry",
                "reason": (
                    "Шаг успешен, "
                    "пересмотр не нужен."
                ),
            }

        if result.get("status") == "REJECTED":
            errors = result.get("errors") or []

            reason = "; ".join(
                str(item) for item in errors
            )

            if not reason:
                reason = (
                    "действие отклонено "
                    "политикой инструментов"
                )

            return {
                "action": "revise",
                "reason": (
                    f"Шаг невыполним: {reason}"
                ),
            }

        error = str(
            result.get("error", "")
        ).lower()

        for hint in self.UNAVAILABLE_HINTS:
            if hint in error:
                return {
                    "action": "revise",
                    "reason": (
                        f"Шаг невыполним: {error.strip()}"
                    ),
                }

        return {
            "action": "retry",
            "reason": (
                "Ошибка транзиентная, "
                "шаг можно повторить."
            ),
        }
