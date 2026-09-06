"""Текст активного окна через UI Automation (Windows).

Возвращает фрагмент сфокусированного элемента
(имя/значение) — то, что читается без vision:
терминал, редактор, заголовки плеера. Все сбои
глотаются с пустой строкой (канал факультативный).
"""
MAX_CHARS = 600


def focused_window_text(
    max_chars=MAX_CHARS,
) -> str:
    try:
        from comtypes.client import (
            GetModule,
            CreateObject,
        )

        GetModule("UIAutomationCore.dll")

        import comtypes.gen.UIAutomationClient as UIAC

        iuia = CreateObject(
            UIAC.CUIAutomation,
            interface=UIAC.IUIAutomation,
        )
        element = iuia.GetFocusedElement()
        if element is None:
            return ""

        name = str(
            element.CurrentName or ""
        ).strip()

        value = ""

        try:
            pattern = element.GetCurrentPattern(
                UIAC.UIA_ValuePatternId
            )
            if pattern:
                value_pattern = (
                    pattern.QueryInterface(
                        UIAC.IUIAutomationValuePattern
                    )
                )
                value = str(
                    value_pattern.CurrentValue
                    or ""
                ).strip()
        except Exception:
            value = ""

        text = value or name

        return text[:max_chars]
    except Exception:
        return ""
