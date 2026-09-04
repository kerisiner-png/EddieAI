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
    INTERVAL = 120.0
    RESIZE = (1280, 720)
    VISION_DAILY_LIMIT = 150

    def __init__(self, model_orchestrator=None, memory=None):
        self._orchestrator = model_orchestrator
        self._memory = memory
        self._last_description = None
        self._last_screenshot_b64 = None
        self._last_timestamp = 0.0
        self._prev_screenshot_b64 = None
        self._vision_calls = 0

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
                from memory.events import Event
                self._memory.remember(Event.create(
                    content=f"Экран: {description}",
                    event_type="WORLD_SNAPSHOT",
                    source_type="VISION",
                    source="screen",
                ))
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
        if self._vision_calls >= self.VISION_DAILY_LIMIT:
            return self._last_description or ""
        try:
            system = "Ты — глаза EddieAI. Опиши кратко что на экране: какое приложение, что открыто, что происходит. Максимум 3 предложения."
            user = "Опиши что на экране."
            vision_fn = getattr(
                self._orchestrator,
                "_cloud_chat_vision",
                None,
            )
            if vision_fn is None:
                return ""
            result = vision_fn(
                system,
                user,
                [screenshot_b64],
            )
            self._vision_calls += 1
            if isinstance(result, dict):
                return result.get("text", "")
            return str(result) if result else ""
        except Exception:
            return ""

    def webcam_capture(self):
        try:
            import cv2
            import base64 as b64mod

            index = self._find_webcam_index()
            if index is None:
                return None
            cap = cv2.VideoCapture(
                index, cv2.CAP_DSHOW
            )
            if not cap.isOpened():
                return None
            try:
                ret, frame = cap.read()
            finally:
                cap.release()
            if not ret:
                return None
            import io
            from PIL import Image

            img = Image.fromarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            )
            img = img.resize(self.RESIZE, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return b64mod.b64encode(
                buf.getvalue()
            ).decode("ascii")
        except Exception:
            return None

    def _find_webcam_index(self):
        """Выбор физической вебки ноутбука.

        Отбрасывает виртуальные камеры (Snap Camera и т.п.):
        открывает индексы 0..4 и предпочитает устройство,
        чьё имя НЕ содержит 'snap', 'virtual', 'obs'.
        Фолбэк — первый открывшийся.
        """
        try:
            import cv2
            import subprocess

            opened = []
            for idx in range(5):
                cap = cv2.VideoCapture(
                    idx, cv2.CAP_DSHOW
                )
                ok = cap.isOpened()
                cap.release()
                if ok:
                    opened.append(idx)
            if not opened:
                return None

            try:
                script = (
                    "Get-PnpDevice -Class Camera,Image "
                    "-Status OK | "
                    "Select-Object -ExpandProperty FriendlyName"
                )
                r = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        script,
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                )
                names = [
                    line.strip()
                    for line in r.stdout.splitlines()
                    if line.strip()
                ]
            except Exception:
                names = []

            bad = ("snap", "virtual", "obs", "camera effects")
            for idx in opened:
                name = (
                    names[idx].lower()
                    if idx < len(names)
                    else ""
                )
                if name and not any(
                    b in name for b in bad
                ):
                    return idx
            return opened[0]
        except Exception:
            return None

    def webcam_describe(self):
        if self._vision_calls >= self.VISION_DAILY_LIMIT:
            return ""
        b64 = self.webcam_capture()
        if b64 is None:
            return ""
        if self._orchestrator is None:
            return ""
        try:
            vision_fn = getattr(
                self._orchestrator,
                "_cloud_chat_vision",
                None,
            )
            if vision_fn is None:
                return ""
            result = vision_fn(
                "Ты — глаза EddieAI. Опиши что видно с камеры: есть ли человек, "
                "что он делает, что вокруг. Максимум 3 предложения.",
                "Что на камере?",
                [b64],
            )
            self._vision_calls += 1
            if isinstance(result, dict):
                return result.get("text", "")
            return str(result) if result else ""
        except Exception:
            return ""
