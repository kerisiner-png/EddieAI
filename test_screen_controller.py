from unittest.mock import patch, MagicMock

def test_click_calls_pyautogui():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.click(100, 200)
    mock_pag.click.assert_called_once_with(100, 200)

def test_right_click_calls_pyautogui():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.right_click(50, 60)
    mock_pag.rightClick.assert_called_once_with(50, 60)

def test_double_click_calls_pyautogui():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.double_click(10, 20)
    mock_pag.doubleClick.assert_called_once_with(10, 20)

def test_type_text_calls_pyautogui():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.type_text("hello world")
    mock_pag.typewrite.assert_called_once_with("hello world", interval=0.02)

def test_key_calls_pyautogui_hotkey():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.key("ctrl+c")
    mock_pag.hotkey.assert_called_once_with("ctrl", "c")

def test_scroll_calls_pyautogui():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    with patch('identity.screen_controller.pyautogui') as mock_pag:
        sc.scroll("down", 3)
    mock_pag.scroll.assert_called_once_with(-3)

def test_get_active_window_returns_dict():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    mock_win = MagicMock()
    mock_win.title = "Chrome"
    mock_win.top = 0
    mock_win.left = 0
    mock_win.width = 1920
    mock_win.height = 1080
    with patch('identity.screen_controller.pygetwindow') as mock_pgw:
        mock_pgw.getActiveWindow.return_value = mock_win
        result = sc.get_active_window()
    assert isinstance(result, dict)
    assert result["title"] == "Chrome"
    assert result["width"] == 1920

def test_list_windows_returns_list():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    mock_win = MagicMock()
    mock_win.title = "Notepad"
    mock_win.top = 10
    mock_win.left = 10
    mock_win.width = 800
    mock_win.height = 600
    with patch('identity.screen_controller.pygetwindow') as mock_pgw:
        mock_pgw.getAllWindows.return_value = [mock_win]
        result = sc.list_windows()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Notepad"

def test_focus_window_returns_bool():
    from identity.screen_controller import ScreenController
    sc = ScreenController.__new__(ScreenController)
    mock_win = MagicMock()
    with patch('identity.screen_controller.pygetwindow') as mock_pgw:
        mock_pgw.getWindowsWithTitle.return_value = [mock_win]
        result = sc.focus_window("Chrome")
    assert result is True
    mock_win.activate.assert_called_once()
