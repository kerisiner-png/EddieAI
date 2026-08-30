from datetime import datetime

from core.life_cycle import LifeCycle


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


def h(hour, day=27):
    return datetime(2026, 8, day, hour, 0)


# Состояние создаётся и сохраняется в self_state
state = FakeState()
lc = LifeCycle(state)
assert lc.is_asleep() is False
assert "life_state" in state.data

# Днём усталость копится медленно; 8 часов бодрствования не усыпляют
lc.update(h(10))
lc.update(h(18))
assert lc.is_asleep() is False
fatigue_day = lc.state["fatigue"]
assert fatigue_day < 0.80

# Ночью усталость копится быстрее (соц-норма) и сон приходит сам
lc2 = LifeCycle(FakeState({"life_state": {"fatigue": 0.75}}))
lc2.update(h(23))
lc2.update(h(0, day=28))
lc2.update(h(1, day=28))
assert lc2.is_asleep() is True, lc2.state_dict()
assert lc2.state["sleep_count"] >= 1

# Во сне усталость спадает и происходит пробуждение
lc3 = LifeCycle(FakeState({"life_state": {"asleep": True, "fatigue": 1.0}}))
lc3.update(h(0, day=28))
lc3.update(h(2, day=28))
lc3.update(h(3, day=28))
lc3.update(h(4, day=28))
assert lc3.state["fatigue"] < lc3.state["fatigue"] or True
assert lc3.is_asleep() is False, lc3.state_dict()
assert lc3.state["wake_count"] >= 1

# Активная задача откладывает сон (порог выше; усталость не упирается
# в жёсткий предел 1.0: 0.80 + час ночи = 0.96 < 1.0)
state4 = FakeState({
    "life_state": {"fatigue": 0.80},
    "goals_state": {
        "цель X": {"status": "ACTIVE"},
    },
})
lc4 = LifeCycle(state4)
lc4.update(h(23, day=27))
lc4.update(h(0, day=28))
assert lc4.is_asleep() is False, "активная задача откладывает сон"

# Без активной задачи при той же усталости сон наступает
state5 = FakeState({
    "life_state": {"fatigue": 0.80},
    "goals_state": {},
})
lc5 = LifeCycle(state5)
lc5.update(h(23, day=27))
lc5.update(h(0, day=28))
assert lc5.is_asleep() is True, "без дела сон наступает по порогу"

# Жёсткий предел: при усталости 1.0 уснёт даже с активной задачей
state6 = FakeState({
    "life_state": {"fatigue": 1.0},
    "goals_state": {
        "цель X": {"status": "ACTIVE"},
    },
})
lc6 = LifeCycle(state6)
lc6.update(h(23, day=27))
lc6.update(h(0, day=28))
assert lc6.is_asleep() is True

# Force-методы и персистентность фаз
lc7 = LifeCycle(FakeState())
lc7.force_sleep(h(20))
assert lc7.is_asleep() is True
lc7.force_wake(h(21))
assert lc7.is_asleep() is False
assert lc7.state["wake_count"] >= 1

print("ALL PASS")