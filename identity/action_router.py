from dataclasses import dataclass

from identity.action_executor import (
    Action,
    VALID_ACTIONS,
)


@dataclass
class RoutedAction:
    action: Action
    tool: str
    allowed: bool
    reason: str


class ActionRouter:
    ROUTES = {
        "THINK": "llm",
        "RESEARCH": "research",
        "WRITE": "llm",
        "READ_FILE": "filesystem",
        "WRITE_FILE": "filesystem",
        "LIST_DIR": "filesystem",
        "SEARCH_FILES": "filesystem",
        "RUN_COMMAND": "powershell",
        "WEB_SEARCH": "web",
        "OPEN_URL": "web",
        "WAIT": "scheduler",
        "LAUNCH_APP": "programs",
        "INSTALL_PACKAGE": "install",
    }

    def __init__(
        self,
        registry,
    ):
        self.registry = registry

    def route(
        self,
        action: Action,
    ) -> RoutedAction:
        if action.action_type not in VALID_ACTIONS:
            return RoutedAction(
                action=action,
                tool="unknown",
                allowed=False,
                reason="Неизвестный тип действия.",
            )

        tool = self.ROUTES.get(
            action.action_type
        )

        if tool is None:
            return RoutedAction(
                action=action,
                tool="unknown",
                allowed=False,
                reason=(
                    "Для действия не найден "
                    "инструмент."
                ),
            )

        spec = self.registry.get(tool)

        if spec is None:
            return RoutedAction(
                action=action,
                tool=tool,
                allowed=False,
                reason=(
                    f"Инструмент '{tool}' "
                    "не зарегистрирован."
                ),
            )

        if not spec.enabled:
            return RoutedAction(
                action=action,
                tool=tool,
                allowed=False,
                reason=(
                    f"Инструмент '{tool}' "
                    "отключён."
                ),
            )

        return RoutedAction(
            action=action,
            tool=tool,
            allowed=True,
            reason="Инструмент доступен.",
        )
