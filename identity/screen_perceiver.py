"""Непрерывный vision-контур EddieAI: захват экрана → change detect → vision model → memory."""
import base64, io, time
from typing import Optional, Dict, Any
try:
    import mss
    import mss.tools
except ImportError:
    mss = None
from PIL import Image

class ScreenPerceiver:
    INTERVAL = 3.0
    RESIZE = (1280, 720)

    def __init__(self, model_orchestrator=None, memory=None):
        self._orchestrator = model_orchestrator
        self._memory = memory
        self._last_description = None
        self._last_screenshot_b64 = None
        self._last_timestamp = 0.0
        self._prev_screenshot_b64 = None

    def tick(self):
        now = time.time()
        if now - self._last_timestamp < self.INTERVAL:
            return
        self.capture_now()

    def capture_now(self):
        screenshot_b64 = self._capture_screen()
        if screenshot_b64 is None:
            return {"description": self._last_description or "", "timestamp": self._last_timestamp, "screenshot_b64": self._last_screenshot_b64 or ""}
        if screenshot_b64 == self._prev_screenshot_b64:
            self._last_timestamp = time.time()
            return {"description": self._last_description or "", "timestamp": self._last_timestamp, "screenshot_b64": screenshot_b64}
        description = self._vision_describe(screenshot_b64)
        self._prev_screenshot_b64 = screenshot_b64
        self._last_screenshot_b64 = screenshot_b64
        self._last_description = description
        self._last_timestamp = time.time()
        if self._memory and description:
            try:
                from memory.memory import Event
                self._memory.remember(Event(kind="WORLD_SNAPSHOT", payload={"description": description}))
            except Exception:
                pass
        return {"description": description, "timestamp": self._last_timestamp, "screenshot_b64": screenshot_b64}

    def get_current(self):
        return {"description": self._last_description or "", "timestamp": self._last_timestamp, "screenshot_b64": self._last_screenshot_b64 or ""}

    def _capture_screen(self):
        if mss is None:
            return None
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                with sct.grab(monitor) as img:
                    raw = img.raw
            img = Image.frombytes("RGB", img.size, raw, "raw", "RGB")
            img = img.resize(self.RESIZE, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None

    def _vision_describe(self, screenshot_b64):
        if self._orchestrator is None:
            return ""
        try:
            system = "Ты — глаза EddieAI. Опиши кратко что на экране: какое приложение, что открыто, что происходит. Максимум 3 предложения."
            user = "Опиши что на экране."
            result = self._orchestrator.execute(system=system, user=user, task="vision", images=[screenshot_b64])
            if isinstance(result, dict):
                return result.get("text", "")
            return str(result) if result else ""
        except Exception:
            return ""
