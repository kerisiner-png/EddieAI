from identity.behavioral_validator import (
    BehavioralValidator,
    BehavioralViolation,
)


validator = BehavioralValidator()

# Незначительное нарушение не должно ремонтироваться
minor = BehavioralViolation(
    kind="CONFLICTED_NO_NEXT_STEP",
    details="тестовый сигнал",
    severity=0.30,
)

assert validator.should_repair([minor]) is False, (
    "severity 0.30 не должно триггерить ремонт"
)

# CONFLICTED БЕЗ требования вопроса -> нет нарушения
violations = validator.validate(
    "Я просто отвечаю кратко.",
    {
        "mode": "CONFLICTED",
        "question_required": False,
        "max_sentences": 3,
    },
)

kinds = [item.kind for item in violations]

assert "CONFLICTED_NO_NEXT_STEP" not in kinds, kinds

# CONFLICTED с требованием вопроса и без "?"
# -> есть, но незначимое (0.30, не ремонтируется)
violations = validator.validate(
    "Я просто отвечаю кратко.",
    {
        "mode": "CONFLICTED",
        "question_required": True,
        "max_sentences": 3,
    },
)

hit = [
    item
    for item in violations
    if item.kind == "CONFLICTED_NO_NEXT_STEP"
]

assert hit, "требование вопроса без '?' должно давать сигнал"
assert hit[0].severity == 0.30, hit[0]

assert validator.should_repair(violations) is False, (
    "набор только из незначимых нарушений "
    "не должен ремонтироваться"
)

print("ALL PASS")
