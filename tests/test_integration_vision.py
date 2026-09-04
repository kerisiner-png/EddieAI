from unittest.mock import patch, MagicMock


def test_self_model_no_vision_removed():
    from identity.self_model import SelfModel, CONTOUR_LIMITATIONS
    ids = [item["id"] for item in CONTOUR_LIMITATIONS]
    assert "no_vision" not in ids


def test_screen_perceiver_can_be_imported():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver()
    assert hasattr(sp, 'tick')
    assert hasattr(sp, 'capture_now')
    assert hasattr(sp, 'get_current')


def test_screen_controller_can_be_imported():
    from identity.screen_controller import ScreenController
    sc = ScreenController()
    assert hasattr(sc, 'click')
    assert hasattr(sc, 'type_text')
    assert hasattr(sc, 'get_active_window')


def test_tool_policy_allows_screen_control():
    from identity.tool_policy import ToolExecutionPolicy
    from identity.action_executor import Action
    policy = ToolExecutionPolicy()
    action = Action(
        action_type="SCREEN_CONTROL",
        target="click",
        parameters={"x": 100, "y": 200},
    )
    result = policy.evaluate(action)
    assert result["allowed"] is True


def test_autonomous_runtime_has_screen_perceiver_attr():
    from core.autonomous_runtime import AutonomousRuntime
    rt = AutonomousRuntime.__new__(AutonomousRuntime)
    rt._screen_perceiver = None
    assert hasattr(rt, '_screen_perceiver')


def test_screen_controller_registered_in_factory():
    import importlib
    mod = importlib.import_module("core.autonomy_runtime_factory")
    assert hasattr(mod.AutonomyRuntimeFactory, 'build')
