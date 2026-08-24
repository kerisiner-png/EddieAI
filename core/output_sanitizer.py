import re


class OutputSanitizer:
    """
    Финальная защита пользовательского ответа.

    Не решает содержание ответа.
    Только обнаруживает явную утечку внутренних
    cognitive/reasoning структур.
    """

    FORBIDDEN_MARKERS = (
        "INTERNAL COGNITIVE REASONING",
        "Core conclusion:",
        "Supporting conclusions:",
        "Response intent:",
        "Confidence:",
        "This is EddieAI's internal reasoning result.",
        "СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ",
        "КОНТЕКСТ",
        "RESPONSE INSTRUCTION",
    )

    @classmethod
    def leaks_reasoning(
        cls,
        text: str,
    ) -> bool:
        normalized = str(text).casefold()

        return any(
            marker.casefold()
            in normalized
            for marker in cls.FORBIDDEN_MARKERS
        )

    @classmethod
    def clean(
        cls,
        text: str,
    ) -> str:
        text = str(text).strip()

        if not cls.leaks_reasoning(text):
            return text

        # Если модель отдала полностью внутренний reasoning,
        # не показываем его пользователю.
        #
        # Здесь пока возвращаем пустую строку:
        # Agent должен будет выполнить fallback regeneration.
        return ""


