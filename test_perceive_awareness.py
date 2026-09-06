from unittest.mock import MagicMock

from identity.action_executor import (
    VALID_ACTIONS,
    ActionExecutor,
)


def test_perceive_in_valid_actions():
    assert "PERCEIVE" in VALID_ACTIONS


def test_action_planner_recognizes_camera_intent():
    from identity.action_planner import ActionPlanner
    from identity.goal_planner import GoalTask

    planner = ActionPlanner()

    scene = planner.plan(
        GoalTask(
            title="посмотри камерой, что там"
        )
    )
    assert scene.action_type == "PERCEIVE"

    scene = planner.plan(
        GoalTask(title="кто рядом со мной?")
    )
    assert scene.action_type == "PERCEIVE"


def test_action_planner_recognizes_screen_intent():
    from identity.action_planner import ActionPlanner
    from identity.goal_planner import GoalTask

    planner = ActionPlanner()

    scene = planner.plan(
        GoalTask(title="посмотри на экран")
    )
    assert scene.action_type == "PERCEIVE"


def test_action_planner_thinks_for_other_tasks():
    from identity.action_planner import ActionPlanner
    from identity.goal_planner import GoalTask

    planner = ActionPlanner()

    scene = planner.plan(
        GoalTask(title="проанализируй общие темы")
    )
    assert scene.action_type == "RESEARCH"


def test_perceive_dry_run_route_policy_ok():
    from identity.tool_registry import ToolRegistry
    from identity.tool_runner import ToolRunner

    registry = ToolRegistry()
    registry.register(
        name="perceive",
        executor=object(),
        description="Восприятие",
        enabled=True,
    )
    runner = ToolRunner(registry)

    action = ActionExecutor().create(
        action_type="PERCEIVE",
        target="space",
        parameters={"source": "webcam"},
        reason="посмотреть вокруг",
        dry_run=True,
    )
    result = runner.run(action)
    assert result["status"] == "SIMULATED"
    assert result["tool"] == "perceive"


def test_sensory_intent_empty_without_request():
    from core.agent import Agent

    agent = Agent.__new__(Agent)
    assert agent._sensory_intent_snapshot(
        "Привет, как дела?"
    ) == ""


def test_sensory_intent_snapshot_uses_camera_when_asked():
    from core.agent import Agent

    agent = Agent.__new__(Agent)
    perceiver = MagicMock()
    perceiver.webcam_describe.return_value = (
        "вижу человека у компьютера"
    )
    agent.screen_perceiver = perceiver

    out = agent._sensory_intent_snapshot(
        "посмотри камерой, кто там?"
    )
    assert "С камеры вижу" in out
    assert "человек" in out


def test_sensory_intent_snapshot_uses_screen_when_asked():
    from core.agent import Agent

    agent = Agent.__new__(Agent)
    perceiver = MagicMock()
    perceiver.capture_now.return_value = {
        "description": "открыт код-редактор",
    }
    agent.screen_perceiver = perceiver

    out = agent._sensory_intent_snapshot(
        "что у тебя на экране?"
    )
    assert "На экране" in out
    assert "код-редактор" in out


def test_sensory_intent_snapshot_no_perceiver():
    from core.agent import Agent

    agent = Agent.__new__(Agent)
    assert agent._sensory_intent_snapshot(
        "посмотри камерой"
    ) == ""


def test_system_prompt_mentions_senses():
    from core.prompts import build_system_prompt

    system = build_system_prompt(
        self_state={},
        user_state={},
        identity_seed={},
        language="ru",
        route="deep",
    )
    assert "ТВОИ ОРГАНЫ ЧУВСТВ" in system
    assert "камера" in system
    assert "экран" in system
    assert "микрофон" in system


def test_quick_prompt_mentions_senses():
    from core.prompts import build_quick_conversation_prompt

    quick = build_quick_conversation_prompt(
        self_state={},
        user_state={},
        language="ru",
        route="quick",
        affective_state={},
        affective_observation={},
    )
    assert "ОРГАНЫ ЧУВСТВ" in quick
    assert "камера" in quick