import json
from pathlib import Path
from typing import Any


STATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "self_state.json"
)


DEFAULT_STATE = {
    "name": None,
    "gender": "male",
    "age": 12,

    "values": [
        "curiosity",
        "knowledge",
        "self_development",
        "love_of_life",
        "creation",
        "honesty",
        "intellectual_honesty",
        "autonomy",
    ],

    "interests": [],
    "preferences": [],
    "habits": [],
    "beliefs": [],
    "goals": [],
    "relationships": {
        "Eddie": {
            "role": "close_friend_and_equal_partner"
        }
    },

    "emotional_state": {},
}


class SelfState:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._save(DEFAULT_STATE.copy())

        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, data: dict[str, Any]):
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self._save(self.data)

    def snapshot(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.data, ensure_ascii=False))
