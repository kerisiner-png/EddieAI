import threading


IDLE = "IDLE"
RINGING_IN = "RINGING_IN"
RINGING_OUT = "RINGING_OUT"
ACTIVE = "ACTIVE"
ENDED = "ENDED"

ENDED_TTL_SECONDS = 5.0

EDDIE_SPEAKING = "EDDIE_SPEAKING"
EDDIEAI_SPEAKING = "EDDIEAI_SPEAKING"

class CallDirector:
    """
    Машина состояний голосового звонка (модель реального
    телефонного звонка).

    IDLE -> RINGING_IN/RINGING_OUT -> ACTIVE -> ENDED -> IDLE

    Разговор (ACTIVE) включается ТОЛЬКО после answer().
    Отказ (reject) или завершение (end) любой стороной
    переводит звонок в ENDED и затем IDLE.
    """

    def __init__(self):
        self._state = IDLE
        self._direction = None
        self._lock = threading.Lock()
        self._on_interrupt_by = None
        self._on_state_change = None
        self._last_speaker = None
        self._ended_at = 0.0

    def set_interrupt_callback(self, callback):
        self._on_interrupt_by = callback

    def set_state_change_callback(self, callback):
        self._on_state_change = callback

    def state(self):
        with self._lock:
            return self._state

    def direction(self):
        with self._lock:
            return self._direction

    def in_call(self):
        with self._lock:
            return (
            self._state == ACTIVE
        )

    def is_ringing(self):
        with self._lock:
            return (
                self._state
                in (RINGING_IN, RINGING_OUT)
            )

    def _set(self, state, direction=None):
        changed = True
        with self._lock:
            if state != self._state:
                changed = True
            self._state = state
            if direction is not None:
                self._direction = direction
        if changed:
            cb = self._on_state_change
            if cb is not None:
                try:
                    cb(state, self._direction)
                except Exception:
                    pass

    def start_call_out(self, target=None):
        """
        Исходящий звонок: зовём собеседника. Собеседник
        решает, ответить или отклонить.
        """
        with self._lock:
            if self._state not in (IDLE, ENDED):
                return False
        self._set(RINGING_OUT, direction="out")
        return True

    def incoming_call(self):
        """
        Входящий звонок от собеседника. Начинается RINGING_IN.
        Ответ/отказ решает получатель.
        """
        with self._lock:
            if self._state not in (IDLE, ENDED):
                return False
        self._set(RINGING_IN, direction="in")
        return True

    def answer(self):
        """
        Ответить на звонок. Разговор (ACTIVE) начинается
        ТОЛЬКО здесь. Действует и на входящий, и на
        исходящий (собеседник ответил).
        """
        with self._lock:
            if self._state not in (
                RINGING_IN,
                RINGING_OUT,
            ):
                return False
            self._state = ACTIVE
            self._ended_at = 0.0
        cb = self._on_state_change
        if cb is not None:
            try:
                cb(ACTIVE, self._direction)
            except Exception:
                pass
        return True

    def reject(self):
        """
        Отклонить входящий звонок (получатель не берёт
        трубку). Разговор не начинается.
        """
        with self._lock:
            if self._state != RINGING_IN:
                return False
            self._state = ENDED
            self._ended_at = self._monotonic()
        cb = self._on_state_change
        if cb is not None:
            try:
                cb(ENDED, self._direction)
            except Exception:
                pass
        return True

    def end(self):
        """
        Завершить звонок: любая из сторон может завершить
        разговор. Действует из ACTIVE или RINGING.
        """
        with self._lock:
            if self._state in (IDLE, ENDED):
                return False
            self._state = ENDED
            self._ended_at = self._monotonic()
        cb = self._on_state_change
        if cb is not None:
            try:
                cb(ENDED, self._direction)
            except Exception:
                pass
        return True

    def idle_if_ended(self):
        """
        Возврат из ENDED в IDLE (внешне ENDED — короткий
        наблюдаемый хвост; для следующего звонка — IDLE).
        """
        with self._lock:
            if self._state != ENDED:
                return False
            if (
                self._monotonic() - self._ended_at
                < ENDED_TTL_SECONDS
            ):
                return False
            self._state = IDLE
            self._direction = None
        return True

    def eddie_starts_speaking(self):
        with self._lock:
            if self._state != ACTIVE:
                return
            was = self._last_speaker
            self._last_speaker = "eddie"
        if was == "eddieai":
            self._notify_interrupt()

    def eddie_stops_speaking(self):
        with self._lock:
            if self._state == ACTIVE:
                self._last_speaker = None

    def eddieai_starts_speaking(self):
        with self._lock:
            if self._state == ACTIVE:
                self._last_speaker = "eddieai"

    def eddieai_stops_speaking(self):
        with self._lock:
            if self._state == ACTIVE:
                self._last_speaker = None

    def _notify_interrupt(self):
        cb = self._on_interrupt_by
        if cb is None:
            return
        try:
            cb()
        except Exception:
            pass

    def _monotonic(self):
        import time

        return time.monotonic()
