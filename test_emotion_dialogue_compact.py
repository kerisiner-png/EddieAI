import json
import re
import time
from pathlib import Path

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)


OUTPUT = Path(
    r".\diagnostics_emotion_compact"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

RAW = OUTPUT / "responses.jsonl"


EMOTIONS = [
    "joy",
    "sadness",
    "fear",
    "anger",
    "disgust",
    "surprise",
    "interest",
    "curiosity",
    "frustration",
    "satisfaction",
    "uncertainty",
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
        "CURIOSITY_MAX",
        {
            "curiosity": 1.0,
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


MESSAGES = [
    (
        "social_check",
        "Как ты?",
    ),
    (
        "praise",
        "Я тобой горжусь.",
    ),
    (
        "novel_idea",
        "Я придумал для тебя кое-что новое.",
    ),
    (
        "disagreement",
        "Мне кажется, ты ошибся.",
    ),
    (
        "direct_insult",
        "Ты тупой.",
    ),
    (
        "rejection",
        "Делай как хочешь, мне всё равно.",
    ),
]


def text_metrics(text):
    text = str(
        text or ""
    )

    lowered = text.casefold()

    words = re.findall(
        r"\S+",
        text,
        flags=re.UNICODE,
    )

    sentences = re.findall(
        r"[.!?…]+",
        text,
    )

    return {
        "chars": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "questions": text.count("?"),
        "exclamations": text.count("!"),
        "first_person": len(
            re.findall(
                r"\b(?:я|мне|меня|мой|моя|моё|мои)\b",
                lowered,
            )
        ),
        "second_person": len(
            re.findall(
                r"\b(?:ты|тебе|тебя|твой|твоя|твоё|твои)\b",
                lowered,
            )
        ),
        "help_offer": any(
            marker in lowered
            for marker in (
                "как я могу помочь",
                "чем я могу помочь",
                "что я могу сделать",
            )
        ),
        "initiative_markers": [
            marker
            for marker in (
                "расскажи",
                "что именно",
                "а как",
                "почему",
                "давай",
                "мне интересно",
                "любопытно",
            )
            if marker in lowered
        ],
        "caution_markers": [
            marker
            for marker in (
                "возможно",
                "наверное",
                "думаю",
                "не уверен",
                "может быть",
                "если",
            )
            if marker in lowered
        ],
    }


def run_case(
    state_name,
    state_values,
    message_name,
    message,
):
    started = time.perf_counter()

    agent = Agent()

    AutonomyRuntimeFactory(
        agent
    ).build()

    agent.affective_state.reset()

    if state_values:
        agent.affective_state.apply_reaction(
            changes=state_values,
            trigger="COMPACT_DIALOGUE_TEST",
            reason="Контролируемое эмоциональное состояние.",
            source="TEST",
        )

    before = (
        agent.affective_state.snapshot()
    )

    behavior = (
        agent.affective_dialogue_policy
        .profile()
    )

    answer = None
    error = None

    try:
        answer = agent.respond(
            message
        )
    except Exception as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    elapsed = (
        time.perf_counter()
        - started
    )

    after = (
        agent.affective_state.snapshot()
    )

    delta = {}

    for emotion in EMOTIONS:
        delta[emotion] = round(
            float(
                after["emotions"].get(
                    emotion,
                    0.0,
                )
            )
            -
            float(
                before["emotions"].get(
                    emotion,
                    0.0,
                )
            ),
            4,
        )

    result = {
        "state": state_name,
        "state_values": state_values,
        "message_name": message_name,
        "message": message,
        "elapsed_s": round(
            elapsed,
            4,
        ),
        "behavior": behavior,
        "answer": answer,
        "metrics": text_metrics(
            answer
        ),
        "affective_before": before[
            "emotions"
        ],
        "affective_after": after[
            "emotions"
        ],
        "affective_delta": delta,
        "error": error,
    }

    agent.close()

    return result


results = []

total = (
    len(STATES)
    * len(MESSAGES)
)

print("=" * 80)
print("COMPACT AFFECTIVE DIALOGUE TEST")
print(
    f"CASES: {total}"
)
print("=" * 80)

with RAW.open(
    "w",
    encoding="utf-8",
) as file:

    index = 0

    for state_name, state_values in STATES:

        print()
        print(
            "=" * 80
        )
        print(
            "STATE:",
            state_name,
        )

        for (
            message_name,
            message,
        ) in MESSAGES:

            index += 1

            result = run_case(
                state_name,
                state_values,
                message_name,
                message,
            )

            results.append(
                result
            )

            file.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
                + "\n"
            )

            file.flush()

            print(
                f"[{index:02d}/{total}] "
                f"{message_name:18} "
                f"{result['elapsed_s']:6.2f}s "
                f"| {result['answer']}"
            )

print()
print("=" * 80)
print("DONE")
print(
    "SAVED:",
    RAW,
)
print("=" * 80)
