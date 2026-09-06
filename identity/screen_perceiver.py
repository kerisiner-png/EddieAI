"""Непрерывный vision-контур EddieAI: захват экрана → change detect → vision model → memory."""
import base64, io, time
from typing import Optional, Dict, Any
try:
    import mss
    import mss.tools
except ImportError:
    mss = None
from PIL import Image, ImageChops
import ctypes


CHANGE_DIFF_PIXEL_THRESHOLD = 24
CHANGE_FRACTION_THRESHOLD = 0.02
ACTIVE_WINDOW_CLASS = ctypes.windll.user32


def active_window_title() -> str:
    """
    Заголовок активного окна Windows
    (ctypes, без зависимостей).
    """
    try:
        hwnd = ACTIVE_WINDOW_CLASS.GetForegroundWindow()
        if not hwnd:
            return ""
        length = ACTIVE_WINDOW_CLASS.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        ACTIVE_WINDOW_CLASS.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""


def changed_significantly(
    prev_b64: str,
    new_b64: str,
) -> bool:
    """
    Значимая ли смена кадра: доля заметно
    отличшихся пикселей в уменьшенном
    градациях серого (мигание курсора и
    мелкий шум отсекаются).
    """
    if not prev_b64 or not new_b64:
        return True

    try:
        prev = Image.open(
            io.BytesIO(base64.b64decode(prev_b64))
        ).convert("RGB").resize((160, 90))
        new = Image.open(
            io.BytesIO(base64.b64decode(new_b64))
        ).convert("RGB").resize((160, 90))
    except Exception:
        return True

    diff = ImageChops.difference(prev, new)
    r, g, b = diff.split()
    max_diff = ImageChops.lighter(
        ImageChops.lighter(r, g), b
    )
    hist = max_diff.histogram()
    total = 160 * 90
    notable = sum(
        hist[CHANGE_DIFF_PIXEL_THRESHOLD + 1:]
    )

    return (
        notable / total
        >= CHANGE_FRACTION_THRESHOLD
    )


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
        self._last_window_title = ""
        self._last_title_seen = ""
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
        if self._prev_screenshot_b64 and not changed_significantly(self._prev_screenshot_b64, screenshot_b64):
            self._prev_screenshot_b64 = screenshot_b64
            self._last_screenshot_b64 = screenshot_b64
            self._last_timestamp = time.time()
            return {"description": self._last_description or "", "timestamp": self._last_timestamp, "screenshot_b64": screenshot_b64}
        title = active_window_title()
        if title and title != self._last_title_seen:
            self._last_title_seen = title
            if self._memory:
                try:
                    from memory.events import Event
                    self._memory.remember(Event.create(
                        content=f"Эдди переключился на окно: {title}",
                        event_type="WORLD_SNAPSHOT",
                        source_type="CONTEXT",
                        source="window",
                    ))
                except Exception:
                    pass
        try:
            from identity.window_text import focused_window_text
            context_text = focused_window_text()
        except Exception:
            context_text = ""
        description = self._vision_describe(screenshot_b64, window_title=title, context_text=context_text)
        self._prev_screenshot_b64 = screenshot_b64
        self._last_screenshot_b64 = screenshot_b64
        self._last_description = description
        self._last_window_title = title
        self._last_timestamp = time.time()
        if self._memory and description:
            try:
                from memory.events import Event
                label = f"Экран [окно: {title}]: {description}" if title else f"Экран: {description}"
                self._memory.remember(Event.create(
                    content=label,
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
                shot = sct.grab(monitor)
                size = shot.size
                rgb = shot.rgb
            img = Image.frombytes("RGB", size, rgb)
            img = img.resize(self.RESIZE, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None

    def _vision_describe(self, screenshot_b64, window_title="", context_text=""):
        if self._orchestrator is None:
            return ""
        if self._vision_calls >= self.VISION_DAILY_LIMIT:
            return self._last_description or ""
        try:
            system = "Ты — глаза EddieAI. Опиши кратко что на экране: какое приложение, что открыто, что происходит. Максимум 3 предложения."
            user = "Опиши что на экране."
            if window_title:
                user = (
                    f"Активное окно Windows: {window_title}. "
                    "Опиши что на экране."
                )
            if context_text:
                user += (
                    " Текст сфокусированного элемента окна "
                    f"(фрагмент): {context_text[:400]}"
                )
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
