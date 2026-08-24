class TaskController:
    """
    Связывает GoalPlanner с результатами ToolRunner.
    """

    def __init__(
        self,
        goal_manager,
        planner,
    ):
        self.goal_manager = goal_manager
        self.planner = planner

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
