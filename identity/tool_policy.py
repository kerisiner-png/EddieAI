from pathlib import Path


class ToolExecutionPolicy:
    """
    Детерминированная политика выполнения инструментов.

    Наличие инструмента != право выполнить конкретное действие.
    """

    def __init__(
        self,
        filesystem_root: str = r"C:\EddieAI",
    ):
        self.filesystem_root = (
            Path(filesystem_root).resolve()
        )

        self.allow_read_files = True
        self.allow_write_files = False
        self.allow_powershell = True
        self.allow_web = True

        self.max_read_bytes = 200_000
        self.max_write_bytes = 100_000

    def evaluate(
        self,
        action,
    ) -> dict:
        action_type = action.action_type

        if action_type == "THINK":
            return self._allow(
                "Внутреннее рассуждение разрешено."
            )

        if action_type == "RESEARCH":
            return self._allow(
                "Исследование разрешено."
            )

        if action_type == "WRITE":
            return self._allow(
                "Генерация текста разрешена."
            )

        if action_type == "READ_FILE":
            return self._read_file(action)

        if action_type == "WRITE_FILE":
            return self._write_file(action)

        if action_type == "LIST_DIR":
            return self._list_dir(action)

        if action_type == "SEARCH_FILES":
            return self._search_files(action)

        if action_type == "RUN_COMMAND":
            return self._powershell(action)

        if action_type in {
            "WEB_SEARCH",
            "OPEN_URL",
        }:
            return self._web(action)

        if action_type == "WAIT":
            return self._allow(
                "Ожидание разрешено."
            )

        if action_type == "SCREEN_CONTROL":
            return self._allow(
                "Управление экраном разрешено."
            )

        if action_type == "LAUNCH_APP":
            return self._launch_app(action)

        if action_type == "INSTALL_PACKAGE":
            return self._install_package(action)

        return self._deny(
            "Неизвестный тип действия."
        )

    def _read_file(
        self,
        action,
    ):
        if not self.allow_read_files:
            return self._deny(
                "Чтение файлов отключено."
            )

        path = action.parameters.get(
            "path"
        )

        if not path:
            return self._deny(
                "Не указан путь к файлу."
            )

        if not self._inside_filesystem(
            path
        ):
            return self._deny(
                "Файл находится вне sandbox."
            )

        max_bytes = action.parameters.get(
            "max_bytes",
            self.max_read_bytes,
        )

        try:
            max_bytes = int(max_bytes)
        except (TypeError, ValueError):
            return self._deny(
                "Некорректный max_bytes."
            )

        if not (
            1 <= max_bytes <= self.max_read_bytes
        ):
            return self._deny(
                "Превышен допустимый размер чтения."
            )

        return self._allow(
            "Чтение файла разрешено."
        )

    def _list_dir(self, action):
        if not self.allow_read_files:
            return self._deny(
                "Листинг каталога отключён."
            )

        path = action.parameters.get(
            "path"
        )

        if not path:
            return self._deny(
                "Не указан путь к каталогу."
            )

        if not self._inside_filesystem(path):
            return self._deny(
                "Каталог находится вне sandbox."
            )

        return self._allow(
            "Листинг каталога разрешён."
        )

    def _search_files(self, action):
        if not self.allow_read_files:
            return self._deny(
                "Поиск файлов отключён."
            )

        pattern = action.parameters.get(
            "pattern"
        )

        if not pattern:
            return self._deny(
                "Не указан паттерн поиска."
            )

        return self._allow(
            "Поиск файлов разрешён."
        )

    def _write_file(
        self,
        action,
    ):
        if not self.allow_write_files:
            return self._deny(
                "Запись файлов отключена."
            )

        path = action.parameters.get(
            "path"
        )

        content = action.parameters.get(
            "content"
        )

        if not path:
            return self._deny(
                "Не указан путь к файлу."
            )

        if content is None:
            return self._deny(
                "Не указано содержимое."
            )

        if not self._inside_filesystem(
            path
        ):
            return self._deny(
                "Файл находится вне sandbox."
            )

        size = len(
            str(content).encode("utf-8")
        )

        if size > self.max_write_bytes:
            return self._deny(
                "Размер записи превышает лимит."
            )

        return self._allow(
            "Запись файла разрешена."
        )

    def _powershell(
        self,
        action,
    ):
        if not self.allow_powershell:
            return self._deny(
                "PowerShell executor отключён."
            )

        command = action.parameters.get(
            "command"
        )

        if not command:
            return self._deny(
                "Не указана команда."
            )

        from identity.command_policy import (
            CommandPolicy,
        )

        policy = CommandPolicy()

        if not policy.is_safe(command):
            reason = policy.deny_reason(
                command
            )
            return self._deny(
                f"Команда заблокирована: {reason}"
            )

        return self._allow(
            "Команда разрешена."
        )

    def _launch_app(
        self,
        action,
    ):
        command = action.parameters.get(
            "command"
        )

        if not command:
            return self._deny(
                "Не указана команда запуска."
            )

        from identity.command_policy import (
            CommandPolicy,
        )

        policy = CommandPolicy()

        if policy.is_destructive(command):
            return self._deny(
                policy.destructive_reason(command)
            )

        return self._allow(
            "Запуск программы разрешён."
        )

    def _install_package(
        self,
        action,
    ):
        package = action.parameters.get(
            "package"
        )

        manager = action.parameters.get(
            "manager"
        )

        if not package or not manager:
            return self._deny(
                "Нужны package и manager."
            )

        command = f"{manager} install {package}"

        from identity.command_policy import (
            CommandPolicy,
        )

        policy = CommandPolicy()

        if policy.is_destructive(command):
            return self._deny(
                policy.destructive_reason(command)
            )

        return self._allow(
            "Установка пакета разрешена."
        )

    def _web(
        self,
        action,
    ):
        if not self.allow_web:
            return self._deny(
                "Web executor отключён."
            )

        if action.action_type != "WEB_SEARCH":
            return self._deny(
                "Разрешён только WEB_SEARCH."
            )

        query = action.parameters.get(
            "query"
        )

        if not query or not str(
            query
        ).strip():
            return self._deny(
                "Поисковый запрос пуст."
            )

        limit = action.parameters.get(
            "limit",
            5,
        )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return self._deny(
                "Некорректный limit."
            )

        if not 1 <= limit <= 10:
            return self._deny(
                "limit должен быть от 1 до 10."
            )

        return self._allow(
            "WEB_SEARCH разрешён."
        )

    def _inside_filesystem(
        self,
        path: str,
    ) -> bool:
        try:
            candidate = Path(path)

            if not candidate.is_absolute():
                candidate = (
                    self.filesystem_root
                    / candidate
                )

            resolved = candidate.resolve()

            return (
                resolved == self.filesystem_root
                or self.filesystem_root
                in resolved.parents
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            return False

    def _allow(
        self,
        reason: str,
    ):
        return {
            "allowed": True,
            "reason": reason,
        }

    def _deny(
        self,
        reason: str,
    ):
        return {
            "allowed": False,
            "reason": reason,
        }
