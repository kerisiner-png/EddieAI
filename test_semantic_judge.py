from core.semantic_judge import SemanticJudge


class Fake:
    def __init__(self, reply):
        self.reply = reply

    def _cloud_chat(self, system, user, options, task):
        return self.reply


# Фабрикация -> судья отвергает
judge = SemanticJudge(
    model_orchestrator=Fake(
        '{"ok": false, "issue": "fabrication", '
        '"reason": "ответ приписывает себе несуществующую деятельность"}'
    )
)

verdict = judge.judge(
    "Что ты делал вчера?",
    "Я вчера запускал ракеты в космос.",
)

assert verdict["ok"] is False
assert verdict["issue"] == "fabrication"

# Уклонение
judge = SemanticJudge(
    model_orchestrator=Fake(
        '{"ok": false, "issue": "evasion", "reason": "не отвечает"}'
    )
)

verdict = judge.judge(
    "Сколько будет 2+2?",
    "Сложный вопрос, давай обсудим философию чисел.",
)

assert verdict["ok"] is False
assert verdict["issue"] == "evasion"

# Адекватный ответ
judge = SemanticJudge(
    model_orchestrator=Fake(
        '{"ok": true, "issue": null, "reason": ""}'
    )
)

verdict = judge.judge(
    "Привет",
    "Привет, рад тебя слышать.",
)

assert verdict["ok"] is True
assert verdict["issue"] is None

# Судья выключен (без orchestrator)
judge = SemanticJudge()

verdict = judge.judge("x", "y")

assert verdict["ok"] is True
assert verdict["issue"] is None

# Пустой ответ
verdict = SemanticJudge(
    model_orchestrator=Fake('{}')
).judge("x", "  ")

assert verdict["ok"] is False
assert verdict["issue"] == "empty"

print("ALL PASS")
