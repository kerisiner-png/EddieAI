import re
from pathlib import Path
from typing import Optional


class CommandPolicy:
    """Анти-катастрофическая страховка для команд терминала.

    Проверяет команды на наличие опасных паттернов (denylist).
    Allowlist опционален — если задан, команда должна совпасть
    с хотя бы одним паттерном.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
    ):
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent
                / "config"
                / "commands.yaml"
            )
        self._config_path = config_path
        self._allowlist = []
        self._denylist = []
        self._load_config()

    def _load_config(self):
        try:
            import yaml
            with open(
                self._config_path,
                "r",
                encoding="utf-8",
            ) as f:
                config = yaml.safe_load(f)
        except (
            FileNotFoundError,
            ImportError,
        ):
            config = self._default_config()

        self._allowlist = config.get(
            "allowlist", []
        )
        self._denylist = config.get(
            "denylist", []
        )

    def _default_config(self):
        return {
            "allowlist": [],
            "denylist": [],
        }

    def is_safe(
        self,
        command: str,
    ) -> bool:
        """Проверить, безопасна ли команда.

        Режим свободы (решение Эдди 04.09): белый список
        отменён, «всё можно что захочет». Блокируется только
        анти-катастрофический denylist (форматирование,
        рекурсивное удаление системного и т.п.).
        """
        if not command or not command.strip():
            return False
        return not self.is_destructive(command)

    def is_destructive(
        self,
        command: str,
    ) -> bool:
        """Проверить только анти-катастрофический denylist.

        Свободный режим (ИНСТР-2/3): команда разрешена
        если не содержит разрушительных паттернов,
        независимо от allowlist.
        """
        if not command or not command.strip():
            return True
        return self._matches_denylist(command.strip())

    def destructive_reason(
        self,
        command: str,
    ) -> Optional[str]:
        """Причина блокировки по denylist
        или None если разрушительного нет."""
        if not command or not command.strip():
            return "Пустая команда"
        for entry in self._denylist:
            pattern = entry.get("pattern", "")
            if re.search(
                pattern,
                command.strip(),
                re.IGNORECASE,
            ):
                return entry.get(
                    "reason",
                    "Заблокировано denylist",
                )
        return None

    def _matches_denylist(
        self,
        command: str,
    ) -> bool:
        for entry in self._denylist:
            pattern = entry.get("pattern", "")
            if re.search(
                pattern,
                command,
                re.IGNORECASE,
            ):
                return True
        return False

    def _matches_allowlist(
        self,
        command: str,
    ) -> bool:
        for entry in self._allowlist:
            pattern = entry.get("pattern", "")
            if re.search(
                pattern,
                command,
                re.IGNORECASE,
            ):
                return True
        return False

    def deny_reason(
        self,
        command: str,
    ) -> Optional[str]:
        """Вернуть причину блокировки
        или None если команда безопасна."""
        return self.destructive_reason(command)
