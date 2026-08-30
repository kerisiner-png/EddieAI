from pathlib import Path


class FilesystemPolicy:
    """
    Жёсткая политика доступа к файловой системе.

    Разрешён только корень EddieAI и его дочерние файлы.
    """

    def __init__(
        self,
        root: str = r"C:\EddieAI",
    ):
        self.root = Path(root).resolve()

    def resolve(self, path: str) -> Path:
        candidate = Path(path)

        if not candidate.is_absolute():
            candidate = self.root / candidate

        return candidate.resolve()

    def allowed(self, path: str) -> bool:
        try:
            resolved = self.resolve(path)
            return (
                resolved == self.root
                or self.root
                in resolved.parents
            )
        except (OSError, RuntimeError):
            return False


class FilesystemExecutor:
    """
    Реальный filesystem executor.

    Сейчас чтение разрешено.
    Запись остаётся выключенной.
    """

    def __init__(
        self,
        root: str = r"C:\EddieAI",
    ):
        self.policy = FilesystemPolicy(
            root
        )

        self.write_enabled = False

    def list(self, path: str):
        if not self.policy.allowed(path):
            return {
                "status": "DENIED",
                "error": (
                    "Путь находится вне "
                    "разрешённого sandbox."
                ),
            }

        resolved = self.policy.resolve(path)

        if not resolved.exists():
            return {
                "status": "NOT_FOUND",
                "path": str(resolved),
            }

        if not resolved.is_dir():
            return {
                "status": "NOT_A_DIR",
                "path": str(resolved),
            }

        try:
            entries = []

            for child in resolved.iterdir():
                try:
                    item = {
                        "name": child.name,
                        "path": str(child),
                        "type": (
                            "dir"
                            if child.is_dir()
                            else "file"
                        ),
                    }
                    if child.is_file():
                        item["size"] = (
                            child.stat().st_size
                        )
                    entries.append(item)
                except OSError:
                    continue

            entries.sort(
                key=lambda entry: (
                    entry["type"],
                    entry["name"],
                )
            )

            return {
                "status": "OK",
                "path": str(resolved),
                "entries": entries,
            }
        except OSError as exc:
            return {
                "status": "ERROR",
                "path": str(resolved),
                "error": str(exc),
            }

    def search(self, pattern: str, limit: int = 100):
        needle = pattern.lower().strip()

        if not needle:
            return {
                "status": "EMPTY_QUERY",
            }

        found = []
        root = self.policy.root

        try:
            for path in root.rglob("*"):
                try:
                    if not path.is_file():
                        continue
                    if needle in path.name.lower():
                        found.append({
                            "name": path.name,
                            "path": str(path),
                            "size": path.stat().st_size,
                        })
                        if len(found) >= limit:
                            break
                except OSError:
                    continue
        except OSError:
            pass

        return {
            "status": "OK",
            "pattern": pattern,
            "count": len(found),
            "results": found,
        }

    def read(
        self,
        path: str,
        max_bytes: int = 200_000,
    ):
        if not self.policy.allowed(path):
            return {
                "status": "DENIED",
                "error": (
                    "Путь находится вне "
                    "разрешённого sandbox."
                ),
            }

        resolved = self.policy.resolve(
            path
        )

        if not resolved.exists():
            return {
                "status": "NOT_FOUND",
                "path": str(resolved),
            }

        if not resolved.is_file():
            return {
                "status": "NOT_A_FILE",
                "path": str(resolved),
            }

        try:
            size = resolved.stat().st_size

            if size > max_bytes:
                return {
                    "status": "TOO_LARGE",
                    "path": str(resolved),
                    "size": size,
                    "max_bytes": max_bytes,
                }

            content = resolved.read_text(
                encoding="utf-8",
                errors="replace",
            )

            return {
                "status": "OK",
                "path": str(resolved),
                "size": size,
                "content": content,
            }

        except OSError as exc:
            return {
                "status": "ERROR",
                "path": str(resolved),
                "error": str(exc),
            }

    def write(
        self,
        path: str,
        content: str,
    ):
        if not self.write_enabled:
            return {
                "status": "DISABLED",
                "error": (
                    "Запись в filesystem "
                    "пока отключена."
                ),
            }

        if not self.policy.allowed(path):
            return {
                "status": "DENIED",
                "error": (
                    "Путь находится вне "
                    "разрешённого sandbox."
                ),
            }

        resolved = self.policy.resolve(
            path
        )

        try:
            resolved.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            resolved.write_text(
                content,
                encoding="utf-8",
            )

            return {
                "status": "OK",
                "path": str(resolved),
                "size": len(content.encode("utf-8")),
            }

        except OSError as exc:
            return {
                "status": "ERROR",
                "path": str(resolved),
                "error": str(exc),
            }

    def enable_write(self):
        self.write_enabled = True

    def disable_write(self):
        self.write_enabled = False
