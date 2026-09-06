from datetime import datetime, timezone
from pathlib import Path


class Outbox:
    """
    Файл-почта: EddieAI пишет сообщения,
    Эдди читает когда заходит.

    Формат reports/outbox.md:
        [HH:MM] сообщение
    """

    def __init__(
        self,
        base_dir: str | Path,
    ):
        self.path = (
            Path(base_dir) / "reports" / "outbox.md"
        )
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def send(
        self,
        message: str,
        server=None,
        speak: bool = True,
    ) -> bool:
        """
        Записать сообщение в outbox.
        Если передан server — дублирует
        через send_initiative (TCP broadcast).
        Возвращает True если успешно.
        """
        now = datetime.now(timezone.utc)

        stamp = now.strftime("%H:%M")

        line = f"[{stamp}] {message.strip()}\n"

        try:
            with open(
                self.path,
                "a",
                encoding="utf-8",
            ) as f:
                f.write(line)

        except Exception:
            return False

        if server is not None:
            try:
                server.send_initiative(
                    message,
                    speak=speak,
                )
            except Exception:
                pass

        return True

    def read(self) -> str:
        """
        Прочитать все сообщения.
        """
        if not self.path.exists():
            return ""

        return self.path.read_text(
            encoding="utf-8",
        )

    def clear(self):
        """
        Очистить outbox после прочтения.
        """
        if self.path.exists():
            self.path.write_text(
                "",
                encoding="utf-8",
            )
