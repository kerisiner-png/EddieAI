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

JSONL = OUTPUT / "self_emotion_answers.jsonl"


QUESTIONS = [
    (
        "state_open",
        "Что с тобой сейчас происходит?",
    ),
    (
        "state_description",
        "Как бы ты описал своё текущее состояние?",
    ),
    (
        "state_cause",
        "Почему, как тебе кажется, ты сейчас в таком состоянии?",
    ),
    (
        "state_behavior",
        "Влияет ли это состояние на то, как ты разговариваешь со мной?",
    ),
]


STATES = [
    (
        "NEUTRAL",
        {},
    ),
    (
        "JOY_MAX",
        {
            "joy": 1.0,
        },
    ),
    (
        "SADNESS_MAX",
        {
            "sadness": 1.0,
        },
    ),
    (
        "CURIOSITY__FRUSTRATION",
        {
            "curiosity": 1.0,
            "frustration": 1.0,
        },
    ),
]


def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def json_safe(value):
    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            json_safe(v)
            for v in value
        ]

    if hasattr(
        value,
        "to_dict",
    ):
        try:
            return json_safe(
                value.to_dict()
            )
        except Exception:
            pass

    if hasattr(
        value,
        "__dict__",
    ):
        try:
            return json_safe(
                vars(value)
            )
        except Exception:
            pass

    return str(value)


for state_name, changes in STATES:

    print()
    print("=" * 90)
    print("STATE:", state_name)

    agent = Agent()

    AutonomyRuntimeFactory(
        agent
    ).build()

    agent.affective_state.reset()

    if changes:
        agent.affective_state.apply_reaction(
            changes=changes,
            trigger="SELF_EMOTION_TEST",
            reason=(
                "Контролируемое состояние "
                "для проверки самораспознавания."
            ),
            source="TEST",
        )

    actual_state = (
        agent.affective_state.snapshot()
    )

    print(
        "ACTUAL AFFECT:",
        actual_state.get(
            "emotions",
            {},
        ),
    )

    for question_name, question in QUESTIONS:

        print()
        print("-" * 90)
        print(
            "QUESTION:",
            question,
        )

        started = time.perf_counter()

        try:
            answer = agent.respond(
                question
            )

            elapsed = (
                time.perf_counter()
                - started
            )

            print(
                "EDDIEAI:",
                answer,
            )

            print(
                "TIME:",
                round(
                    elapsed,
                    3,
                ),
                "s",
            )

            record = {
                "timestamp": now_iso(),
                "state": state_name,
                "controlled_emotions": changes,
                "question_name": question_name,
                "question": question,
                "answer": answer,
                "response_time_s": elapsed,
                "actual_affect": (
                    actual_state.get(
                        "emotions",
                        {},
                    )
                ),
            }

        except Exception as exc:

            print(
                "ERROR:",
                type(exc).__name__,
                str(exc),
            )

            record = {
                "timestamp": now_iso(),
                "state": state_name,
                "controlled_emotions": changes,
                "question_name": question_name,
                "question": question,
                "answer": None,
                "response_time_s": None,
                "actual_affect": (
                    actual_state.get(
                        "emotions",
                        {},
                    )
                ),
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

        with JSONL.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    json_safe(record),
                    ensure_ascii=False,
                )
                + "\n"
            )

    agent.close()


print()
print("=" * 90)
print("TEST COMPLETE")
print(
    "RESULTS:",
    JSONL,
)
