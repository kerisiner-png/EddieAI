from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


VALID_ACTIONS = {
    "THINK",
    "RESEARCH",
    "WRITE",
    "READ_FILE",
    "WRITE_FILE",
    "LIST_DIR",
    "SEARCH_FILES",
    "RUN_COMMAND",
    "WEB_SEARCH",
    "OPEN_URL",
    "WAIT",
    "SCREEN_CONTROL",
    "LAUNCH_APP",
    "INSTALL_PACKAGE",
}


@dataclass
class Action:
    action_type: str
    target: str
    parameters: dict[str, Any]
    reason: str = ""
    dry_run: bool = True
    status: str = "READY"
    created_at: str | None = None

    def __post_init__(self):
        if self.action_type not in VALID_ACTIONS:
            raise ValueError(
                f"Unknown action type: {self.action_type}"
            )

        if self.created_at is None:
            self.created_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

    def to_dict(self):
        return asdict(self)


class ActionExecutor:
    """
    Первый безопасный слой действий.

    Сейчас:
    - создаёт действия;
    - валидирует их;
    - поддерживает DRY_RUN;
    - ничего реально не запускает.

    Реальные инструменты подключим позже.
    """

    def __init__(self):
        self.history = []

    def create(
        self,
        action_type: str,
        target: str,
        parameters: dict | None = None,
        reason: str = "",
        dry_run: bool = True,
    ):
        action = Action(
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            reason=reason,
            dry_run=dry_run,
        )

        self.history.append(
            action
        )

        return action

    def validate(self, action: Action):
        errors = []

        if not action.target.strip():
            errors.append(
                "Action target cannot be empty."
            )

        if action.action_type in {
            "READ_FILE",
            "WRITE_FILE",
        }:
            if "path" not in action.parameters:
                errors.append(
                    "File action requires 'path'."
                )

        if action.action_type == "RUN_COMMAND":
            if "command" not in action.parameters:
                errors.append(
                    "RUN_COMMAND requires 'command'."
                )

        if action.action_type == "WEB_SEARCH":
            if "query" not in action.parameters:
                errors.append(
                    "WEB_SEARCH requires 'query'."
                )

        if action.action_type == "OPEN_URL":
            if "url" not in action.parameters:
                errors.append(
                    "OPEN_URL requires 'url'."
                )

        return {
            "valid": not errors,
            "errors": errors,
        }

    def execute(self, action: Action):
        validation = self.validate(
            action
        )

        if not validation["valid"]:
            action.status = "REJECTED"

            return {
                "status": "REJECTED",
                "action": action.to_dict(),
                "errors": validation["errors"],
            }

        if action.dry_run:
            action.status = "SIMULATED"

            return {
                "status": "SIMULATED",
                "action": action.to_dict(),
                "result": (
                    "Действие прошло валидацию, "
                    "но не было реально выполнено."
                ),
            }

        # Реальные исполнители пока намеренно
        # отсутствуют.
        action.status = "UNAVAILABLE"

        return {
            "status": "UNAVAILABLE",
            "action": action.to_dict(),
            "result": (
                "Реальный исполнитель этого "
                "действия ещё не подключён."
            ),
        }

    def last(self, limit: int = 10):
        return self.history[-limit:]
