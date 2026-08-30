import time
from datetime import datetime, timezone


DEFAULT_LIFE_STATE = {
    "asleep": False,
    "fatigue": 0.0,
    "awake_since": None,
    "asleep_since": None,
    "sleep_count": 0,
    "wake_count": 0,
    "updated_at": None,
}

# Социальная норма 23:00–07:00 — только мягкая подсказка
# (ускорение накопления усталости), не принуждение.
SLEEP_WINDOW_START = 23
SLEEP_WINDOW_END = 7
NIGHT_FATIGUE_MULTIPLIER = 1.6

# Скорости усталости и пороги. Свобода: EddieAI сам решает,
# когда и сколько спать; активная задача откладывает сон.
FATIGUE_GAIN_PER_HOUR_AWAKE = 0.10
FATIGUE_LOSS_PER_HOUR_SLEEP = 0.35
SLEEP_THRESHOLD = 0.80
HARD_SLEEP_THRESHOLD = 1.0
WAKE_THRESHOLD = 0.25
ACTIVE_TASK_EXTRA = 0.15

MAX_DT_HOURS = 6.0
SAVE_INTERVAL_SECONDS = 300


class LifeCycle:
    """
    Режим жизни: свободный сон/бодрствование.

    Сон и пробуждение — решение самой личности, а не расписание.
    Социальная норма 23:00–07:00 лишь ускоряет усталость в это время
    (подсказка «обычно в это время спят»), но не принуждает.
    Усталость копится в бодрствовании (ночью быстрее) и спадает во сне.
    """

    def __init__(
        self,
        self_state,
        night_boost=NIGHT_FATIGUE_MULTIPLIER,
    ):
        self.self_state = self_state
        self.night_boost = night_boost

        state = self_state.get("life_state")
        if not isinstance(state, dict):
            state = {}

        merged = dict(DEFAULT_LIFE_STATE)
        merged.update(state)
        self.state = merged

        if self_state.get("life_state") is None:
            self_state.set("life_state", dict(self.state))

        self._last_save = time.time()

    def is_asleep(self) -> bool:
        return bool(self.state.get("asleep"))

    def state_dict(self) -> dict:
        return dict(self.state)

    def in_sleep_window(self, now) -> bool:
        return (
            now.hour >= SLEEP_WINDOW_START
            or now.hour < SLEEP_WINDOW_END
        )

    def _has_active_task(self) -> bool:
        goals_state = self.self_state.get(
            "goals_state"
        ) or {}

        for value in goals_state.values():
            if (
                isinstance(value, dict)
                and str(value.get("status"))
                == "ACTIVE"
            ):
                return True

        return False

    def update(
        self,
        now=None,
        has_active_task=None,
    ) -> dict:
        now = now or datetime.now(
            timezone.utc
        ).astimezone()

        last = self.state.get("updated_at")

        if last is None:
            self.state["updated_at"] = (
                now.isoformat()
            )
            return self.state_dict()

        try:
            last_dt = datetime.fromisoformat(
                last
            )
        except (TypeError, ValueError):
            last_dt = now

        dt_seconds = (
            now - last_dt
        ).total_seconds()

        dt_hours = max(
            0.0,
            min(
                dt_seconds / 3600.0,
                MAX_DT_HOURS,
            ),
        )

        if dt_hours <= 0:
            return self.state_dict()

        if has_active_task is None:
            has_active_task = (
                self._has_active_task()
            )

        asleep = self.is_asleep()
        was_asleep = asleep

        fatigue = float(
            self.state.get("fatigue", 0.0)
        )

        if asleep:
            fatigue -= (
                FATIGUE_LOSS_PER_HOUR_SLEEP
                * dt_hours
            )
            fatigue = max(0.0, fatigue)

            if fatigue <= WAKE_THRESHOLD:
                asleep = False
                self.state["wake_count"] = (
                    int(
                        self.state.get(
                            "wake_count",
                            0,
                        )
                    )
                    + 1
                )
                self.state["asleep_since"] = None
                self.state["awake_since"] = (
                    now.isoformat()
                )
        else:
            gain = (
                FATIGUE_GAIN_PER_HOUR_AWAKE
                * dt_hours
            )

            if self.in_sleep_window(now):
                gain *= self.night_boost

            fatigue += gain
            fatigue = min(fatigue, 1.0)

            threshold = SLEEP_THRESHOLD

            if has_active_task:
                threshold += ACTIVE_TASK_EXTRA

            if (
                fatigue >= HARD_SLEEP_THRESHOLD
                or (
                    fatigue >= threshold
                    and not has_active_task
                )
            ):
                asleep = True
                self.state["sleep_count"] = (
                    int(
                        self.state.get(
                            "sleep_count",
                            0,
                        )
                    )
                    + 1
                )
                self.state["awake_since"] = None
                self.state["asleep_since"] = (
                    now.isoformat()
                )

        self.state["fatigue"] = fatigue
        self.state["asleep"] = asleep
        self.state["updated_at"] = (
            now.isoformat()
        )

        if was_asleep != asleep:
            self._save()
        elif dt_seconds >= SAVE_INTERVAL_SECONDS:
            self._save()

        return self.state_dict()

    def force_sleep(self, now=None) -> dict:
        now = now or datetime.now(
            timezone.utc
        ).astimezone()

        if not self.is_asleep():
            self.state["asleep"] = True
            self.state["sleep_count"] = (
                int(
                    self.state.get(
                        "sleep_count",
                        0,
                    )
                )
                + 1
            )
            self.state["awake_since"] = None
            self.state["asleep_since"] = (
                now.isoformat()
            )
            self._save()

        return self.state_dict()

    def force_wake(self, now=None) -> dict:
        now = now or datetime.now(
            timezone.utc
        ).astimezone()

        if self.is_asleep():
            self.state["asleep"] = False
            self.state["wake_count"] = (
                int(
                    self.state.get(
                        "wake_count",
                        0,
                    )
                )
                + 1
            )
            self.state["asleep_since"] = None
            self.state["awake_since"] = (
                now.isoformat()
            )
            self.state["fatigue"] = min(
                float(
                    self.state.get("fatigue", 0.0)
                ),
                WAKE_THRESHOLD,
            )
            self._save()

        return self.state_dict()

    def _save(self):
        try:
            self.self_state.set(
                "life_state",
                dict(self.state),
            )
        except Exception:
            pass