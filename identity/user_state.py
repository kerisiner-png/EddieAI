import json
import re
from pathlib import Path
from typing import Any


STATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "user_state.json"
)


DEFAULT_STATE = {
    "name": "Эдди",
    "age": None,
    "interests": [],
    "preferences": [],
    "habits": [],
}


class UserState:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():
            self._save(DEFAULT_STATE)

        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _save(self, data: dict[str, Any]):
        with self.path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

    def get(
        self,
        key: str,
        default=None,
    ):
        return self.data.get(
            key,
            default,
        )

    def set(
        self,
        key: str,
        value,
    ):
        self.data[key] = value
        self._save(self.data)

    def update_from_message(
        self,
        message: str,
    ) -> list[dict[str, Any]]:
        """
        Извлекает только явно сообщённые пользователем
        простые факты.

        Возвращает список реально изменённых полей.
        """

        changes = []

        text = message.strip()

        age_patterns = [
            r"\bмне\s+(?:уже\s+)?(\d{1,3})\b",
            r"\bмне\s+исполн(?:илось|яется)\s+(\d{1,3})\b",
            r"\bмне\s+(\d{1,3})\s+лет\b",
            r"\bмой\s+возраст\s*[:\-—]?\s*(\d{1,3})\b",
        ]

        for pattern in age_patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if not match:
                continue

            age = int(match.group(1))

            if not 1 <= age <= 120:
                continue

            old_age = self.get("age")

            if old_age != age:
                self.set(
                    "age",
                    age,
                )

                changes.append({
                    "field": "age",
                    "old_value": old_age,
                    "new_value": age,
                    "source_text": message,
                })

            break

        return changes

    def snapshot(self):
        return json.loads(
            json.dumps(
                self.data,
                ensure_ascii=False,
            )
        )
