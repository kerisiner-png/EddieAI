import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.decision_core import DecisionCore
from identity.goal_manager import GoalManager
from identity.goal_planner import GoalPlanner
from identity.self_state import SelfState
from memory.database import Memory


STATE = {
    "goal": None,
    "task_type": None,
    "inbox_unread": 0,
    "affect": {"valence": 0.6},
    "period": "evening",
    "freshness": 5,
    "idle_seconds": 0,
}


def _dead_goal(goal_manager, value):
    goal_manager.add_candidate(
        value=value,
        motivation=0.7,
        priority=0.7,
        confidence=0.7,
    )
    goal_manager.ensure_plan(
        value,
        ["Собрать материал"],
    )
    goal_manager.planner.complete_task(
        value,
        "Собрать материал",
    )
    goal_manager.complete(value)


def _pattern(core, value):
    return json.dumps(
        {
            "kind": "ACTIVATE_GOAL",
            "payload": {"value": value},
        },
        ensure_ascii=False,
    )


with TemporaryDirectory() as temp:
    # 1. Паттерн ведёт на завершённую цель с исчерпанным
    #    планом -> карусель должна не срабатывать.
    state1 = SelfState(Path(temp) / "s1.json")
    state1.set("interests", [])
    db1 = Memory(Path(temp) / "m1.db")
    gm1 = GoalManager(state1, GoalPlanner(state1))
    core1 = DecisionCore(memory=db1, goal_manager=gm1)

    _dead_goal(
        gm1,
        "изучить тему: понимание устройства мира",
    )

    db1.pattern_record(
        core1.key(STATE),
        _pattern(
            core1,
            "изучить тему: понимание устройства мира",
        ),
        confidence=0.5,
    )

    decision = core1.decide(STATE)

    assert decision.kind != "ACTIVATE_GOAL", decision

    cmp = db1.pattern_lookup(core1.key(STATE))
    assert cmp is not None
    assert cmp["times_used"] == 0, cmp["times_used"]

    # 2. Скука (интерес) на завершённую цель:
    #    пустой learn-паттерн не должен сеяться.
    state2 = SelfState(Path(temp) / "s2.json")
    state2.set("interests", ["понимание устройства мира"])
    db2 = Memory(Path(temp) / "m2.db")
    gm2 = GoalManager(state2, GoalPlanner(state2))
    core2 = DecisionCore(memory=db2, goal_manager=gm2)

    _dead_goal(
        gm2,
        "изучить тему: понимание устройства мира",
    )

    decision = core2.decide(STATE)

    assert decision.kind != "ACTIVATE_GOAL", decision

    assert db2.pattern_lookup(core2.key(STATE)) is None, (
        "learn не должен засеивать бесполезный паттерн"
    )

    # 3. Живая цель (с PENDING-задачами) активируется
    #    через паттерн как обычно.
    state3 = SelfState(Path(temp) / "s3.json")
    state3.set("interests", [])
    db3 = Memory(Path(temp) / "m3.db")
    gm3 = GoalManager(state3, GoalPlanner(state3))
    core3 = DecisionCore(memory=db3, goal_manager=gm3)

    gm3.add_candidate(
        value="исследовать: северное сияние",
        motivation=0.9,
        priority=0.9,
        confidence=0.9,
    )
    gm3.ensure_plan(
        "исследовать: северное сияние",
        ["Собрать фотографии"],
    )

    db3.pattern_record(
        core3.key(STATE),
        _pattern(core3, "исследовать: северное сияние"),
        confidence=0.5,
    )

    decision = core3.decide(STATE)

    assert decision.kind == "ACTIVATE_GOAL", decision
    assert decision.payload == {
        "value": "исследовать: северное сияние"
    }, decision

    db1.close()
    db2.close()
    db3.close()

    # 4. Публичный наука-сев learn_from_memory():
    #    dead-цель не сеет паттерн, живой интерес — сеет.
    state4 = SelfState(Path(temp) / "s4.json")
    state4.set("interests", ["понимание устройства мира"])
    db4 = Memory(Path(temp) / "m4.db")
    gm4 = GoalManager(state4, GoalPlanner(state4))
    core4 = DecisionCore(memory=db4, goal_manager=gm4)

    _dead_goal(
        gm4,
        "изучить тему: понимание устройства мира",
    )

    seeded = core4.learn_from_memory()

    assert seeded == 0, seeded
    assert db4.pattern_lookup(core4._idle_key()) is None, (
        "learn_from_memory не должен сеять dead-паттерн"
    )

    db4.close()

    state5 = SelfState(Path(temp) / "s5.json")
    state5.set("interests", ["аквариумистика"])
    db5 = Memory(Path(temp) / "m5.db")
    gm5 = GoalManager(state5, GoalPlanner(state5))
    core5 = DecisionCore(memory=db5, goal_manager=gm5)

    seeded = core5.learn_from_memory()

    assert seeded == 1, seeded
    cmp = db5.pattern_lookup(core5._idle_key())
    assert cmp is not None and cmp["times_used"] == 0, cmp
    import json as _json
    payload = _json.loads(cmp["action"])["payload"]
    assert payload == {
        "value": "изучить тему: аквариумистика"
    }, payload

    db5.close()

print("ALL OK")