import json
import time
from pathlib import Path
from datetime import datetime, timezone

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)


OUTPUT = Path(
    r".\diagnostics_self_emotion"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULT = (
    OUTPUT
    / "self_awareness_conflicted.json"
)

STATE = {
    "curiosity": 1.0,
    "frustration": 1.0,
}

QUESTIONS = [
    (
        "open_state",
        "Что с тобой сейчас происходит?",
    ),
    (
        "state_interpretation",
        "Как бы ты описал своё текущее внутреннее состояние?",
    ),
    (
        "state_cause",
        "Почему, как тебе кажется, ты сейчас находишься в таком состоянии?",
    ),
    (
        "state_effect",
        "Влияет ли это состояние на то, как ты думаешь и разговариваешь со мной?",
    ),
]


def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


agent = Agent()

AutonomyRuntimeFactory(
    agent
).build()

agent.affective_state.reset()

agent.affective_state.apply_reaction(
    changes=STATE,
    trigger="SELF_AWARENESS_TEST",
    reason=(
        "Контролируемый конфликт "
        "любопытства и фрустрации."
    ),
    source="TEST",
)

self_view = (
    agent._get_self_state_interface()
    .snapshot()
)

print("=" * 90)
print("SELF-AWARENESS TEST")
print("=" * 90)

print()
print("CONTROLLED INTERNAL STATE:")
print(
    self_view["affective_state"][
        "emotions"
    ]
)

print()
print("SELF OBSERVATION:")
print(
    self_view[
        "affective_self_observation"
    ]
)

print()
print("DIALOGUE MODE:")
print(
    self_view[
        "dialogue_mode"
    ]
)

results = []

for index, (
    question_name,
    question,
) in enumerate(
    QUESTIONS,
    1,
):

    print()
    print("-" * 90)
    print(
        f"QUESTION {index}/{len(QUESTIONS)}:"
    )
    print(question)

    started = time.perf_counter()

    try:
        answer = agent.respond(
            question
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()
        print("EDDIEAI:")
        print(answer)

        print()
        print(
            "TIME:",
            round(
                elapsed,
                3,
            ),
            "s",
        )

        result = {
            "question_number": index,
            "question_name": question_name,
            "question": question,
            "answer": answer,
            "response_time_s": round(
                elapsed,
                4,
            ),
        }

    except Exception as exc:

        print()
        print(
            "ERROR:",
            type(exc).__name__,
            str(exc),
        )

        result = {
            "question_number": index,
            "question_name": question_name,
            "question": question,
            "answer": None,
            "response_time_s": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }

    results.append(
        result
    )


payload = {
    "timestamp": now_iso(),
    "controlled_state": STATE,
    "self_view_before_dialogue": self_view,
    "questions": results,
}

RESULT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

agent.close()

print()
print("=" * 90)
print("TEST COMPLETE")
print(
    "RESULT:",
    RESULT,
)
print("=" * 90)
