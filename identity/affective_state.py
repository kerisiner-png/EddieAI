from datetime import datetime, timezone


DECAY_HALF_LIFE_SECONDS = {
    "joy": 900.0,
    "sadness": 3600.0,
    "fear": 1200.0,
    "anger": 900.0,
    "disgust": 1800.0,
    "surprise": 120.0,
    "interest": 1800.0,
    "curiosity": 2400.0,
    "frustration": 1200.0,
    "uncertainty": 2400.0,
    "satisfaction": 1800.0,
}


DEFAULT_EMOTIONS = {
    "joy": 0.0,
    "sadness": 0.0,
    "fear": 0.0,
    "anger": 0.0,
    "disgust": 0.0,
    "surprise": 0.0,
    "interest": 0.0,
    "curiosity": 0.0,
    "frustration": 0.0,
    "uncertainty": 0.0,
    "satisfaction": 0.0,
}


class AffectiveState:
    """
    Текущее функциональное эмоциональное состояние EddieAI.

    Состояние возникает как реакция на события.
    Этот класс не определяет психологический смысл реакции.
    Он хранит динамическое состояние и его историю.
    """

    def __init__(
        self,
        self_state,
    ):
        self.self_state = self_state
        self._ensure_state()

    def _ensure_state(self):
        state = self.self_state.get(
            "emotional_state",
            {},
        )

        if not isinstance(
            state,
            dict,
        ):
            state = {}

        emotions = state.get(
            "emotions",
            {},
        )

        if not isinstance(
            emotions,
            dict,
        ):
            emotions = {}

        history = state.get(
            "history",
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            history = []

        changed = False

        for name, value in DEFAULT_EMOTIONS.items():
            if name not in emotions:
                emotions[name] = float(value)
                changed = True

        if "updated_at" not in state:
            state["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            changed = True

        state["emotions"] = emotions
        state["history"] = history

        if changed:
            self.self_state.set(
                "emotional_state",
                state,
            )

    def snapshot(self) -> dict:
        state = self.self_state.get(
            "emotional_state",
            {},
        )

        emotions = state.get(
            "emotions",
            {},
        )

        return {
            "emotions": {
                key: float(value)
                for key, value in emotions.items()
            },
            "updated_at": state.get(
                "updated_at"
            ),
            "history": list(
                state.get(
                    "history",
                    [],
                )
            ),
        }

    def get(
        self,
        name: str,
    ) -> float:
        return float(
            self.snapshot()[
                "emotions"
            ].get(
                name,
                0.0,
            )
        )

    def set(
        self,
        name: str,
        intensity: float,
    ):
        if name not in DEFAULT_EMOTIONS:
            raise ValueError(
                f"Unknown affective state: {name}"
            )

        intensity = max(
            0.0,
            min(
                1.0,
                float(intensity),
            ),
        )

        state = self.snapshot()

        state["emotions"][name] = intensity

        state["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.self_state.set(
            "emotional_state",
            state,
        )

        return self.snapshot()

    def adjust(
        self,
        name: str,
        delta: float,
    ):
        return self.set(
            name,
            self.get(name) + float(delta),
        )

    def apply_reaction(
        self,
        *,
        changes: dict[str, float],
        trigger: str,
        reason: str,
        source: str,
        metadata: dict | None = None,
    ):
        state = self.snapshot()

        for name, delta in changes.items():
            if name not in DEFAULT_EMOTIONS:
                raise ValueError(
                    f"Unknown affective state: {name}"
                )

            current = float(
                state["emotions"].get(
                    name,
                    0.0,
                )
            )

            state["emotions"][name] = max(
                0.0,
                min(
                    1.0,
                    current + float(delta),
                ),
            )

        timestamp = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        state["updated_at"] = timestamp

        state["history"].append({
            "timestamp": timestamp,
            "trigger": trigger,
            "reason": reason,
            "source": source,
            "changes": {
                key: float(value)
                for key, value in changes.items()
            },
            "metadata": (
                metadata
                if isinstance(
                    metadata,
                    dict,
                )
                else {}
            ),
        })

        # Не даём истории разрастаться бесконечно.
        state["history"] = state[
            "history"
        ][-100:]

        self.self_state.set(
            "emotional_state",
            state,
        )

        return self.snapshot()

    def decay(
        self,
        *,
        now: datetime | None = None,
    ):
        """
        Постепенно возвращает текущее affective state
        к baseline.

        История реакций не изменяется.

        Decay основан на времени, прошедшем с последнего
        изменения affective state.
        """

        now = (
            now
            or datetime.now(
                timezone.utc
            )
        )

        state = self.snapshot()

        updated_at = state.get(
            "updated_at"
        )

        if not updated_at:
            return state

        try:
            previous = datetime.fromisoformat(
                updated_at
            )
        except (
            TypeError,
            ValueError,
        ):
            return state

        if previous.tzinfo is None:
            previous = previous.replace(
                tzinfo=timezone.utc
            )

        elapsed = (
            now - previous
        ).total_seconds()

        if elapsed <= 0:
            return state

        changed = False

        for name, intensity in state[
            "emotions"
        ].items():

            half_life = (
                DECAY_HALF_LIFE_SECONDS.get(
                    name,
                    1800.0,
                )
            )

            if intensity <= 0.0:
                continue

            factor = (
                0.5
                ** (
                    elapsed
                    / half_life
                )
            )

            new_intensity = (
                intensity * factor
            )

            # Не создаём микроскопические хвосты.
            if new_intensity < 0.001:
                new_intensity = 0.0

            if abs(
                new_intensity - intensity
            ) >= 0.0001:
                state["emotions"][
                    name
                ] = new_intensity
                changed = True

        if not changed:
            return state

        state["updated_at"] = (
            now.isoformat()
        )

        self.self_state.set(
            "emotional_state",
            state,
        )

        return self.snapshot()

    def reset(
        self,
        name: str | None = None,
    ):
        state = self.snapshot()

        if name is None:
            for key in DEFAULT_EMOTIONS:
                state["emotions"][key] = 0.0
        else:
            if name not in DEFAULT_EMOTIONS:
                raise ValueError(
                    f"Unknown affective state: {name}"
                )

            state["emotions"][name] = 0.0

        state["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.self_state.set(
            "emotional_state",
            state,
        )

        return self.snapshot()
