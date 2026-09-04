import subprocess
from typing import Optional


class SoftwareInstaller:
    """Установка ПО (ИНСТР-3).

    Свобода установки: агент может установить пакет через
    любой менеджер (pip/winget/choco/npm и т.п.) без
    согласования. Единственный фильтр — анти-катастрофический
    denylist (CommandPolicy): команда, содержащая разрушительные
    паттерны (форматирование, рекурсивное удаление), всегда
    заблокирована. Ведёт историю в self_state.install_history.
    """

    def __init__(
        self,
        self_state=None,
        timeout: int = 300,
    ):
        self._self_state = self_state
        self._timeout = timeout
        self._history = []

    def _policy(self):
        from identity.command_policy import (
            CommandPolicy,
        )

        return CommandPolicy()

    def _build_command(self, package, manager):
        manager = (manager or "").strip()
        package = (package or "").strip()
        if not manager or not package:
            return ""
        return f"{manager} install {package}"

    def _do_install(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout,
            )
            return {
                "status": (
                    "OK"
                    if result.returncode == 0
                    else "ERROR"
                ),
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "ERROR",
                "stderr": (
                    f"Установка превысила таймаут "
                    f"{self._timeout}с"
                ),
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "stderr": str(exc),
            }

    def install(
        self,
        package,
        manager,
    ):
        command = self._build_command(
            package, manager
        )
        if not command:
            return {
                "status": "DENIED",
                "reason": "Пустой пакет или менеджер.",
            }
        policy = self._policy()
        if policy.is_destructive(command):
            return {
                "status": "DENIED",
                "reason": policy.destructive_reason(
                    command
                ),
            }
        result = self._do_install(command)
        self._record(
            package, manager, command, result
        )
        return result

    def _record(
        self, package, manager, command, result
    ):
        entry = {
            "package": package,
            "manager": manager,
            "command": command,
            "status": result.get("status"),
            "at": None,
        }
        try:
            from datetime import datetime, timezone

            entry["at"] = datetime.now(
                timezone.utc
            ).isoformat()
        except Exception:
            pass
        self._history.append(entry)
        if self._self_state is not None:
            try:
                history = self._self_state.get(
                    "install_history", []
                )
                if not isinstance(history, list):
                    history = []
                history.append(entry)
                self._self_state.set(
                    "install_history", history[-50:]
                )
            except Exception:
                pass