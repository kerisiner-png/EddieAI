from datetime import datetime, timezone

from core.situation import encode_situation


def build_state(**overrides):
    state = {
        "goal": "Изучить тему: космос",
        "task_type": "research",
        "inbox_unread": 0,
        "affect": {"valence": 0.6},
        "period": "day",
        "freshness": 5,
        "now": datetime(
            2026, 8, 26, 14, 0,
            tzinfo=timezone.utc,
        ),
    }

    state.update(overrides)

    return state


base = build_state()

same = build_state()

key_a = encode_situation(base)
key_b = encode_situation(same)

print("KEY_A:", key_a)
print("KEY_B:", key_b)

assert key_a == key_b, "одинаковые состояния должны давать одинаковый ключ"

different = encode_situation(
    build_state(goal="Изучить тему: океан")
)

print("KEY_C:", different)

assert key_a != different, "разные цели должны давать разные ключи"

inbox = encode_situation(
    build_state(inbox_unread=2)
)

print("KEY_D:", inbox)

assert key_a != inbox, "разное наличие почты должно давать разные ключи"

affect = encode_situation(
    build_state(affect={"valence": -0.8})
)

print("KEY_E:", affect)

assert key_a != affect, "разный аффект должен давать разные ключи"

period = encode_situation(
    build_state(
        period=None,
        now=datetime(
            2026, 8, 26, 23, 0,
            tzinfo=timezone.utc,
        ),
    )
)

print("KEY_F:", period)

assert key_a != period, "разное время суток должно давать разные ключи"

freshness = encode_situation(
    build_state(freshness=900)
)

print("KEY_G:", freshness)

assert key_a != freshness, "разная свежесть должна давать разные ключи"

print("ALL PASS")
