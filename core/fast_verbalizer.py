from __future__ import annotations


class FastVerbalizer:
    """
    Дешёвая вербализация уже сформированного внутреннего вывода.

    В DIRECT-режиме LLM вообще не вызывается.
    """

    def render(
        self,
        *,
        conclusion: dict,
        user_message: str,
        language: str,
    ) -> str | None:

        if not conclusion:
            return None

        text = str(
            conclusion.get(
                "conclusion",
                "",
            )
            or ""
        ).strip()

        if not text:
            return None

        stored_language = (
            conclusion.get(
                "language"
            )
        )

        def normalize_language(
            value: str | None,
        ) -> str:
            normalized = (
                str(value or "")
                .strip()
                .casefold()
            )

            aliases = {
                "ru": "ru",
                "русский": "ru",
                "russian": "ru",
                "en": "en",
                "английский": "en",
                "english": "en",
            }

            return aliases.get(
                normalized,
                normalized,
            )

        stored_lang = normalize_language(
            stored_language
        )

        current_lang = normalize_language(
            language
        )

        # Если язык известен с обеих сторон и они
        # действительно различаются, direct mode
        # не используется.
        #
        # Неизвестный язык не блокирует direct mode:
        # сам conclusion уже содержит готовый текст.
        if (
            stored_lang
            and current_lang
            and stored_lang != "unknown"
            and current_lang != "unknown"
            and stored_lang != current_lang
        ):
            return None

        return text
