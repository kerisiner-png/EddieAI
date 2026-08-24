from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import threading

_DEFAULT_QUEUE_DIR = Path(
    os.environ.get("EDDIE_DATA_DIR")
    or (
        Path(__file__).resolve().parent.parent
        / "data"
    )
)


@dataclass
class CognitiveItem:
    id: str
    content: str
    route: str
    reason: str
    created_at: str
    status: str = "PENDING"
    attempts: int = 0
    analysis: str | None = None


class CognitiveQueue:
    """
    Persistent очередь значимых когнитивных событий.

    PENDING   — ждёт анализа
    PROCESSING — анализируется в фоне
    ANALYZED  — анализ готов, ждёт применения
    DONE      — решение применено
    DEFERRED  — сознательно отложено
    FAILED    — обработка завершилась ошибкой
    """

    def __init__(
        self,
        path: str | None = None,
    ):
        if path is None:
            path = (
                _DEFAULT_QUEUE_DIR
                / "cognitive_queue.json"
            )

        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()
        self.items = self._load()

    def _load(self):
        if not self.path.exists():
            return []

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            return [
                CognitiveItem(**item)
                for item in data
            ]

        except Exception:
            return []

    def _save(self):
        payload = [
            asdict(item)
            for item in self.items
        ]

        temp_path = self.path.with_suffix(
            ".tmp"
        )

        temp_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temp_path.replace(self.path)

    def _make_id(
        self,
        content: str,
        route: str,
    ) -> str:
        raw = (
            f"{route}\n{content}"
        )

        return sha256(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    def enqueue(
        self,
        *,
        content: str,
        route: str,
        reason: str,
    ) -> CognitiveItem:

        with self._lock:
            item_id = self._make_id(
                content,
                route,
            )

            for item in self.items:
                if item.id == item_id:
                    return item

            item = CognitiveItem(
                id=item_id,
                content=content,
                route=route,
                reason=reason,
                created_at=(
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            )

            self.items.append(item)
            self._save()

            return item

    def pending(self):
        with self._lock:
            return [
                item
                for item in self.items
                if item.status == "PENDING"
            ]

    def analyzed(self):
        with self._lock:
            return [
                item
                for item in self.items
                if item.status == "ANALYZED"
            ]

    def next(self):
        with self._lock:
            pending = self.pending()

            if not pending:
                return None

            item = pending[0]

            item.status = "PROCESSING"
            item.attempts += 1

            self._save()

            return item

    def save_analysis(
        self,
        item_id: str,
        analysis: str,
    ):
        with self._lock:
            item = self.get(item_id)

            if item is None:
                return None

            item.analysis = analysis
            item.status = "ANALYZED"

            self._save()

            return item

    def complete(
        self,
        item_id: str,
        analysis: str | None = None,
    ):
        with self._lock:
            item = self.get(item_id)

            if item is None:
                return None

            item.status = "DONE"

            if analysis is not None:
                item.analysis = analysis

            self._save()

            return item

    def defer(
        self,
        item_id: str,
    ):
        with self._lock:
            item = self.get(item_id)

            if item is None:
                return None

            item.status = "DEFERRED"
            self._save()

            return item

    def fail(
        self,
        item_id: str,
    ):
        with self._lock:
            item = self.get(item_id)

            if item is None:
                return None

            item.status = "FAILED"
            self._save()

            return item

    def get(
        self,
        item_id: str,
    ):
        for item in self.items:
            if item.id == item_id:
                return item

        return None

    def stats(self):
        with self._lock:
            result = {}

            for item in self.items:
                result[item.status] = (
                    result.get(item.status, 0)
                    + 1
                )

            return result
