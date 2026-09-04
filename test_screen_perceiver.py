import base64, time
from unittest.mock import patch, MagicMock

def test_capture_now_returns_dict():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._last_description = None
    sp._last_screenshot_b64 = None
    sp._last_timestamp = 0
    sp._prev_screenshot_b64 = None
    sp._orchestrator = None
    sp._memory = None
    with patch('identity.screen_perceiver.mss') as mock_mss:
        mock_mss_instance = MagicMock()
        mock_mss.mss.return_value.__enter__ = MagicMock(return_value=mock_mss_instance)
        buf = MagicMock()
        buf.__enter__ = MagicMock(return_value=buf)
        buf.__exit__ = MagicMock(return_value=False)
        buf.raw = b"\x00" * 100
        buf.size = (100, 100)
        mock_mss_instance.grab.return_value = buf
        mock_mss_instance.monitors = [None, {"left": 0, "top": 0, "width": 100, "height": 100}]
        result = sp.capture_now()
    assert isinstance(result, dict)
    assert "description" in result
    assert "timestamp" in result
    assert "screenshot_b64" in result

def test_change_detect_skips_if_no_change():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._last_description = "previous"
    sp._last_screenshot_b64 = base64.b64encode(b"same_image").decode()
    sp._last_timestamp = time.time()
    sp._prev_screenshot_b64 = base64.b64encode(b"same_image").decode()
    sp._orchestrator = None
    sp._memory = None
    with patch('identity.screen_perceiver.mss') as mock_mss:
        mock_mss_instance = MagicMock()
        mock_mss.mss.return_value.__enter__ = MagicMock(return_value=mock_mss_instance)
        buf = MagicMock()
        buf.__enter__ = MagicMock(return_value=buf)
        buf.__exit__ = MagicMock(return_value=False)
        buf.raw = b"same_image"
        buf.size = (10, 10)
        mock_mss_instance.grab.return_value = buf
        mock_mss_instance.monitors = [None, {"left": 0, "top": 0, "width": 10, "height": 10}]
        result = sp.capture_now()
    assert result["description"] == "previous"

def test_tick_respects_interval():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._last_description = None
    sp._last_screenshot_b64 = None
    sp._last_timestamp = time.time()
    sp._prev_screenshot_b64 = None
    sp._orchestrator = None
    sp._memory = None
    call_count = [0]
    original_capture = sp.capture_now
    def mock_capture():
        call_count[0] += 1
        return {"description": "", "timestamp": 0, "screenshot_b64": ""}
    sp.capture_now = mock_capture
    sp.tick()
    assert call_count[0] == 0  # interval not elapsed

def test_get_current_returns_last_state():
    from identity.screen_perceiver import ScreenPerceiver
    sp = ScreenPerceiver.__new__(ScreenPerceiver)
    sp._last_description = "test desc"
    sp._last_screenshot_b64 = "abc123"
    sp._last_timestamp = 12345.0
    result = sp.get_current()
    assert result["description"] == "test desc"
    assert result["screenshot_b64"] == "abc123"
    assert result["timestamp"] == 12345.0
