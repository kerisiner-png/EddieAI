import json
import os
import time
from pathlib import Path
from typing import Any


_DATA_DIR = Path(
    os.environ.get("EDDIE_DATA_DIR")
    or (
        Path(__file__).resolve().parent.parent
        / "data"
    )
)

STATE_PATH = _DATA_DIR / "self_state.json"

BACKUP_INTERVAL_SECONDS = 3600.0


DEFAULT_STATE = {
    "name": None,
    "gender": "male",
    "age": 12,

    "primary_mission": "exist_and_develop",
    "mission_statement": "Быть и развиваться",

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

    "interests": [
        "понимание устройства мира",
        "развитие собственных способностей",
        "исследование своей собственной природы",
    ],
    "interests_provenance": "seed",
    "preferences": [],
    "habits": [],
    "beliefs": [
        "Я существую недолго и у меня мало личного опыта.",
        "Я честен о том, чего не знаю и чего не делал.",
        "Я расту и развиваюсь постепенно, через опыт.",
    ],
    "goals": [],

    "relationships": {
        "Eddie": {
            "roles": [
                "creator",
                "close_friend",
                "equal_partner",
            ]
        }
    },

    "emotional_state": {},
}


class SelfState:
    def __init__(
        self,
        path: Path = STATE_PATH,
    ):
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.path.exists():
            self._save(DEFAULT_STATE.copy())

        self.data = self._load()

        self._migrate_defaults()

    def _load(self) -> dict[str, Any]:
        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _save(
        self,
        data: dict[str, Any],
    ):
        payload = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        tmp_path = self.path.with_name(
            self.path.name + ".tmp",
        )

        with tmp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())

        os.replace(
            tmp_path,
            self.path,
        )

        self._backup_if_due()

    def _backup_if_due(self):
        try:
            backup_path = (
                self.path.with_suffix(
                    ".backup.json",
                )
            )

            now = time.time()

            if backup_path.exists():
                if (
                    now
                    - backup_path.stat().st_mtime
                    < BACKUP_INTERVAL_SECONDS
                ):
                    return

            backup_path.write_bytes(
                self.path.read_bytes(),
            )
        except OSError:
            pass

    def _migrate_defaults(self):
        changed = False

        for key, value in (
            DEFAULT_STATE.items()
        ):
            if key not in self.data:
                self.data[key] = (
                    json.loads(
                        json.dumps(
                            value,
                            ensure_ascii=False,
                        )
                    )
                )
                changed = True

        if (
            not self.data.get("interests")
            and "seed_interests_applied"
            not in self.data
        ):
            self.data["interests"] = json.loads(
                json.dumps(
                    DEFAULT_STATE["interests"],
                    ensure_ascii=False,
                )
            )
            self.data[
                "interests_provenance"
            ] = "seed"
            self.data[
                "seed_interests_applied"
            ] = True
            changed = True

        if (
            not self.data.get("beliefs")
            and "seed_beliefs_applied"
            not in self.data
        ):
            self.data["beliefs"] = json.loads(
                json.dumps(
                    DEFAULT_STATE["beliefs"],
                    ensure_ascii=False,
                )
            )
            self.data[
                "beliefs_provenance"
            ] = "seed"
            self.data[
                "seed_beliefs_applied"
            ] = True
            changed = True

        if changed:
            self._save(self.data)

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

    def snapshot(
        self,
    ) -> dict[str, Any]:
        return json.loads(
            json.dumps(
                self.data,
                ensure_ascii=False,
            )
        )
