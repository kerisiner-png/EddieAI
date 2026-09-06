from pathlib import Path
from tempfile import TemporaryDirectory

from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from identity.task_controller import TaskController
from identity.task_revision import TaskRevisionPolicy


class Fixture:
    def __init__(self):
        self.temp = TemporaryDirectory()
        path = Path(self.temp.name) / "s.json"
        self.state = SelfState(path)
        self.planner = GoalPlanner(self.state)
        self.goal_manager = GoalManager(self.state)
        self.planner.create_plan(
            goal="изучить космос",
            tasks=[
                "Провести исследование: космос",
                "Проанализировать результаты",
            ],
        )


def _make():
    return Fixture()


def test_policy_retries_on_transient_error():
    pol = TaskRevisionPolicy()
    decision = pol.decide(
        "изучить космос",
        "Провести исследование: космос",
        {"status": "FAILED", "error": "timeout"},
    )
    assert decision["action"] == "retry"


def test_policy_revises_on_unavailable_tool():
    pol = TaskRevisionPolicy()
    decision = pol.decide(
        "изучить космос",
        "Запустить проверку git",
        {
            "status": "FAILED",
            "error": (
                "нет инструмента для "
                "выполнения"
            ),
        },
    )
    assert decision["action"] == "revise"


def test_controller_without_policy_behaves_as_before():
    fix = _make()
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
    )
    result = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        {"status": "FAILED", "error": "ошибка"},
    )
    assert result["status"] == "TASK_NOT_COMPLETED"
    task = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert task.status != "SKIPPED"


def test_controller_revises_and_advances():
    fix = _make()
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
        revision_policy=TaskRevisionPolicy(),
    )
    result = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        {
            "status": "FAILED",
            "error": (
                "нет инструмента для "
                "выполнения шага"
            ),
        },
    )
    assert result["status"] == "TASK_REVISED"
    skipped = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert skipped.status == "SKIPPED"
    # следующий шаг становится следующим выполнимым
    assert result["next_task"] is not None


def test_policy_revises_on_rejected_action():
    pol = TaskRevisionPolicy()
    decision = pol.decide(
        "изучить космос",
        "Записать результаты в файл",
        {
            "status": "REJECTED",
            "errors": [
                "действие запрещено политикой"
            ],
        },
    )
    assert decision["action"] == "revise"


def test_controller_revises_on_rejected_result():
    fix = _make()
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
        revision_policy=TaskRevisionPolicy(),
    )
    result = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        {
            "status": "REJECTED",
            "errors": [
                "действие запрещено политикой"
            ],
        },
    )
    assert result["status"] == "TASK_REVISED"
    skipped = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert skipped.status == "SKIPPED"
    assert result["next_task"] is not None


def test_controller_revise_retransient_keeps_retry():
    fix = _make()
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
        revision_policy=TaskRevisionPolicy(),
    )
    result = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        {"status": "FAILED", "error": "timeout"},
    )
    assert result["status"] == "TASK_NOT_COMPLETED"
    task = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert task.status != "SKIPPED"


if __name__ == "__main__":
    test_policy_retries_on_transient_error()
    test_policy_revises_on_unavailable_tool()
    test_policy_revises_on_rejected_action()
    test_controller_without_policy_behaves_as_before()
    test_controller_revises_and_advances()
    test_controller_revise_retransient_keeps_retry()
    test_controller_revises_on_rejected_result()
    print("ALL OK")


def test_planner_revives_orphan_active_tasks():
    fix = _make()
    fix.planner.activate_next(
        "изучить космос"
    )

    tasks = fix.planner.tasks(
        "изучить космос"
    )
    assert tasks[0].status == "ACTIVE"

    revived = fix.planner.revive_orphans()

    assert revived == 1
    tasks = fix.planner.tasks(
        "изучить космос"
    )
    assert tasks[0].status == "PENDING"
    assert (
        fix.planner.next_task(
            "изучить космос"
        )
        is not None
    )


def test_planner_revive_keeps_completed():
    fix = _make()
    fix.planner.complete_task(
        "изучить космос",
        "Провести исследование: космос",
    )

    revived = fix.planner.revive_orphans()

    assert revived == 0
    task = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert task.status == "COMPLETED"


if __name__ == "__main__":
    test_policy_retries_on_transient_error()
    test_policy_revises_on_unavailable_tool()
    test_policy_revises_on_rejected_action()
    test_controller_without_policy_behaves_as_before()
    test_controller_revises_and_advances()
    test_controller_revise_retransient_keeps_retry()
    test_controller_revises_on_rejected_result()
    test_planner_revives_orphan_active_tasks()
    test_planner_revive_keeps_completed()
    print("ALL OK")


def test_controller_revises_after_retry_limit():
    fix = _make()
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
        revision_policy=TaskRevisionPolicy(),
    )

    stuck = {
        "status": "NO_ACCEPTED_SOURCES"
    }

    first = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        stuck,
        activate_next=False,
    )
    assert (
        first["status"] == "TASK_NOT_COMPLETED"
    )

    second = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        stuck,
        activate_next=False,
    )
    assert (
        second["status"] == "TASK_NOT_COMPLETED"
    )

    third = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        stuck,
        activate_next=False,
    )
    assert third["status"] == "TASK_REVISED"
    skipped = fix.planner.tasks(
        "изучить космос"
    )[0]
    assert skipped.status == "SKIPPED"


def test_controller_retry_resets_on_success():
    fix = _make()
    fix.goal_manager.add_candidate(
        value="изучить космос",
        motivation=0.6,
        priority=0.5,
        confidence=0.6,
    )
    fix.goal_manager.activate(
        "изучить космос"
    )
    controller = TaskController(
        fix.goal_manager,
        fix.planner,
        revision_policy=TaskRevisionPolicy(),
    )

    stuck = {
        "status": "NO_ACCEPTED_SOURCES"
    }

    controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        stuck,
        activate_next=False,
    )

    controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        {"status": "OK"},
        activate_next=False,
    )

    again = controller.execute_result(
        "изучить космос",
        "Провести исследование: космос",
        stuck,
        activate_next=False,
    )
    assert (
        again["status"] == "TASK_NOT_COMPLETED"
    )


if __name__ == "__main__":
    test_policy_retries_on_transient_error()
    test_policy_revises_on_unavailable_tool()
    test_policy_revises_on_rejected_action()
    test_controller_without_policy_behaves_as_before()
    test_controller_revises_and_advances()
    test_controller_revise_retransient_keeps_retry()
    test_controller_revises_on_rejected_result()
    test_planner_revives_orphan_active_tasks()
    test_planner_revive_keeps_completed()
    test_controller_revises_after_retry_limit()
    test_controller_retry_resets_on_success()
    print("ALL OK")
