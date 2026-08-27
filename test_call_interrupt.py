import time

from communication.call_engine import (
    CallDirector,
    EDDIE_SPEAKING,
    EDDIEAI_SPEAKING,
    IN_CALL,
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


def make_app():
    app = object.__new__(EddieChatApp)
    app._voice = FakeVoice()
    app._call = CallDirector()
    app._chat = None
    app._call.set_interrupt_callback(
        app._on_eddie_interrupt
    )
    return app


# 1. Дирижёр: переход EDDIEAI_SPEAKING -> EDDIE_SPEAKING
#    вызывает перехват (это и есть автопрерывание)
director = CallDirector()
fired = []
director.set_interrupt_callback(
    lambda: fired.append(True)
)
director.start_call()
director.eddieai_starts_speaking()
assert director.state() == EDDIEAI_SPEAKING
director.eddie_starts_speaking()
assert fired, "перехват не сработал"
assert director.state() == EDDIE_SPEAKING

# 2. Регрессия бага: без EDDIEAI_SPEAKING перехвата быть не должно
director2 = CallDirector()
fired2 = []
director2.set_interrupt_callback(
    lambda: fired2.append(True)
)
director2.start_call()
director2.eddie_starts_speaking()
assert not fired2, "перехват без отметки EddieAI говорящим"

# 3. Полный контур chat_app: EddieAI говорит, Эдди перебивает ->
#    озвучка остановлена, состояние EDDIE_SPEAKING
app = make_app()
app._call.start_call()
app._speak_with_detector(
    "Привет! Как дела?", None
)
assert app._voice.spoken == "Привет! Как дела?"
assert app._call.state() == EDDIEAI_SPEAKING
assert app._voice.detector_started == 1
app._voice.detector_cb()
assert app._voice.stopped is True, "озвучка не остановлена"
assert app._call.state() == EDDIE_SPEAKING

# 4. Вне звонка: озвучка есть, детектора и состояний нет
app2 = make_app()
app2._call.start_call()
app2._call.end_call()
app2._speak_with_detector("Снаружи звонка", None)
assert app2._voice.spoken == "Снаружи звонка"
assert app2._voice.detector_started == 0
assert app2._call.state() == IDLE

# 5. Естественное окончание речи возвращает состояние в IN_CALL
#    (reap-таймер)
app3 = make_app()
app3._call.start_call()
app3._speak_with_detector("Привет", None)
assert app3._call.state() == EDDIEAI_SPEAKING
time.sleep(1.5)
assert app3._call.state() == IN_CALL, app3._call.state()
assert app3._voice.detector_stopped >= 1

print("ALL PASS")