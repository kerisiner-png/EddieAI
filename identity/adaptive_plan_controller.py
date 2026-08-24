from identity.goal_planner import VALID_TASK_STATUSES


class AdaptivePlanController:
    """
    Применяет решение AdaptivePlanner к существующему плану.

    Уже выполненные задачи не изменяются.
    """

    MAX_TASKS = 5

    def __init__(
        self,
        goal_planner,
    ):
        self.goal_planner = goal_planner

    def apply(
        self,
        goal: str,
        decision: dict,
    ):
        action = decision.get(
            "decision",
            "KEEP",
        )

        new_tasks = self._clean_tasks(
            decision.get(
                "tasks",
                [],
            )
        )

        if action == "KEEP":
            return {
                "status": "UNCHANGED",
                "decision": action,
                "tasks": self.goal_planner.tasks(
                    goal
                ),
            }

        plan = self.goal_planner.get_plan(
            goal
        )

        if plan is None:
            return {
                "status": "REJECTED",
                "decision": action,
                "reason": (
                    "План цели отсутствует."
                ),
            }

        if not new_tasks:
            return {
                "status": "REJECTED",
                "decision": action,
                "reason": (
                    "AdaptivePlanner не "
                    "предложил корректных задач."
                ),
            }

        if action == "APPEND":
            return self._append(
                goal,
                new_tasks,
            )

        if action == "REPLACE":
            return self._replace_pending(
                goal,
                new_tasks,
            )

        return {
            "status": "REJECTED",
            "decision": action,
            "reason": (
                "Неизвестное решение."
            ),
        }

    def _append(
        self,
        goal: str,
        tasks: list[str],
    ):
        existing = self.goal_planner.tasks(
            goal
        )

        existing_titles = {
            task.title.strip().lower()
            for task in existing
        }

        additions = [
            task
            for task in tasks
            if task.lower()
            not in existing_titles
        ]

        if not additions:
            return {
                "status": "UNCHANGED",
                "decision": "APPEND",
                "reason": (
                    "Новых уникальных задач нет."
                ),
                "tasks": existing,
            }

        current_count = len(existing)

        available = max(
            0,
            self.MAX_TASKS - current_count,
        )

        additions = additions[
            :available
        ]

        if not additions:
            return {
                "status": "REJECTED",
                "decision": "APPEND",
                "reason": (
                    "Достигнут лимит задач."
                ),
            }

        plan = self.goal_planner.get_plan(
            goal
        )

        start_order = len(
            plan["tasks"]
        ) + 1

        for index, title in enumerate(
            additions,
            start=start_order,
        ):
            plan["tasks"].append({
                "title": title,
                "priority": max(
                    0.1,
                    1.0
                    - (
                        (index - 1)
                        / max(
                            1,
                            self.MAX_TASKS,
                        )
                        * 0.5
                    ),
                ),
                "status": "PENDING",
                "progress": 0.0,
                "order": index,
                "created_at": None,
                "completed_at": None,
            })

        self.goal_planner._save(
            self.goal_planner._plans()
        )

        return {
            "status": "UPDATED",
            "decision": "APPEND",
            "tasks_added": additions,
            "tasks": self.goal_planner.tasks(
                goal
            ),
        }

    def _replace_pending(
        self,
        goal: str,
        tasks: list[str],
    ):
        plan = self.goal_planner.get_plan(
            goal
        )

        if plan is None:
            return {
                "status": "REJECTED",
                "decision": "REPLACE",
            }

        existing = self.goal_planner.tasks(
            goal
        )

        completed = [
            task
            for task in existing
            if task.status
            in {
                "COMPLETED",
                "SKIPPED",
            }
        ]

        active = [
            task
            for task in existing
            if task.status == "ACTIVE"
        ]

        if active:
            return {
                "status": "REJECTED",
                "decision": "REPLACE",
                "reason": (
                    "Нельзя заменять план, "
                    "пока есть активная задача."
                ),
            }

        titles = {
            task.title.strip().lower()
            for task in completed
        }

        filtered = [
            title
            for title in tasks
            if title.lower()
            not in titles
        ]

        if not filtered:
            return {
                "status": "REJECTED",
                "decision": "REPLACE",
                "reason": (
                    "Новые задачи конфликтуют "
                    "с уже выполненными."
                ),
            }

        new_plan = [
            task.to_dict()
            for task in completed
        ]

        start_order = len(
            new_plan
        ) + 1

        for index, title in enumerate(
            filtered[: self.MAX_TASKS
                     - len(new_plan)],
            start=start_order,
        ):
            new_plan.append({
                "title": title,
                "priority": max(
                    0.1,
                    1.0
                    - (
                        (index - 1)
                        / max(
                            1,
                            self.MAX_TASKS,
                        )
                        * 0.5
                    ),
                ),
                "status": "PENDING",
                "progress": 0.0,
                "order": index,
                "created_at": None,
                "completed_at": None,
            })

        plan["tasks"] = new_plan

        self.goal_planner._save(
            self.goal_planner._plans()
        )

        return {
            "status": "UPDATED",
            "decision": "REPLACE",
            "tasks": self.goal_planner.tasks(
                goal
            ),
        }

    def _clean_tasks(
        self,
        tasks,
    ):
        if not isinstance(
            tasks,
            list,
        ):
            return []

        result = []
        seen = set()

        for task in tasks:
            if not isinstance(
                task,
                str,
            ):
                continue

            task = " ".join(
                task.strip().split()
            )

            if not task:
                continue

            key = task.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(task)

            if len(result) >= self.MAX_TASKS:
                break

        return result
