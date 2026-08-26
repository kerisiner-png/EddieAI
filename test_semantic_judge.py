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

# Авто-ремонт: при issue судья перегенерирует ответ
class FakeSeq:
    def __init__(self, replies):
        self.replies = list(replies)

    def _cloud_chat(self, system, user, options, task):
        return (
            self.replies.pop(0)
            if self.replies
            else "{}"
        )


judge = SemanticJudge(
    model_orchestrator=FakeSeq([
        '{"ok": false, "issue": "fabrication", '
        '"reason": "выдумал деятельность"}',
        "Честный ответ по сути.",
    ])
)

verdict = judge.judge("Что ты делал?", "Я летал на Марс.")

assert verdict["ok"] is False

retried = judge.regenerate(
    "Что ты делал?",
    "Я летал на Марс.",
    verdict,
)

assert retried == "Честный ответ по сути.", retried

# Ок-вердикт -> ремонт не нужен
assert judge.regenerate(
    "x", "y",
    {"ok": True, "issue": None},
) is None

print("ALL PASS")
