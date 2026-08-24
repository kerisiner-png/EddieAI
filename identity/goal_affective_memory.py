from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class GoalAffectiveProfile:
    goal: str
    observations: int
    positive_score: float
    negative_score: float
    valence: float
    emotions: dict[str, float]


class GoalAffectiveMemory:
    """
    Persistent association between goals and affective reactions.

    Stores what EddieAI actually experienced while pursuing
    a concrete goal. It does not infer emotions from goal text.
    """

    POSITIVE_EMOTIONS = {
        "joy",
        "interest",
        "curiosity",
        "satisfaction",
    }

    NEGATIVE_EMOTIONS = {
        "sadness",
        "fear",
        "anger",
        "disgust",
        "frustration",
    }

    IGNORED_EMOTIONS = {
        "surprise",
        "uncertainty",
    }

    def __init__(self, memory):
        self.memory = memory
        self._ensure_table()

    def _ensure_table(self):
        self.memory.connection.execute("""
            CREATE TABLE IF NOT EXISTS goal_affective_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                emotion TEXT NOT NULL,
                delta REAL NOT NULL,
                trigger TEXT,
                created_at TEXT NOT NULL
            )
        """)

        self.memory.connection.commit()

    def record(
        self,
        *,
        goal: str,
        changes: dict[str, float],
        trigger: str | None = None,
    ) -> int:
        goal = str(
            goal or ""
        ).strip()

        if not goal:
            return 0

        if not isinstance(
            changes,
            dict,
        ):
            return 0

        created = 0
        timestamp = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        for emotion, raw_delta in changes.items():
            try:
                delta = float(
                    raw_delta
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if delta == 0:
                continue

            self.memory.connection.execute(
                """
                INSERT INTO goal_affective_events (
                    goal,
                    emotion,
                    delta,
                    trigger,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    goal,
                    str(emotion),
                    delta,
                    trigger,
                    timestamp,
                ),
            )

            created += 1

        if created:
            self.memory.connection.commit()

        return created

    def profile(
        self,
        goal: str,
    ) -> GoalAffectiveProfile:
        goal = str(
            goal or ""
        ).strip()

        rows = self.memory.connection.execute(
            """
            SELECT emotion, delta
            FROM goal_affective_events
            WHERE lower(goal) = lower(?)
            ORDER BY id ASC
            """,
            (goal,),
        ).fetchall()

        emotions = {}
        observations = 0

        for row in rows:
            emotion = str(
                row["emotion"]
            )

            delta = float(
                row["delta"]
            )

            emotions[emotion] = (
                emotions.get(
                    emotion,
                    0.0,
                )
                + delta
            )

            observations += 1

        positive = sum(
            value
            for emotion, value
            in emotions.items()
            if emotion
            in self.POSITIVE_EMOTIONS
            and value > 0
        )

        negative = sum(
            abs(value)
            for emotion, value
            in emotions.items()
            if emotion
            in self.NEGATIVE_EMOTIONS
            and value > 0
        )

        total = (
            positive
            + negative
        )

        if total <= 0:
            valence = 0.0
        else:
            valence = (
                positive - negative
            ) / total

        return GoalAffectiveProfile(
            goal=goal,
            observations=observations,
            positive_score=round(
                positive,
                4,
            ),
            negative_score=round(
                negative,
                4,
            ),
            valence=round(
                max(
                    -1.0,
                    min(
                        1.0,
                        valence,
                    ),
                ),
                4,
            ),
            emotions={
                key: round(
                    value,
                    4,
                )
                for key, value
                in emotions.items()
            },
        )

    def bias(
        self,
        goal: str,
        maximum: float = 0.15,
    ) -> float:
        profile = self.profile(
            goal
        )

        if profile.observations <= 0:
            return 0.0

        # Early observations should influence behavior,
        # but should not overpower rational goal scoring.
        experience_factor = min(
            1.0,
            profile.observations / 8.0,
        )

        value = (
            profile.valence
            * 0.10
            * experience_factor
        )

        return round(
            max(
                -maximum,
                min(
                    maximum,
                    value,
                ),
            ),
            4,
        )
