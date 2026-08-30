from communication.call_engine import (
    CallDirector,
    ACTIVE,
    IDLE,
)
from communication.chat_app import EddieChatApp


class FakeVoice:
    def __init__(self):
        self.stopped = False
        self.spoken = None
        self.detector_started = 0
        self.detector_stopped = 0
        self.detector_cb = None

    def speak(self, text, mood=None):
        self.spoken = text

    def start_interrupt_detector(self, cb):
        self.detector_started += 1
        self.detector_cb = cb

    def stop_interrupt_detector(self):
        self.detector_stopped += 1

    def stop_speaking(self):
        self.stopped = True

    def on_interrupt_detector_end(self, cb):
        self.detector_end_cb = cb


def make_active_call(director):
    director.start_call_out()
    director.answer()


def make_app():
    app = object.__new__(EddieChatApp)
    app._voice = FakeVoice()
    app._call = CallDirector()
    app._chat = None
    app._awaiting_speech_end = False
    app._call.set_interrupt_callback(
        app._on_eddie_interrupt
    )
    return app


# 1. Дирижёр: пока EddieAI говорит (eddieai), начавшая речь Эдди
#    (eddie) вызывает перехват — это и есть автопрерывание.
#    Состояние разговора остаётся ACTIVE.
director = CallDirector()
make_active_call(director)
fired = []
director.set_interrupt_callback(
    lambda: fired.append(True)
)
director.eddieai_starts_speaking()
assert director.state() == ACTIVE
director.eddie_starts_speaking()
assert fired, "перехват не сработал"
assert director.state() == ACTIVE

# 2. Регрессия бага: без отметки EddieAI говорящим перехвата быть не должно
director2 = CallDirector()
make_active_call(director2)
fired2 = []
director2.set_interrupt_callback(
    lambda: fired2.append(True)
)
director2.eddie_starts_speaking()
assert not fired2, "перехват без отметки EddieAI говорящим"

# 3. Полный контур chat_app: EddieAI говорит, Эдди перебивает ->
#    озвучка остановлена; разговор по-прежнему ACTIVE
app = make_app()
make_active_call(app._call)
app._speak_with_detector(
    "Привет! Как дела?", None
)
assert app._voice.spoken == "Привет! Как дела?"
assert app._eddieai_talking is True
app._on_detected_speech()
assert app._voice.stopped is True, "озвучка не остановлена"
assert app._awaiting_speech_end is True
assert app._call.state() == ACTIVE

# 4. Вне звонка: озвучка есть, детектора и состояния нет
app2 = make_app()
app2._speak_with_detector("Снаружи звонка", None)
assert app2._voice.spoken == "Снаружи звонка"
assert app2._voice.detector_started == 0
assert app2._call.state() == IDLE

# 5. Детектор прерывания вшит в контур: при озвучке в звонке
#    VoiceIO.start_interrupt_detector запущен с колбэком остановки;
#    вне звонка детектор не стартует (см. #4 выше).
app_det = make_app()
make_active_call(app_det._call)
app_det._speak_with_detector(
    "Привет", None
)
assert app_det._voice.detector_started == 1, (
    "детектор прерывания не запущен во время озвучки в звонке"
)
assert app_det._voice.detector_cb == (
    app_det._on_detected_speech
), "детектор не подключён к обработчику речи Эдди"

# 6. По завершении речи (reap) детектор останавливается
import time
time.sleep(1.2)
assert app_det._voice.detector_stopped == 1, (
    "детектор не остановлен после окончания озвучки"
)

# 7. Естественное окончание речи (reap): отметка EddieAI снимается,
#    разговор остаётся ACTIVE, и Эдди больше не блокируется ложным
#    перехватом (после паузы — реакция на его речь не срабатывает)
app3 = make_app()
make_active_call(app3._call)
app3._speak_with_detector("Привет", None)
assert app3._eddieai_talking is True
time_slept = None
import time

time.sleep(1.2)
assert app3._eddieai_talking is False, "reap не снял отметку речи"
assert app3._call.state() == ACTIVE
fired3 = []
app3._call.set_interrupt_callback(
    lambda: fired3.append(True)
)
app3._on_detected_speech()
assert not fired3, "ложный перехват после паузы"

# 6. После окончания речи Эдди (пауза) отметка собеседника снимается —
#    EddieAI снова может говорить, и его речь вновь прерываема
app4 = make_app()
make_active_call(app4._call)
app4._speak_with_detector(
    "Это важное сообщение", None
)
app4._on_detected_speech()
assert app4._awaiting_speech_end is True
assert app4._voice.stopped is True, "озвучка EddieAI не остановлена"

app4._on_detected_speech_end()
assert app4._awaiting_speech_end is False
assert app4._call.state() == ACTIVE

# после паузы EddieAI снова говорит, и перехват опять работает
fired4 = []
app4._call.set_interrupt_callback(
    lambda: fired4.append(True)
)
app4._call.eddieai_starts_speaking()
app4._call.eddie_starts_speaking()
assert fired4, "после паузы перехват не восстановился"
assert app4._call.state() == ACTIVE

print("ALL PASS")