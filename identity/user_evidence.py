class UserEvidenceRecorder:
    """
    Записывает явные утверждения пользователя
    как provenance USER_STATEMENT.

    Важно:
    этот класс не интерпретирует слова пользователя.
    Он получает уже выделенное утверждение.
    """

    def __init__(self, evidence):
        self.evidence = evidence

    def record_interest(
        self,
        value: str,
    ):
        value = str(
            value
        ).strip()

        if not value:
            return {
                "status": "REJECTED",
                "reason": (
                    "Пустое утверждение."
                ),
            }

        record = self.evidence.add(
            category="interest",
            value=value,
            source="USER_STATEMENT",
        )

        return {
            "status": "RECORDED",
            "field": "interest",
            "value": value,
            "evidence": record,
        }
