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

    def on_interrupt_detector_end(self, cb):
        self.detector_end_cb = cb


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

# 6. Окончание речи собеседника (этап 4): после перехвата Эдди
#    детектор доживает до паузы и сбрасывает EDDIE_SPEAKING -> IN_CALL,
#    чтобы EddieAI снова мог говорить. Озвучка EddieAI остановлена,
#    детектор НЕ гасится при перехвате.
app4 = make_app()
app4._call.start_call()
app4._speak_with_detector(
    "Это важное сообщение", None
)
assert app4._call.state() == EDDIEAI_SPEAKING
assert app4._voice.detector_end_cb is not None, \
    "end-callback не зарегистрирован"

app4._voice.detector_cb()  # Эдди начал говорить (перехват)
assert app4._awaiting_speech_end is True
assert app4._voice.stopped is True, "озвучка EddieAI не остановлена"
assert app4._call.state() == EDDIE_SPEAKING

app4._voice.detector_end_cb()  # пауза после речи Эдди
assert app4._awaiting_speech_end is False
assert app4._call.state() == IN_CALL, \
    f"ожидался IN_CALL, получен {app4._call.state()}"

# после IN_CALL EddieAI снова может говорить
app4._call.eddieai_starts_speaking()
assert app4._call.state() == EDDIEAI_SPEAKING

# 7. Без перехвата (Эдди молчит) end-callback НЕ срабатывает при
#    естественной паузе детектора — reap сам гасит детектор
#    (speech_seen=False, пауза не даёт on_speech_end).
app5 = make_app()
app5._call.start_call()
app5._speak_with_detector("Тишина", None)
assert app5._awaiting_speech_end is False
time.sleep(1.5)
assert app5._call.state() == IN_CALL
assert app5._voice.detector_stopped >= 1

print("ALL PASS")