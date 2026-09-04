import json
import sys
import tkinter as tk
from pathlib import Path

BASE = Path(__file__).resolve().parent

HEARTBEAT = BASE / "data" / "heartbeat.json"
SELF_STATE = BASE / "data" / "self_state.json"
STATUS = BASE / "data" / "status.json"


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_status():
    st_hb = _read_json(STATUS) or {}
    hb = _read_json(HEARTBEAT) or {}
    ss = _read_json(SELF_STATE) or {}

    runtime_state = str(
        st_hb.get("state")
        or hb.get("state")
        or "?"
    )
    asleep = bool(st_hb.get("asleep"))
    life = ss.get("life_state") or {}
    if not asleep:
        asleep = bool(life.get("asleep"))
    fatigue = life.get("fatigue", 0.0)
    decision = st_hb.get("decision", "")

    goals_state = ss.get("goals_state") or {}
    active = [
        v
        for v in goals_state.values()
        if isinstance(v, dict)
        and str(v.get("status")) == "ACTIVE"
    ]
    research = ss.get("current_research") or {}

    if asleep:
        main = "СПИТ"
        color = "#3344cc"
    elif runtime_state in {"ACTING", "REFLECTING"}:
        main = "РАБОТАЕТ"
        color = "#33aa44"
    elif runtime_state == "ERROR":
        main = "ОШИБКА"
        color = "#cc3333"
    elif runtime_state == "LOW_RESOURCE":
        main = "МАЛО ПАМЯТИ"
        color = "#cc8800"
    else:
        main = "БОДРСТВУЕТ"
        color = "#2299cc"

    detail = ""
    if research and isinstance(research, dict):
        topic = research.get("topic") or research.get(
            "current_topic"
        )
        if topic:
            detail = f"исследую: {topic}"
    if not detail and active:
        detail = active[0].get(
            "value", ""
        )[:60]
    if not detail and decision:
        detail = str(decision)[:60]
    if not detail:
        if runtime_state == "IDLE":
            detail = "отдыхаю, наблюдаю"
        else:
            detail = runtime_state

    fatigue_pct = int(round(float(fatigue) * 100))

    return {
        "main": main,
        "color": color,
        "detail": detail,
        "fatigue": fatigue_pct,
    }


class StatusOverlay:
    WIDTH = 230
    HEIGHT = 62

    def __init__(self, refresh_ms=2000):
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        try:
            self._root.attributes(
                "-transparentcolor", "#010203"
            )
        except tk.TclError:
            pass
        try:
            self._root.wm_attributes(
                "-alpha", 0.82
            )
        except tk.TclError:
            pass

        sw = self._root.winfo_screenwidth()
        x = sw - self.WIDTH - 12
        y = 60
        self._root.geometry(
            f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}"
        )

        self._canvas = tk.Canvas(
            self._root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#010203",
            highlightthickness=0,
        )
        self._canvas.pack()

        self._drag = None

        self._canvas.bind(
            "<ButtonPress-1>", self._on_press
        )
        self._canvas.bind(
            "<B1-Motion>", self._on_drag
        )
        self._canvas.bind(
            "<ButtonRelease-1>", self._on_release
        )

        self._refresh_ms = refresh_ms
        self._redraw()

    def _on_press(self, event):
        self._drag = (
            event.x_root - self._root.winfo_x(),
            event.y_root - self._root.winfo_y(),
        )

    def _on_drag(self, event):
        if self._drag is None:
            return
        dx, dy = self._drag
        self._root.geometry(
            f"+{event.x_root - dx}+{event.y_root - dy}"
        )

    def _on_release(self, event):
        self._drag = None

    def _redraw(self):
        st = build_status()
        self._canvas.delete("all")

        r = 8
        self._canvas.create_oval(
            14, self.HEIGHT / 2 - r,
            14 + 2 * r, self.HEIGHT / 2 + r,
            fill=st["color"], outline=""
        )

        self._canvas.create_text(
            40, 16,
            anchor="w",
            text=st["main"],
            fill="white",
            font=("Segoe UI", 11, "bold"),
        )
        self._canvas.create_text(
            40, 34,
            anchor="w",
            text=st["detail"],
            fill="#dddddd",
            font=("Segoe UI", 8),
        )
        self._canvas.create_text(
            40, 50,
            anchor="w",
            text=f"усталость {st['fatigue']}%",
            fill="#999999",
            font=("Segoe UI", 7),
        )

        self._root.after(
            self._refresh_ms, self._redraw
        )

    def run(self):
        self._root.mainloop()


def main():
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        pass
    overlay = StatusOverlay()
    overlay.run()


if __name__ == "__main__":
    main()