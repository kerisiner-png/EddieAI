import random

from core.dream_processor import (
    DreamProcessor,
)


class FakeMemory:
    def __init__(self):
        self.saved = []
        self.life_feed = (
            "[22:40] Я закончил большой розыск.\n"
            "[22:55] Эдди поблагодарил меня за идею."
        )
        self.actions_feed = (
            "[22:50] Инструмент research: "
            "Найдено 5 результатов: ссылки"
        )

    def recent_life_feed(self, limit=8):
        return self.life_feed

    def recent_action_results(self, limit=4):
        return self.actions_feed

    def remember(self, event):
        self.saved.append(event)
        return len(self.saved)


class FakeAffective:
    def __init__(self):
        self.calls = []

    def apply_reaction(
        self,
        *,
        changes,
        trigger,
        reason,
        source,
        metadata=None,
    ):
        self.calls.append({
            "changes": changes,
            "trigger": trigger,
            "reason": reason,
            "source": source,
            "metadata": metadata,
        })


class FakeDiary:
    def __init__(self):
        self.entries = []

    def write(self, entry, trigger="dream"):
        self.entries.append(entry)
        return len(self.entries)


class FakeModel:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def _cloud_chat(self, system, user, options=None):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


DREAM_JSON = (
    '{"scene": "Я иду по ночной школе, '
    'светящиеся коридоры складываются в формулы", '
    '"emotion": "curiosity", '
    '"intensity": 0.8, "theme": "исследование"}'
)

SEGMENTS = [
    {"text": "Я закончил большой розыск по интересу про школы.", "type": "day"},
    {"text": "Эдди поблагодарил меня за идею.", "type": "day"},
    {"text": "Инструмент research нашёл 5 результатов.", "type": "tool"},
]

# 1. Пустая жатва → тихий сон, ничего не пишем
dp = DreamProcessor(
    memory=None,
    diary=FakeDiary(),
    model=FakeModel(DREAM_JSON),
)
res = dp.process(segments=[])
assert res["status"] == "empty", res

# 2. Полный конвейер: кадры → сон → эмоция (демпфер) → записи
mem = FakeMemory()
aff = FakeAffective()
diary = FakeDiary()
model = FakeModel(DREAM_JSON)
dp = DreamProcessor(
    memory=mem,
    affective_state=aff,
    diary=diary,
    model=model,
    rng=random.Random(7),
)
res = dp.process()
assert res["status"] == "dreamed", res
assert res["emotion"] == "curiosity"
assert res["intensity"] == 0.8
assert len(aff.calls) == 1, aff.calls
delta = aff.calls[0]["changes"].get("curiosity")
assert delta == round(0.8 * 0.5 * 0.25, 4), delta
assert aff.calls[0]["source"] == "DREAM"
assert aff.calls[0]["trigger"] == "dream"
assert len(mem.saved) == 2, \
    "DREAM-событие + DREAM_INTERPRETATION записаны"
assert mem.saved[0].source_type == "DREAM"
assert mem.saved[0].confidence == 0.25
assert mem.saved[1].source_type == "DREAM_INTERPRETATION"
assert mem.saved[1].confidence == 0.35
assert len(diary.entries) == 1
assert "снилось" in diary.entries[0]

# 3. Сбой модели (не-JSON) → фолбэк-сон, но запись остаётся
mem2 = FakeMemory()
aff2 = FakeAffective()
dp = DreamProcessor(
    memory=mem2,
    affective_state=aff2,
    diary=FakeDiary(),
    model=FakeModel("не JSON вовсе"),
    rng=random.Random(1),
)
res = dp.process()
assert res["status"] == "dreamed", res
assert res["emotion"] == "neutral"
assert res["intensity"] == 0.1
assert len(mem2.saved) >= 1, "запись сна не потеряна при сбое"
assert aff2.calls[0]["changes"].get("neutral") == 0.1 * 0.5 * 0.25

# 4. Эмоция вне списка → нейтральный фолбэк
dp = DreamProcessor(
    memory=FakeMemory(),
    affective_state=FakeAffective(),
    diary=FakeDiary(),
    model=FakeModel(
        '{"scene": "сон", "emotion": "euphoria", '
        '"intensity": 0.9, "theme": "x"}'
    ),
    rng=random.Random(2),
)
res = dp.process()
assert res["emotion"] == "neutral"

# 5. Детерминизм: тот же seed → те же кадры
dp_a = DreamProcessor(
    memory=FakeMemory(),
    diary=FakeDiary(),
    model=None,
    rng=random.Random(42),
)
dp_b = DreamProcessor(
    memory=FakeMemory(),
    diary=FakeDiary(),
    model=None,
    rng=random.Random(42),
)
fa = dp_a.frames(dp_a.replay(SEGMENTS))
fb = dp_b.frames(dp_b.replay(SEGMENTS))
assert [f["scene"] for f in fa] == [f["scene"] for f in fb]

# 6. Сон без модели (dry, офлайн в тестах) не падает
dp = DreamProcessor(
    memory=FakeMemory(),
    diary=FakeDiary(),
    model=None,
    rng=random.Random(3),
)
res = dp.process()
assert res["status"] in ("dreamed", "empty")
assert model is None or isinstance(res["status"], str)

# 7. Лимит повторов сюжета: кадров не больше max_frames,
#    повтор одной композиции не превышает plot_repeat_limit
dp = DreamProcessor(
    memory=FakeMemory(),
    diary=FakeDiary(),
    model=None,
    rng=random.Random(4),
    max_frames=4,
    plot_repeat_limit=3,
)
replay = dp.replay([{"text": "одна и та же закрытая ситуация.", "type": "day"}] * 6)
frames = dp.frames(replay)
assert len(frames) <= 4
scenes = [f["scene"] for f in frames]
assert len(set(scenes)) <= 3, "повтор сюжета превысил лимит"

print("ALL PASS")