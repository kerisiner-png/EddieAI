from typing import Dict, List, Tuple
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None
try:
    import pygetwindow
    pgw = pygetwindow
except ImportError:
    pygetwindow = None
    pgw = None

class ScreenController:
    def click(self, x, y):
        if pyautogui:
            pyautogui.click(x, y)

    def right_click(self, x, y):
        if pyautogui:
            pyautogui.rightClick(x, y)

    def double_click(self, x, y):
        if pyautogui:
            pyautogui.doubleClick(x, y)

    def type_text(self, text):
        if pyautogui:
            pyautogui.typewrite(text, interval=0.02)

    def key(self, hotkey):
        if pyautogui:
            parts = [k.strip() for k in hotkey.split("+")]
            pyautogui.hotkey(*parts)

    def scroll(self, direction="down", amount=3):
        if pyautogui:
            clicks = amount if direction == "up" else -amount
            pyautogui.scroll(clicks)

    def drag(self, start, end, duration=0.5):
        if pyautogui:
            pyautogui.moveTo(start[0], start[1])
            pyautogui.drag(end[0] - start[0], end[1] - start[1], duration=duration)

    def get_active_window(self):
        if pygetwindow:
            try:
                win = pygetwindow.getActiveWindow()
                if win:
                    return {"title": win.title, "top": win.top, "left": win.left, "width": win.width, "height": win.height}
            except Exception:
                pass
        return {"title": "", "top": 0, "left": 0, "width": 0, "height": 0}

    def list_windows(self):
        if pygetwindow:
            try:
                return [{"title": w.title, "top": w.top, "left": w.left, "width": w.width, "height": w.height}
                        for w in pygetwindow.getAllWindows() if w.title]
            except Exception:
                pass
        return []

    def focus_window(self, title):
        if pygetwindow:
            try:
                wins = pygetwindow.getWindowsWithTitle(title)
                if wins:
                    wins[0].activate()
                    return True
            except Exception:
                pass
        return False
