from pathlib import Path
from tempfile import TemporaryDirectory

from identity.action_planner import ActionPlanner
from identity.goal_plan_generator import GoalPlanGenerator
from identity.goal_planner import GoalPlanner
from identity.plan_feasibility import (
    PlanFeasibility,
    FeasibilityIssue,
)
from identity.self_state import SelfState


def _feasibility(available=None):
    planner = ActionPlanner()
    return PlanFeasibility(
        planner=planner,
        available_actions=(
            available
            or {
                "RESEARCH",
                "WEB_SEARCH",
                "READ_FILE",
                "WRITE_FILE",
                "LIST_DIR",
                "SEARCH_FILES",
                "RUN_COMMAND",
                "THINK",
            }
        ),
    )


def test_classifies_research_as_feasible():
    fz = _feasibility()
    tasks = [
        "Провести исследование: космос",
    ]
    issues = fz.check(tasks)
    assert issues == []


def test_flags_task_with_disabled_tool():
    fz = _feasibility(
        available={
            "RESEARCH",
            "THINK",
            "WRITE_FILE",
        }
    )
    tasks = [
        "Запустить проверку git status",
    ]
    issues = fz.check(tasks)
    assert len(issues) == 1
    assert isinstance(issues[0], FeasibilityIssue)
    assert issues[0].action_type == "RUN_COMMAND"
    assert "RUN_COMMAND" in issues[0].reason


def test_feasible_tasks_filters_out_unavailable():
    fz = _feasibility(
        available={
            "RESEARCH",
            "THINK",
        }
    )
    tasks = [
        "Провести исследование: тема",
        "Запустить проверку git status",
        "Проанализировать результаты",
    ]
    ok, issues = fz.assess("цель", tasks)
    assert ok == [
        "Провести исследование: тема",
        "Проанализировать результаты",
    ]
    assert len(issues) == 1


def test_assess_not_feasible_when_all_unavailable():
    fz = _feasibility(
        available={"THINK"}
    )
    tasks = [
        "Запустить проверку git status",
        "Запустить выполнение команды",
    ]
    ok, issues = fz.assess("цель", tasks)
    assert ok == []
    assert len(issues) == 2


def test_ensure_phases_adds_missing_write_for_research():
    fz = _feasibility()
    tasks = [
        "Провести исследование: космос",
        "Проанализировать результаты исследования",
    ]
    phases = fz.ensure_phases("космос", tasks)
    texts = " | ".join(phases).lower()
    # должна появиться недостающая фаза записи результата
    assert any(
        w in texts
        for w in ("записать", "зафиксировать")
    )


def test_ensure_phases_keeps_existing_phases():
    fz = _feasibility()
    tasks = [
        "Провести исследование: космос",
        "Проанализировать результаты исследования",
        "Записать результаты исследования",
    ]
    phases = fz.ensure_phases("космос", tasks)
    assert len(phases) >= 3


def test_ensure_phases_filters_unavailable():
    fz = _feasibility(
        available={"RESEARCH", "THINK"}
    )
    tasks = [
        "Провести исследование: космос",
        "Записать результаты исследования",
    ]
    ok, issues = fz.assess("космос", tasks)
    phases = fz.ensure_phases("космос", ok)
    assert all(
        "записать" not in p.lower()
        for p in phases
    )


def test_generator_sanitize_applies_feasibility_and_phases():
    with TemporaryDirectory() as temp:
        state = SelfState(
            Path(temp) / "g.json"
        )
        planner = GoalPlanner(state)
        fz = PlanFeasibility(
            planner=ActionPlanner(),
            available_actions={
                "RESEARCH",
                "THINK",
                "WRITE_FILE",
            },
        )
        gen = GoalPlanGenerator(
            planner,
            feasibility=fz,
        )
        tasks = gen._sanitize_tasks(
            "изучить космос",
            [
                "Провести исследование: космос",
                "Собрать данные о планетах",
            ],
        )
        assert len(tasks) >= 3
        texts = " | ".join(tasks).lower()
        assert "исследование" in texts
        assert (
            "анализировать" in texts
            or "анализ" in texts
        )


if __name__ == "__main__":
    test_classifies_research_as_feasible()
    test_flags_task_with_disabled_tool()
    test_feasible_tasks_filters_out_unavailable()
    test_assess_not_feasible_when_all_unavailable()
    test_ensure_phases_adds_missing_write_for_research()
    test_ensure_phases_keeps_existing_phases()
    test_ensure_phases_filters_unavailable()
    test_generator_sanitize_applies_feasibility_and_phases()
    print("ALL OK")
