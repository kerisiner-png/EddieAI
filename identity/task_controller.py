class TaskController:
    """
    Связывает GoalPlanner с результатами ToolRunner.
    """

    MAX_TASK_RETRIES = 3

    def __init__(
        self,
        goal_manager,
        planner,
        revision_policy=None,
    ):
        self.goal_manager = goal_manager
        self.planner = planner
        self.revision_policy = revision_policy
        self._retry_counts = {}

    def execute_result(
        self,
        goal: str,
        task_title: str,
        result: dict,
        activate_next: bool = True,
    ):
        status = result.get(
            "status",
            "UNKNOWN",
        )

        if status == "OK":
            self._retry_counts.pop(
                (goal, task_title.lower()),
                None,
            )

            completed = (
                self.planner.complete_task(
                    goal,
                    task_title,
                )
            )

            updated_goal = (
                self.goal_manager.sync_progress(
                    goal
                )
            )

            next_task = None

            if activate_next:
                next_task = (
                    self.goal_manager
                    .activate_next_task(
                        goal
                    )
                )

            return {
                "status": "TASK_COMPLETED",
                "task": completed,
                "goal": updated_goal,
                "next_task": next_task,
            }

        if self.revision_policy is not None:
            decision = (
                self.revision_policy.decide(
                    goal,
                    task_title,
                    result,
                )
            )

            if (
                decision.get("action")
                == "revise"
            ):
                self.planner.revise(
                    goal,
                    task_title,
                    reason=decision.get(
                        "reason",
                        "",
                    ),
                )

                next_task = None

                if activate_next:
                    next_task = (
                        self.goal_manager
                        .activate_next_task(
                            goal
                        )
                    )

                return {
                    "status": "TASK_REVISED",
                    "task": self._current_task(
                        goal,
                        task_title,
                    ),
                    "goal": self.goal_manager.get(
                        goal
                    ),
                    "next_task": next_task,
                }

        key = (goal, task_title.lower())

        retries = (
            self._retry_counts.get(key, 0) + 1
        )

        self._retry_counts[key] = retries

        if retries >= self.MAX_TASK_RETRIES:
            self._retry_counts.pop(key, None)

            self.planner.revise(
                goal,
                task_title,
                reason=(
                    f"Шаг не удался "
                    f"{retries} раза подряд "
                    f"(status={status}) — "
                    f"пропущен после лимита "
                    f"повторов."
                ),
            )

            next_task = None

            if activate_next:
                next_task = (
                    self.goal_manager
                    .activate_next_task(
                        goal
                    )
                )

            return {
                "status": "TASK_REVISED",
                "task": self._current_task(
                    goal,
                    task_title,
                ),
                "goal": self.goal_manager.get(
                    goal
                ),
                "next_task": next_task,
            }

        return {
            "status": "TASK_NOT_COMPLETED",
            "task": self._current_task(
                goal,
                task_title,
            ),
            "goal": self.goal_manager.get(
                goal
            ),
            "next_task": None,
        }

    def _current_task(
        self,
        goal: str,
        task_title: str,
    ):
        for task in self.planner.tasks(
            goal
        ):
            if (
                task.title.strip().lower()
                == task_title.strip().lower()
            ):
                return task

        return None
