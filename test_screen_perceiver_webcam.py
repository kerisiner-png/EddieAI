import base64
from unittest.mock import MagicMock


def test_webcam_describe_calls_vision():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._orchestrator = None
    sp._memory = None
    sp._last_description = None
    sp._last_screenshot_b64 = None
    sp._last_timestamp = 0
    sp._prev_screenshot_b64 = None
    sp._vision_calls = 0

    # mock webcam capture
    sp.webcam_capture = lambda: base64.b64encode(
        b"fake_cam_frame"
    ).decode()

    class FakeVision:
        def _cloud_chat_vision(self, system, user, images):
            return {"text": "вижу человека за компьютером"}

    sp._orchestrator = FakeVision()
    desc = sp.webcam_describe()
    assert desc == "вижу человека за компьютером"
    assert sp._vision_calls == 1


def test_webcam_describe_returns_empty_without_camera():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._orchestrator = None
    sp._memory = None
    sp._last_description = None
    sp._last_screenshot_b64 = None
    sp._last_timestamp = 0
    sp._prev_screenshot_b64 = None
    sp._vision_calls = 0
    sp.webcam_capture = lambda: None
    assert sp.webcam_describe() == ""


def test_vision_daily_limit_blocks_calls():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._orchestrator = None
    sp._memory = None
    sp._last_description = "last desc"
    sp._last_screenshot_b64 = None
    sp._last_timestamp = 0
    sp._prev_screenshot_b64 = None
    sp._vision_calls = ScreenPerceiver.VISION_DAILY_LIMIT

    class FakeVision:
        def _cloud_chat_vision(self, system, user, images):
            return {"text": "should not be called"}

    sp._orchestrator = FakeVision()
    result = sp._vision_describe("b64")
    assert result == "last desc"

    cam_calls = [0]
    sp.webcam_capture = lambda: (cam_calls.__setitem__(0, cam_calls[0] + 1) or "b64")
    assert sp.webcam_describe() == ""
    assert cam_calls[0] == 0