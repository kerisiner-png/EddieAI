import threading


IDLE = "IDLE"
IN_CALL = "IN_CALL"
EDDIE_SPEAKING = "EDDIE_SPEAKING"
EDDIEAI_SPEAKING = "EDDIEAI_SPEAKING"

SPEAKING = {
    EDDIE_SPEAKING,
    EDDIEAI_SPEAKING,
}


class CallDirector:
    """
    Дирижёр голосового звонка (turn-taking).

    Хранит состояние звонка и отвечает на вопрос
    «кто сейчас может говорить». Звонок живёт
    внутри мессенджера, поэтому дирижёр не зависит
    от аудио/UI и тестируется юнит-тестом.
    """

    def __init__(self):
        self._state = IDLE
        self._lock = threading.Lock()
        self._on_interrupt_by_eddie = None

    def set_interrupt_callback(self, callback):
        self._on_interrupt_by_eddie = callback

    def state(self):
        with self._lock:
            return self._state

    def in_call(self):
        return self.state() != IDLE

    def start_call(self):
        with self._lock:
            if self._state == IDLE:
                self._state = IN_CALL

    def end_call(self):
        with self._lock:
            self._state = IDLE

    def eddie_starts_speaking(self):
        with self._lock:
            was = self._state
            self._state = EDDIE_SPEAKING
        if was == EDDIEAI_SPEAKING:
            self._notify_interrupt()

    def eddie_stops_speaking(self):
        with self._lock:
            if self._state == EDDIE_SPEAKING:
                self._state = IN_CALL

    def eddieai_starts_speaking(self):
        with self._lock:
            if self._state == EDDIEAI_SPEAKING:
                return
            self._state = EDDIEAI_SPEAKING

    def eddieai_stops_speaking(self):
        with self._lock:
            if self._state == EDDIEAI_SPEAKING:
                self._state = IN_CALL

    def _notify_interrupt(self):
        cb = self._on_interrupt_by_eddie
        if cb is None:
            return
        try:
            cb()
        except Exception:
            pass
