import threading

from PIL import Image, ImageDraw, ImageFont
import pystray


def _create_icon_image(size=32):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 1
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(30, 100, 200, 255),
    )
    try:
        font = ImageFont.truetype("arial.ttf", size - 8)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "E", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2
    ty = cy - th // 2 - bbox[1]
    draw.text((tx, ty), "E", fill=(255, 255, 255, 255), font=font)
    return img


class TrayIcon:

    def __init__(self):
        self._open_callbacks = []
        self._exit_callbacks = []
        self._icon = None
        self._thread = None
        image = _create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem(
                "Открыть чат",
                self._handle_open,
                default=True,
            ),
            pystray.MenuItem(
                "Выход",
                self._handle_exit,
            ),
        )
        self._icon = pystray.Icon(
            "EddieAI",
            image,
            "EddieAI Chat",
            menu,
        )

    def show_balloon(self, title, message):
        if self._icon is not None:
            self._icon.notify(message, title)

    def on_open_chat(self, callback):
        self._open_callbacks.append(callback)

    def on_exit(self, callback):
        self._exit_callbacks.append(callback)

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        if self._icon is not None:
            self._icon.stop()
            self._thread = None

    def _handle_open(self, icon=None, item=None):
        for cb in self._open_callbacks:
            try:
                cb()
            except Exception:
                pass

    def _handle_exit(self, icon=None, item=None):
        for cb in self._exit_callbacks:
            try:
                cb()
            except Exception:
                pass
        if self._icon is not None:
            self._icon.stop()
