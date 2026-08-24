from datetime import datetime, timezone


class AffectiveSelfObserver:
    """
    Наблюдает собственное affective state EddieAI.

    Долговременная история сохраняется полностью,
    но обычное наблюдение ограничивается событиями
    текущей runtime-сессии.

    Observer не назначает эмоциональные ярлыки
    и не изменяет состояние.
    """

    def __init__(
        self,
        affective_state,
    ):
        self.affective_state = affective_state

        # Граница текущей сессии наблюдения.
        # Старые эмоциональные события остаются
        # в persistent history, но не считаются
        # текущим опытом.
        self.session_started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    def observe(
        self,
        *,
        since: str | None = None,
        limit: int = 10,
    ) -> dict:

        state = (
            self.affective_state.snapshot()
        )

        history = state.get(
            "history",
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            history = []

        observation_start = (
            since
            if since is not None
            else self.session_started_at
        )

        selected = [
            item
            for item in history
            if str(
                item.get(
                    "timestamp",
                    "",
                )
            ) > str(
                observation_start
            )
        ]

        selected = selected[-max(
            1,
            int(limit),
        ):]

        changes = []

        for event in selected:
            event_changes = event.get(
                "changes",
                {},
            )

            if not isinstance(
                event_changes,
                dict,
            ):
                continue

            for name, delta in event_changes.items():

                try:
                    delta = float(delta)
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                changes.append({
                    "state": name,
                    "delta": delta,
                    "trigger": event.get(
                        "trigger"
                    ),
                    "reason": event.get(
                        "reason"
                    ),
                    "timestamp": event.get(
                        "timestamp"
                    ),
                    "source": event.get(
                        "source"
                    ),
                })

        return {
            "status": "OK",
            "interpretation_status": (
                "UNINTERPRETED"
            ),
            "session_started_at": (
                self.session_started_at
            ),
            "current_state": {
                key: float(value)
                for key, value
                in state.get(
                    "emotions",
                    {},
                ).items()
            },
            "changes": changes,
            "observed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

    def recent_changes(
        self,
        limit: int = 5,
    ) -> list[dict]:

        return self.observe(
            limit=limit
        )["changes"]

    def reset_session(
        self,
    ):
        self.session_started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
