import subprocess
from typing import Optional


class AppLauncher:
    """Запуск программ (ИНСТР-2 / ДПК2).

    Свобода запуска: агент может запустить любую программу.
    Единственный фильтр — анти-катастрофический denylist
    (CommandPolicy.is_destructive): форматирование, рекурсивное
    удаление системного и т.п. всегда заблокировано.
    Ведёт историю запусков в self_state.app_launch_history.
    """

    def __init__(
        self,
        self_state=None,
    ):
        self._self_state = self_state

    def _policy(self):
        from identity.command_policy import (
            CommandPolicy,
        )

        return CommandPolicy()

    def _real_launch(self, command):
        return subprocess.Popen(
            command,
            shell=True,
        )

    def is_allowed(self, command):
        if not command or not command.strip():
            return False
        return not self._policy().is_destructive(
            command
        )

    def launch(self, command):
        if not command or not command.strip():
            return {
                "status": "DENIED",
                "reason": "Пустая команда запуска.",
            }
        policy = self._policy()
        if policy.is_destructive(command):
            return {
                "status": "DENIED",
                "reason": policy.destructive_reason(
                    command
                ),
            }
        try:
            self._real_launch(command)
        except Exception as exc:
            return {
                "status": "ERROR",
                "reason": str(exc),
                "command": command,
            }
        self._record(command)
        return {
            "status": "OK",
            "command": command,
        }

    def _record(self, command):
        if self._self_state is None:
            return
        try:
            from datetime import datetime, timezone

            history = self._self_state.get(
                "app_launch_history", []
            )
            if not isinstance(history, list):
                history = []
            history.append(
                {
                    "command": command,
                    "at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
            )
            self._self_state.set(
                "app_launch_history", history[-20:]
            )
        except Exception:
            pass