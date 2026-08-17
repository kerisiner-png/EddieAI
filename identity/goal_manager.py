from datetime import datetime, timezone

from identity.goal import (
    Goal,
    VALID_STATUSES,
)
from identity.goal_planner import GoalPlanner


class GoalManager:
    """
    Управляет жизненным циклом целей.

    При активации цели автоматически создаёт план,
    если для неё уже определён план.
    """

    MAX_ACTIVE_GOALS = 3

    def __init__(
        self,
        self_state,
        planner=None,
    ):
        self.self_state = self_state

        self.planner = (
            planner
            if planner is not None
            else GoalPlanner(self_state)
        )

        if self.self_state.get("goals_state") is None:
            self.self_state.set(
                "goals_state",
                {}
            )

    def _goals(self) -> dict:
        return self.self_state.get(
            "goals_state",
            {}
        )

    def _save(
        self,
        goals: dict,
    ):
        self.self_state.set(
            "goals_state",
            goals
        )

    def _key(
        self,
        value: str,
    ) -> str:
        return value.strip().lower()

    def get(
        self,
        value: str,
    ):
        data = self._goals().get(
            self._key(value)
        )

        if data is None:
            return None

        return Goal(
            value=data["value"],
            status=data["status"],
            priority=float(
                data["priority"]
            ),
            motivation=float(
                data["motivation"]
            ),
            confidence=float(
                data["confidence"]
            ),
            created_at=data.get(
                "created_at"
            ),
            updated_at=data.get(
                "updated_at"
            ),
            progress=float(
                data.get("progress", 0.0)
            ),
            source=data.get(
                "source",
                "self",
            ),
        )

    def all(self):
        result = []

        for data in self._goals().values():
            result.append(
                Goal(
                    value=data["value"],
                    status=data["status"],
                    priority=float(
                        data["priority"]
                    ),
                    motivation=float(
                        data["motivation"]
                    ),
                    confidence=float(
                        data["confidence"]
                    ),
                    created_at=data.get(
                        "created_at"
                    ),
                    updated_at=data.get(
                        "updated_at"
                    ),
                    progress=float(
                        data.get(
                            "progress",
                            0.0,
                        )
                    ),
                    source=data.get(
                        "source",
                        "self",
                    ),
                )
            )

        return result

    def active(self):
        return [
            goal
            for goal in self.all()
            if goal.status == "ACTIVE"
        ]

    def add_candidate(
        self,
        value: str,
        motivation: float,
        priority: float,
        confidence: float,
        source: str = "self",
    ):
        existing = self.get(value)

        if existing is not None:
            return existing

        goal = Goal(
            value=value,
            status="CANDIDATE",
            motivation=motivation,
            priority=priority,
            confidence=confidence,
            source=source,
        )

        self._write(goal)

        return goal

    def activate(
        self,
        value: str,
        plan: list[str] | None = None,
    ):
        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        active = self.active()

        if (
            goal.status != "ACTIVE"
            and len(active)
            >= self.MAX_ACTIVE_GOALS
        ):
            return {
                "status": "DEFERRED",
                "reason": (
                    "Достигнут лимит "
                    "активных целей."
                ),
                "goal": goal,
            }

        goal.status = "ACTIVE"
        goal.updated_at = self._now()

        self._write(goal)

        # Если план передан при активации,
        # создаём его автоматически.
        if plan:
            self.planner.create_plan(
                goal=goal.value,
                tasks=plan,
            )

        return {
            "status": "ACTIVATED",
            "goal": goal,
            "plan": (
                self.planner.get_plan(
                    goal.value
                )
                if plan
                else None
            ),
        }

    def ensure_plan(
        self,
        value: str,
        tasks: list[str],
    ):
        """
        Создаёт план для существующей цели,
        если его ещё нет.
        """

        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        existing = self.planner.get_plan(
            value
        )

        if existing is not None:
            return existing

        return self.planner.create_plan(
            goal=value,
            tasks=tasks,
        )

    def current_task(
        self,
        value: str,
    ):
        return self.planner.next_task(
            value
        )

    def activate_next_task(
        self,
        value: str,
    ):
        return self.planner.activate_next(
            value
        )

    def pause(
        self,
        value: str,
    ):
        return self._set_status(
            value,
            "PAUSED",
        )

    def abandon(
        self,
        value: str,
    ):
        return self._set_status(
            value,
            "ABANDONED",
        )

    def complete(
        self,
        value: str,
    ):
        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        goal.status = "COMPLETED"
        goal.progress = 1.0
        goal.updated_at = self._now()

        self._write(goal)

        return goal

    def update_progress(
        self,
        value: str,
        progress: float,
    ):
        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        goal.progress = max(
            0.0,
            min(1.0, progress),
        )

        if goal.progress >= 1.0:
            goal.status = "COMPLETED"

        goal.updated_at = self._now()

        self._write(goal)

        return goal

    def sync_progress(
        self,
        value: str,
    ):
        """
        Синхронизирует общий прогресс цели
        с прогрессом её плана.
        """

        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        progress = self.planner.plan_progress(
            value
        )

        goal.progress = progress

        if self.planner.is_complete(value):
            goal.status = "COMPLETED"
            goal.progress = 1.0

        goal.updated_at = self._now()

        self._write(goal)

        return goal

    def rank_candidates(self):
        goals = [
            goal
            for goal in self.all()
            if goal.status in {
                "CANDIDATE",
                "PAUSED",
            }
        ]

        return sorted(
            goals,
            key=lambda goal: (
                goal.priority * 0.45
                + goal.motivation * 0.35
                + goal.confidence * 0.20
            ),
            reverse=True,
        )

    def best_candidate(self):
        candidates = self.rank_candidates()

        if not candidates:
            return None

        return candidates[0]

    def _set_status(
        self,
        value: str,
        status: str,
    ):
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid goal status: {status}"
            )

        goal = self.get(value)

        if goal is None:
            raise ValueError(
                f"Goal does not exist: {value}"
            )

        goal.status = status
        goal.updated_at = self._now()

        self._write(goal)

        return goal

    def _write(
        self,
        goal: Goal,
    ):
        goals = self._goals()

        goals[
            self._key(goal.value)
        ] = goal.to_dict()

        self._save(goals)

    def _now(self):
        return datetime.now(
            timezone.utc
        ).isoformat()
