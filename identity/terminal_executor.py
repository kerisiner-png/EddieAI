import subprocess
import sys
import threading
from typing import Optional


class TerminalExecutor:
    """Безопасное выполнение команд через терминал.

    Выполняет команды через subprocess с:
    - Таймаутом (30 сек)
    - Захватом stdout/stderr
    - Ограничением размера вывода (50KB)
    - Кодировкой UTF-8
    """

    DEFAULT_TIMEOUT = 30
    MAX_OUTPUT_BYTES = 50 * 1024

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_output_bytes: int = MAX_OUTPUT_BYTES,
        default_cwd: Optional[str] = None,
    ):
        self._timeout = timeout
        self._max_output_bytes = max_output_bytes
        self._default_cwd = default_cwd

    def _kill_tree(
        self,
        proc: subprocess.Popen,
    ):
        """Убить всё дерево процессов (Windows)."""
        if sys.platform == "win32":
            subprocess.run(
                f"taskkill /F /T /PID {proc.pid}",
                shell=True,
                capture_output=True,
            )
        else:
            proc.kill()

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """Выполнить команду и вернуть результат.

        Returns:
            dict с ключами:
            - status: "OK" | "TIMEOUT" | "ERROR"
            - stdout: str (обрезанный до max_output_bytes)
            - stderr: str
            - exit_code: int | None
            - command: str (оригинальная команда)
        """
        if not command or not command.strip():
            return {
                "status": "ERROR",
                "stdout": "",
                "stderr": "Пустая команда",
                "exit_code": None,
                "command": command,
            }

        effective_cwd = cwd or self._default_cwd
        effective_timeout = timeout or self._timeout

        timed_out = [False]

        def on_timeout():
            timed_out[0] = True
            self._kill_tree(proc)

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=effective_cwd,
                encoding="utf-8",
                errors="replace",
            )

            timer = threading.Timer(
                effective_timeout,
                on_timeout,
            )
            timer.start()

            stdout_raw, stderr_raw = proc.communicate()
            timer.cancel()

            if timed_out[0]:
                return {
                    "status": "TIMEOUT",
                    "stdout": "",
                    "stderr": (
                        f"Команда превысила таймаут "
                        f"{effective_timeout}с"
                    ),
                    "exit_code": None,
                    "command": command,
                }

            stdout = stdout_raw[
                : self._max_output_bytes
            ]
            stderr = stderr_raw[
                : self._max_output_bytes
            ]

            return {
                "status": "OK",
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": proc.returncode,
                "command": command,
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "stdout": "",
                "stderr": str(e),
                "exit_code": None,
                "command": command,
            }
