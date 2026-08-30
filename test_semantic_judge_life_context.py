import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.semantic_judge import SemanticJudge


class FakeLlm:
    def __init__(self):
        self.calls = []

    def chat(self, system, user, options, task):
        self.calls.append(user)
        return '{"ok": true, "issue": null, "reason": "чисто"}'


def _judge_with(llm):
    judge = object.__new__(SemanticJudge)
    judge.enabled = True
    judge.llm = llm
    return judge


def test_judge_passes_life_context():
    llm = FakeLlm()
    judge = _judge_with(llm)
    verdict = judge.judge(
        "Что ты нашёл?",
        "Я провёл исследование и нашёл: связь интересна (URL).",
        life_context=(
            "РЕЗУЛЬТАТЫ ТВОИХ ДЕЙСТВИЙ\n"
            "[21:00] Инструмент research выполнил действие "
            "'исследовать связь'. Найдено 5 результатов."
        ),
    )
    assert verdict["ok"] is True
    assert "связь интересна" in llm.calls[0]
    assert "Реальные недавние факты" in llm.calls[0]
    assert "исследовать связь" in llm.calls[0]


def test_judge_without_life_context_stays_compact():
    llm = FakeLlm()
    judge = _judge_with(llm)
    judge.judge("Привет", "Привет, Эдди.")
    assert "Реальные недавние факты" not in llm.calls[0]


def test_regenerate_passes_life_context():
    llm = FakeLlm()
    judge = _judge_with(llm)
    judge.regenerate(
        "Что ты нашёл?",
        "Я нашёл связь.",
        {"issue": "fabrication", "reason": "нет во входных данных"},
        life_context=(
            "РЕЗУЛЬТАТЫ ТВОИХ ДЕЙСТВИЙ\n"
            "[21:00] Инструмент research нашёл 5 результатов."
        ),
    )
    assert "РЕЗУЛЬТАТЫ ТВОИХ ДЕЙСТВИЙ" in llm.calls[0]
    assert "5 результатов" in llm.calls[0]


if __name__ == "__main__":
    test_judge_passes_life_context()
    test_judge_without_life_context_stays_compact()
    test_regenerate_passes_life_context()
    print("ALL OK")