"""Режим «смотрим вместе»: EddieAI сам входит, комментирует и выходит.

Автономный вход — по маркерам видео в заголовке активного окна
(устойчивым во времени) и по свежей звуковой активности; выход — по
долгой тишине (нет новых кадров и нет звука). Комментарии — раз в
COMMENT_INTERVAL через инициативный канал.
"""
import time

VIDEO_TITLE_MARKERS = (
    "youtube",
    "vk video",
    "кинопоиск",
    "netflix",
    "twitch",
    "rutube",
    "смотреть",
    "видео",
    "фильм",
    "сериал",
)

COMMENT_INTERVAL = 600.0
EXIT_QUIET_SEC = 300.0
TITLE_SUSTAIN_SEC = 60.0
MIN_PAUSE_COMMENT_LEN = 40
HOLD_RESUME_SEC = 180.0
SPEECH_CHARS_PER_SEC = 13.0


def looks_like_video_title(title) -> bool:
    needle = (title or "").strip().lower()
    if not needle:
        return False
    return any(
        marker in needle
        for marker in VIDEO_TITLE_MARKERS
    )


def estimate_speech_seconds(text) -> float:
    text = (text or "").strip()
    if not text:
        return 0.0
    return max(
        4.0,
        len(text) / SPEECH_CHARS_PER_SEC
        + 3.0,
    )


def is_question(text) -> bool:
    text = (text or "").strip()
    if text.endswith("?"):
        return True
    markers = (
        "как думаешь",
        "что думаешь",
        "как тебе",
        "а у тебя",
        "тебе нравится",
        "видел ли",
        "замечал ли",
    )
    lowered = text.lower()
    return any(
        marker in lowered for marker in markers
    )


def pause_decision(
    text,
    audio_playing,
):
    """
    Удобство восприятия, не закон: ставим
    паузу перед заметной репликой, если
    видео действительно играет. Возврат:
    None | "resume_auto" (договорил и
    снял) | "resume_hold" (ждёт ответа).
    """
    text = (text or "").strip()

    if not audio_playing:
        return None

    if len(text) < MIN_PAUSE_COMMENT_LEN:
        return None

    if is_question(text):
        return "resume_hold"

    return "resume_auto"


class WatchMode:
    def __init__(
        self,
        comment_interval=COMMENT_INTERVAL,
        exit_quiet_sec=EXIT_QUIET_SEC,
    ):
        self.comment_interval = comment_interval
        self.exit_quiet_sec = exit_quiet_sec
        self.active = False
        self.source = None
        self.entered_at = 0.0
        self.last_comment_ts = 0.0
        self.last_motion_ts = 0.0
        self.last_audio_ts = 0.0
        self._title_since = 0.0

    def note_motion(self, now):
        self.last_motion_ts = now

    def note_audio(self, now):
        self.last_audio_ts = now

    def audio_recent(self, now):
        return (
            now - self.last_audio_ts
            <= 90.0
        )

    def maybe_enter(
        self,
        now,
        window_title,
    ):
        if self.active:
            return False

        if not looks_like_video_title(
            window_title
        ):
            self._title_since = 0.0
            return False

        if self._title_since == 0.0:
            self._title_since = now
            return False

        if (
            now - self._title_since
            < TITLE_SUSTAIN_SEC
        ):
            return False

        self.force_enter(now, "self")
        return True

    def force_enter(self, now, source):
        self.active = True
        self.source = source
        self.entered_at = now
        self.last_comment_ts = now
        self.last_motion_ts = now
        self._title_since = 0.0

    def maybe_exit(self, now):
        if not self.active:
            return False

        motion_quiet = (
            now - self.last_motion_ts
            > self.exit_quiet_sec
        )
        audio_quiet = (
            now - self.last_audio_ts
            > self.exit_quiet_sec
        )

        if motion_quiet and audio_quiet:
            self.force_exit(now)
            return True

        return False

    def force_exit(self, now):
        self.active = False
        self.source = None
        self.entered_at = 0.0
        self._title_since = 0.0

    def should_comment(self, now):
        return (
            self.active
            and now - self.last_comment_ts
            >= self.comment_interval
        )

    def mark_commented(self, now):
        self.last_comment_ts = now

    def press_media_pause(self) -> bool:
        """
        Медиа-клавиша Play/Pause (VK 0xB3):
        Chrome/Edge и плееры обрабатывают её
        глобально.
        """
        try:
            import ctypes

            ctypes.windll.user32.keybd_event(
                0xB3, 0, 0, 0
            )
            ctypes.windll.user32.keybd_event(
                0xB3, 0, 2, 0
            )
            return True
        except Exception:
            return False
