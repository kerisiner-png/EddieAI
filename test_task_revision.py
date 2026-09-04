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
    test_controller_without_policy_behaves_as_before()
    test_controller_revises_and_advances()
    test_controller_revise_retransient_keeps_retry()
    print("ALL OK")
