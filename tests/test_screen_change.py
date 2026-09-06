import base64
import io

from PIL import Image, ImageDraw

from identity.screen_perceiver import (
    active_window_title,
    changed_significantly,
)


def _png(draw_fn):
    img = Image.new("RGB", (320, 180), (40, 40, 40))
    draw_fn(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _solid(color):
    return _png(lambda d: d.rectangle([0, 0, 319, 179], fill=color))


def test_identical_frames_not_significant():
    a = _solid((90, 90, 90))
    assert changed_significantly(a, a) is False


def test_cursor_blink_not_significant():
    a = _solid((90, 90, 90))

    def blink(d):
        d.rectangle(
            [0, 0, 319, 179], fill=(90, 90, 90)
        )
        d.rectangle(
            [150, 80, 155, 90],
            fill=(255, 255, 255),
        )

    b = _png(blink)
    assert changed_significantly(a, b) is False


def test_real_change_is_significant():
    a = _solid((90, 90, 90))
    b = _solid((220, 60, 40))
    assert changed_significantly(a, b) is True


def test_empty_prev_always_significant():
    a = _solid((90, 90, 90))
    assert changed_significantly("", a) is True


def test_active_window_title_returns_string():
    title = active_window_title()
    assert isinstance(title, str)
