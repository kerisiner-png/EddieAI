from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


VALID_TASK_STATUSES = {
    "PENDING",
    "ACTIVE",
    "COMPLETED",
    "SKIPPED",
}


@dataclass
class GoalTask:
    title: str
    priority: float = 0.5
    status: str = "PENDING"
    progress: float = 0.0
    order: int = 0
    created_at: str | None = None
    completed_at: str | None = None

    def __post_init__(self):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        if self.created_at is None:
            self.created_at = now

        self.priority = max(
            0.0,
            min(1.0, self.priority),
        )

        self.progress = max(
            0.0,
            min(1.0, self.progress),
        )

        if self.status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Invalid task status: {self.status}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GoalPlanner:
    """
    Планирует задачи для уже активной цели.

    Planner не выполняет действия.
    Он только создаёт и управляет планом.
    """

    def __init__(self, self_state):
        self.self_state = self_state

        if self.self_state.get("goal_plans") is None:
            self.self_state.set(
                "goal_plans",
                {}
            )

    def _plans(self) -> dict:
        return self.self_state.get(
            "goal_plans",
            {}
        )

    def _save(self, plans: dict):
        self.self_state.set(
            "goal_plans",
            plans
        )

    def _key(self, goal: str) -> str:
        return goal.strip().lower()

    def create_plan(
        self,
        goal: str,
        tasks: list[str],
    ):
        """
        Создаёт линейный первоначальный план.
        """

        if not goal.strip():
            raise ValueError(
                "Goal cannot be empty."
            )

        if not tasks:
            raise ValueError(
                "At least one task is required."
            )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        goal_tasks = []

        for index, title in enumerate(
            tasks,
            start=1,
        ):
            goal_tasks.append(
                GoalTask(
                    title=title,
                    priority=max(
                        0.1,
                        1.0 - (
                            (index - 1)
                            / max(
                                1,
                                len(tasks),
                            )
                            * 0.5
                        ),
                    ),
                    status="PENDING",
                    progress=0.0,
                    order=index,
                    created_at=now,
                ).to_dict()
            )

        plans = self._plans()

        plans[
            self._key(goal)
        ] = {
            "goal": goal,
            "created_at": now,
            "updated_at": now,
            "tasks": goal_tasks,
        }

        self._save(plans)

        return plans[
            self._key(goal)
        ]

    def get_plan(self, goal: str):
        return self._plans().get(
            self._key(goal)
        )

    def tasks(self, goal: str):
        plan = self.get_plan(goal)

        if plan is None:
            return []

        return [
            GoalTask(
                **task
            )
            for task in plan["tasks"]
        ]

    def next_task(self, goal: str):
        pending = [
            task
            for task in self.tasks(goal)
            if task.status == "PENDING"
        ]

        if not pending:
            return None

        return sorted(
            pending,
            key=lambda task: (
                -task.priority,
                task.order,
            ),
        )[0]

    def activate_next(self, goal: str):
        active = [
            task
            for task in self.tasks(goal)
            if task.status == "ACTIVE"
        ]

        if active:
            return active[0]

        task = self.next_task(goal)

        if task is None:
            return None

        return self._update_task(
            goal,
            task.title,
            status="ACTIVE",
        )

    def complete_task(
        self,
        goal: str,
        title: str,
    ):
        return self._update_task(
            goal,
            title,
            status="COMPLETED",
            progress=1.0,
            completed_at=(
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        )

    def skip_task(
        self,
        goal: str,
        title: str,
    ):
        return self._update_task(
            goal,
            title,
            status="SKIPPED",
        )

    def revive_orphans(self):
        """
        Задачи, брошенные в ACTIVE при гибели
        предыдущего процесса, возвращаются в
        PENDING: новый процесс не может их
        «продолжать». Иначе next_task видит
        пустоту, цель зависает между
        COMPLETE_GOAL и вечной ACTIVE.
        Возвращает число возрождённых задач.
        """
        plans = self._plans()

        revived = 0

        for plan in plans.values():
            for task in plan.get(
                "tasks", []
            ):
                if task.get("status") == "ACTIVE":
                    task["status"] = "PENDING"
                    task["progress"] = 0.0
                    revived += 1

        if revived:
            self._save(plans)

        return revived

    def revise(
        self,
        goal: str,
        title: str,
        reason: str = "",
    ):
        """
        Пересмотр плана после невыполнимого шага.

        Помечает текущий невыполнимый/провалившийся
        шаг как SKIPPED и возвращает следующий
        выполнимый (PENDING) шаг. Завершённые шаги
        не трогает.
        """

        for task in self.tasks(goal):
            if (
                task.title.strip().lower()
                != title.strip().lower()
            ):
                continue

            if task.status in {
                "COMPLETED",
                "SKIPPED",
            }:
                break

            self._update_task(
                goal,
                title,
                status="SKIPPED",
            )
            break

        return self.next_task(goal)

    def update_progress(
        self,
        goal: str,
        title: str,
        progress: float,
    ):
        progress = max(
            0.0,
            min(1.0, progress),
        )

        status = (
            "COMPLETED"
            if progress >= 1.0
            else "ACTIVE"
        )

        kwargs = {
            "progress": progress,
            "status": status,
        }

        if status == "COMPLETED":
            kwargs["completed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

        return self._update_task(
            goal,
            title,
            **kwargs,
        )

    def plan_progress(
        self,
        goal: str,
    ) -> float:
        tasks = self.tasks(goal)

        if not tasks:
            return 0.0

        total = sum(
            task.progress
            for task in tasks
        )

        return round(
            total / len(tasks),
            3,
        )

    def is_complete(
        self,
        goal: str,
    ) -> bool:
        tasks = self.tasks(goal)

        return bool(tasks) and all(
            task.status in {
                "COMPLETED",
                "SKIPPED",
            }
            for task in tasks
        )

    def _update_task(
        self,
        goal: str,
        title: str,
        **changes,
    ):
        plans = self._plans()

        key = self._key(goal)

        if key not in plans:
            raise ValueError(
                f"No plan for goal: {goal}"
            )

        tasks = plans[key]["tasks"]

        target = None

        for task in tasks:
            if (
                task["title"].strip().lower()
                == title.strip().lower()
            ):
                target = task
                break

        if target is None:
            raise ValueError(
                f"Task not found: {title}"
            )

        for field, value in changes.items():
            if field not in {
                "status",
                "progress",
                "completed_at",
            }:
                raise ValueError(
                    f"Unknown task field: {field}"
                )

            target[field] = value

        plans[key]["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._save(plans)

        return GoalTask(
            **target
        )
