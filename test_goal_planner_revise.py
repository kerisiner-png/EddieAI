from pathlib import Path
from tempfile import TemporaryDirectory

from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState


class Fixture:
    def __init__(self):
        self.temp = TemporaryDirectory()
        path = Path(self.temp.name) / "state.json"
        self.state = SelfState(path)
        self.planner = GoalPlanner(self.state)


def _make():
    return Fixture()


def test_revise_skips_failed_task_and_returns_next():
    fix = _make()
    fix.planner.create_plan(
        goal="изучить космос",
        tasks=[
            "Провести исследование: космос",
            "Проанализировать результаты",
            "Записать результаты исследования",
        ],
    )
    fix.planner.activate_next("изучить космос")
    nxt = fix.planner.revise(
        "изучить космос",
        "Провести исследование: космос",
        reason="инструмент research недоступен",
    )
    assert nxt is not None
    assert nxt.title == "Проанализировать результаты"
    skipped = fix.planner.tasks("изучить космос")[0]
    assert skipped.status == "SKIPPED"


def test_revise_unknown_title_returns_next_task():
    fix = _make()
    fix.planner.create_plan(
        goal="цель",
        tasks=["Шаг один"],
    )
    fix.planner.activate_next("цель")
    nxt = fix.planner.revise("цель", "нет такой задачи")
    assert nxt is None or nxt.status != "SKIPPED"


def test_revise_keeps_already_completed_task():
    fix = _make()
    fix.planner.create_plan(
        goal="цель",
        tasks=["Шаг один", "Шаг два"],
    )
    fix.planner.complete_task("цель", "Шаг один")
    nxt = fix.planner.revise("цель", "Шаг один")
    assert nxt is None or nxt.title != "Шаг один"
    assert fix.planner.tasks("цель")[0].status == "COMPLETED"


if __name__ == "__main__":
    test_revise_skips_failed_task_and_returns_next()
    test_revise_unknown_title_returns_next_task()
    test_revise_keeps_already_completed_task()
    print("ALL OK")
