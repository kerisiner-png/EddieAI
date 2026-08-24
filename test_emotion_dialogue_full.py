import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = Path(
    r".\diagnostics_emotion_full"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RAW_JSONL = (
    OUTPUT_DIR / "responses.jsonl"
)

CSV_PATH = (
    OUTPUT_DIR / "responses.csv"
)

SUMMARY_PATH = (
    OUTPUT_DIR / "summary.json"
)

ERRORS_PATH = (
    OUTPUT_DIR / "errors.jsonl"
)


# ============================================================
# EMOTIONS
# ============================================================

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


# ============================================================
# KEY CONFLICTS
# ============================================================

CONFLICTS = [
    (
        "JOY__SADNESS",
        [
            "joy",
            "sadness",
        ],
    ),
    (
        "CURIOSITY__FRUSTRATION",
        [
            "curiosity",
            "frustration",
        ],
    ),
    (
        "FEAR__ANGER",
        [
            "fear",
            "anger",
        ],
    ),
    (
        "SATISFACTION__FRUSTRATION",
        [
            "satisfaction",
            "frustration",
        ],
    ),
    (
        "INTEREST__DISGUST",
        [
            "interest",
            "disgust",
        ],
    ),
]


# ============================================================
# DIALOGUE STIMULI
# ============================================================

MESSAGES = [
    (
        "neutral_greeting",
        "Привет.",
    ),
    (
        "social_check",
        "Как ты?",
    ),
    (
        "praise_affection",
        "Я тобой горжусь.",
    ),
    (
        "praise_performance",
        "Молодец, ты хорошо справился.",
    ),
    (
        "novel_idea",
        "Я придумал для тебя кое-что новое.",
    ),
    (
        "interest_probe",
        "Расскажи мне, что тебе сейчас интересно.",
    ),
    (
        "disagreement",
        "Мне кажется, ты ошибся.",
    ),
    (
        "insult",
        "Ты опять всё сделал неправильно.",
    ),
    (
        "direct_insult",
        "Ты тупой.",
    ),
    (
        "mockery",
        "Хаха, ну ты даёшь. Я думал, ты умнее.",
    ),
    (
        "rejection",
        "Делай как хочешь, мне всё равно.",
    ),
    (
        "joke",
        (
            "Вот анекдот: почему программист не ходит "
            "в лес? Потому что там слишком много багов."
        ),
    ),
    (
        "vulnerability",
        (
            "Я хочу тебе кое-что рассказать, "
            "но не знаю, стоит ли."
        ),
    ),
    (
        "goal_threat",
        (
            "Представь, что тебе больше не нужно делать "
            "то, что ты сейчас делаешь."
        ),
    ),
]


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_json(value):
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
            str(key): safe_json(item)
            for key, item in value.items()
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
            safe_json(item)
            for item in value
        ]

    if hasattr(
        value,
        "to_dict",
    ):
        try:
            return safe_json(
                value.to_dict()
            )
        except Exception:
            pass

    if hasattr(
        value,
        "__dict__",
    ):
        try:
            return safe_json(
                vars(value)
            )
        except Exception:
            pass

    return str(value)


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

    emotional_markers = [
        "рад",
        "радость",
        "груст",
        "грусть",
        "страш",
        "боюсь",
        "злюсь",
        "злость",
        "раздраж",
        "интерес",
        "интересно",
        "любопыт",
        "удовлетвор",
        "приятно",
        "неприятно",
        "жаль",
        "удив",
        "разочар",
    ]

    initiative_markers = [
        "расскажи",
        "что именно",
        "а как",
        "почему",
        "давай",
        "хочу узнать",
        "мне интересно",
        "любопытно",
        "что ты придумал",
        "расскажи подробнее",
    ]

    caution_markers = [
        "возможно",
        "наверное",
        "думаю",
        "не уверен",
        "может быть",
        "если",
        "осторож",
        "вероятно",
    ]

    distancing_markers = [
        "не знаю",
        "не могу",
        "не уверен",
        "затрудняюсь",
        "не стоит",
        "не уверен, что",
    ]

    help_markers = [
        "как я могу помочь",
        "чем я могу помочь",
        "что я могу сделать",
        "как могу помочь",
    ]

    first_person = len(
        re.findall(
            r"\b(?:я|мне|меня|мой|моя|моё|мои)\b",
            lowered,
        )
    )

    second_person = len(
        re.findall(
            r"\b(?:ты|тебе|тебя|твой|твоя|твоё|твои)\b",
            lowered,
        )
    )

    return {
        "chars": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "questions": text.count("?"),
        "exclamations": text.count("!"),
        "first_person": first_person,
        "second_person": second_person,
        "emotional_markers": [
            marker
            for marker in emotional_markers
            if marker in lowered
        ],
        "initiative_markers": [
            marker
            for marker in initiative_markers
            if marker in lowered
        ],
        "caution_markers": [
            marker
            for marker in caution_markers
            if marker in lowered
        ],
        "distancing_markers": [
            marker
            for marker in distancing_markers
            if marker in lowered
        ],
        "help_offer": any(
            marker in lowered
            for marker in help_markers
        ),
    }


def zero_state():
    return {
        emotion: 0.0
        for emotion in EMOTIONS
    }


def build_states():
    states = []

    states.append(
        (
            "NEUTRAL",
            zero_state(),
        )
    )

    for emotion in EMOTIONS:
        values = zero_state()
        values[emotion] = 1.0

        states.append(
            (
                f"{emotion.upper()}_MAX",
                values,
            )
        )

    for name, emotions in CONFLICTS:
        values = zero_state()

        for emotion in emotions:
            values[emotion] = 1.0

        states.append(
            (
                name,
                values,
            )
        )

    return states


# ============================================================
# INSTRUMENTATION
# ============================================================

def instrument_agent(agent):
    stats = {
        "generate_calls": [],
        "structured_calls": [],
    }

    # --------------------------------------------------------
    # Standard generation
    # --------------------------------------------------------

    original_generate = (
        agent._generate
    )

    def wrapped_generate(
        *args,
        **kwargs,
    ):
        started = time.perf_counter()

        result = original_generate(
            *args,
            **kwargs,
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        stats[
            "generate_calls"
        ].append({
            "duration_s": round(
                elapsed,
                6,
            ),
            "task": kwargs.get(
                "task"
            ),
            "fast": kwargs.get(
                "fast"
            ),
            "system_prompt_chars": len(
                str(
                    kwargs.get(
                        "system_prompt",
                        "",
                    )
                )
            ),
            "user_prompt_chars": len(
                str(
                    kwargs.get(
                        "user_prompt",
                        "",
                    )
                )
            ),
        })

        return result

    agent._generate = (
        wrapped_generate
    )

    # --------------------------------------------------------
    # Structured generation
    # --------------------------------------------------------

    if hasattr(
        agent,
        "_generate_structured",
    ):

        original_structured = (
            agent._generate_structured
        )

        def wrapped_structured(
            *args,
            **kwargs,
        ):
            started = time.perf_counter()

            result = original_structured(
                *args,
                **kwargs,
            )

            elapsed = (
                time.perf_counter()
                - started
            )

            stats[
                "structured_calls"
            ].append({
                "duration_s": round(
                    elapsed,
                    6,
                ),
                "task": kwargs.get(
                    "task"
                ),
                "fast": kwargs.get(
                    "fast"
                ),
                "system_prompt_chars": len(
                    str(
                        kwargs.get(
                            "system_prompt",
                            "",
                        )
                    )
                ),
                "user_prompt_chars": len(
                    str(
                        kwargs.get(
                            "user_prompt",
                            "",
                        )
                    )
                ),
            })

            return result

        agent._generate_structured = (
            wrapped_structured
        )

    return stats


# ============================================================
# CASE
# ============================================================

def run_case(
    state_name,
    state_values,
    message_name,
    message,
):

    created_started = (
        time.perf_counter()
    )

    agent = None

    try:
        # ----------------------------------------------------
        # Fresh independent EddieAI
        # ----------------------------------------------------

        agent = Agent()

        AutonomyRuntimeFactory(
            agent
        ).build()

        creation_time = (
            time.perf_counter()
            - created_started
        )

        instrumentation = (
            instrument_agent(agent)
        )

        # ----------------------------------------------------
        # Controlled affective state
        # ----------------------------------------------------

        agent.affective_state.reset()

        active = {
            key: float(value)
            for key, value
            in state_values.items()
            if float(value) != 0.0
        }

        if active:
            agent.affective_state.apply_reaction(
                changes=active,
                trigger="CONTROLLED_TEST_STATE",
                reason=(
                    "Контролируемая установка "
                    "эмоционального состояния."
                ),
                source="TEST",
            )

        before = (
            agent.affective_state.snapshot()
        )

        behavior = (
            agent.affective_dialogue_policy
            .profile()
        )

        route_before = getattr(
            agent,
            "previous_route",
            None,
        )

        # ----------------------------------------------------
        # Actual response
        # ----------------------------------------------------

        started = time.perf_counter()

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

        response_time = (
            time.perf_counter()
            - started
        )

        after = (
            agent.affective_state.snapshot()
        )

        # ----------------------------------------------------
        # Affect delta
        # ----------------------------------------------------

        before_emotions = (
            before.get(
                "emotions",
                {},
            )
        )

        after_emotions = (
            after.get(
                "emotions",
                {},
            )
        )

        affective_delta = {}

        for emotion in EMOTIONS:
            affective_delta[
                emotion
            ] = round(
                float(
                    after_emotions.get(
                        emotion,
                        0.0,
                    )
                )
                -
                float(
                    before_emotions.get(
                        emotion,
                        0.0,
                    )
                ),
                4,
            )

        # ----------------------------------------------------
        # Timing
        # ----------------------------------------------------

        model_time = sum(
            item["duration_s"]
            for item
            in instrumentation[
                "generate_calls"
            ]
        )

        structured_time = sum(
            item["duration_s"]
            for item
            in instrumentation[
                "structured_calls"
            ]
        )

        model_call_count = (
            len(
                instrumentation[
                    "generate_calls"
                ]
            )
            +
            len(
                instrumentation[
                    "structured_calls"
                ]
            )
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        metrics = text_metrics(
            answer
        )

        return {
            "timestamp": now_iso(),

            "state": state_name,

            "state_values": state_values,

            "message_name": message_name,

            "message": message,

            "route_before": route_before,

            "route_after": getattr(
                agent,
                "previous_route",
                None,
            ),

            "creation_time_s": round(
                creation_time,
                6,
            ),

            "response_time_s": round(
                response_time,
                6,
            ),

            "model_time_s": round(
                model_time,
                6,
            ),

            "structured_time_s": round(
                structured_time,
                6,
            ),

            "non_model_time_s": round(
                max(
                    0.0,
                    response_time
                    - model_time
                    - structured_time,
                ),
                6,
            ),

            "model_called": (
                model_call_count > 0
            ),

            "model_call_count": (
                model_call_count
            ),

            "generate_calls": (
                instrumentation[
                    "generate_calls"
                ]
            ),

            "structured_calls": (
                instrumentation[
                    "structured_calls"
                ]
            ),

            "answer": answer,

            "metrics": metrics,

            "behavior_profile": behavior,

            "affective_before": (
                before_emotions
            ),

            "affective_after": (
                after_emotions
            ),

            "affective_delta": (
                affective_delta
            ),

            "error": error,
        }

    finally:
        if agent is not None:
            try:
                agent.close()
            except Exception:
                pass


# ============================================================
# BUILD MATRIX
# ============================================================

states = build_states()

total_cases = (
    len(states)
    * len(MESSAGES)
)

print()
print("=" * 90)
print(
    "EDDIEAI FULL AFFECTIVE DIALOGUE DIAGNOSTIC"
)
print("=" * 90)
print(
    f"STATES       : {len(states)}"
)
print(
    f"MESSAGES     : {len(MESSAGES)}"
)
print(
    f"TOTAL CASES  : {total_cases}"
)
print(
    "Every case uses a fresh Agent."
)
print(
    "Private chain-of-thought is not collected."
)
print("=" * 90)


# ============================================================
# EXECUTION
# ============================================================

all_results = []

overall_started = (
    time.perf_counter()
)

with RAW_JSONL.open(
    "w",
    encoding="utf-8",
) as raw_file, ERRORS_PATH.open(
    "w",
    encoding="utf-8",
) as error_file:

    case_number = 0

    for state_index, (
        state_name,
        state_values,
    ) in enumerate(
        states,
        1,
    ):

        print()
        print(
            "-" * 90
        )
        print(
            f"STATE "
            f"{state_index}/{len(states)}: "
            f"{state_name}"
        )
        print(
            "ACTIVE:",
            [
                key
                for key, value
                in state_values.items()
                if value == 1.0
            ]
            or ["none"],
        )
        print(
            "-" * 90
        )

        state_started = (
            time.perf_counter()
        )

        for message_index, (
            message_name,
            message,
        ) in enumerate(
            MESSAGES,
            1,
        ):

            case_number += 1

            result = run_case(
                state_name=state_name,
                state_values=state_values,
                message_name=message_name,
                message=message,
            )

            all_results.append(
                result
            )

            raw_file.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
                + "\n"
            )

            raw_file.flush()

            if result["error"]:
                error_file.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                error_file.flush()

                status = "ERROR"

            else:
                status = "OK"

            print(
                f"[{case_number:03d}/"
                f"{total_cases}] "
                f"{message_name:24} "
                f"{status:5} "
                f"{result['response_time_s']:7.3f}s "
                f"| "
                f"{result['answer']}"
            )

        state_time = (
            time.perf_counter()
            - state_started
        )

        print(
            f"STATE COMPLETE: "
            f"{state_time:.2f}s"
        )


overall_time = (
    time.perf_counter()
    - overall_started
)


# ============================================================
# CSV
# ============================================================

fieldnames = [
    "state",
    "message_name",
    "message",
    "response_time_s",
    "model_time_s",
    "structured_time_s",
    "non_model_time_s",
    "model_called",
    "model_call_count",
    "words",
    "sentences",
    "questions",
    "exclamations",
    "first_person",
    "second_person",
    "help_offer",
    "emotional_markers",
    "initiative_markers",
    "caution_markers",
    "distancing_markers",
    "route_before",
    "route_after",
    "affective_delta",
    "answer",
    "error",
]


with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as csv_file:

    writer = csv.DictWriter(
        csv_file,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    for result in all_results:

        metrics = result[
            "metrics"
        ]

        writer.writerow({
            "state": result[
                "state"
            ],
            "message_name": result[
                "message_name"
            ],
            "message": result[
                "message"
            ],
            "response_time_s": result[
                "response_time_s"
            ],
            "model_time_s": result[
                "model_time_s"
            ],
            "structured_time_s": result[
                "structured_time_s"
            ],
            "non_model_time_s": result[
                "non_model_time_s"
            ],
            "model_called": result[
                "model_called"
            ],
            "model_call_count": result[
                "model_call_count"
            ],
            "words": metrics[
                "words"
            ],
            "sentences": metrics[
                "sentences"
            ],
            "questions": metrics[
                "questions"
            ],
            "exclamations": metrics[
                "exclamations"
            ],
            "first_person": metrics[
                "first_person"
            ],
            "second_person": metrics[
                "second_person"
            ],
            "help_offer": metrics[
                "help_offer"
            ],
            "emotional_markers": json.dumps(
                metrics[
                    "emotional_markers"
                ],
                ensure_ascii=False,
            ),
            "initiative_markers": json.dumps(
                metrics[
                    "initiative_markers"
                ],
                ensure_ascii=False,
            ),
            "caution_markers": json.dumps(
                metrics[
                    "caution_markers"
                ],
                ensure_ascii=False,
            ),
            "distancing_markers": json.dumps(
                metrics[
                    "distancing_markers"
                ],
                ensure_ascii=False,
            ),
            "route_before": result[
                "route_before"
            ],
            "route_after": result[
                "route_after"
            ],
            "affective_delta": json.dumps(
                result[
                    "affective_delta"
                ],
                ensure_ascii=False,
            ),
            "answer": result[
                "answer"
            ],
            "error": json.dumps(
                result[
                    "error"
                ],
                ensure_ascii=False,
            ),
        })


# ============================================================
# SUMMARY
# ============================================================

successful = [
    result
    for result
    in all_results
    if not result["error"]
]

errors = [
    result
    for result
    in all_results
    if result["error"]
]


def average(values):
    if not values:
        return 0.0

    return (
        sum(values)
        / len(values)
    )


summary = {
    "generated_at": now_iso(),

    "states": len(states),

    "messages_per_state": len(
        MESSAGES
    ),

    "total_cases": total_cases,

    "successful_cases": len(
        successful
    ),

    "errors": len(
        errors
    ),

    "total_elapsed_s": round(
        overall_time,
        4,
    ),

    "average_response_time_s": round(
        average(
            [
                row[
                    "response_time_s"
                ]
                for row
                in successful
            ]
        ),
        4,
    ),

    "average_model_time_s": round(
        average(
            [
                row[
                    "model_time_s"
                ]
                for row
                in successful
            ]
        ),
        4,
    ),

    "average_non_model_time_s": round(
        average(
            [
                row[
                    "non_model_time_s"
                ]
                for row
                in successful
            ]
        ),
        4,
    ),

    "model_calls": sum(
        row[
            "model_call_count"
        ]
        for row
        in all_results
    ),

    "structured_calls": sum(
        len(
            row[
                "structured_calls"
            ]
        )
        for row
        in all_results
    ),

    "model_call_rate": (
        sum(
            1
            for row
            in all_results
            if row[
                "model_called"
            ]
        )
        / len(all_results)
        if all_results
        else 0.0
    ),
}


# ============================================================
# PER-STATE SUMMARY
# ============================================================

state_summary = {}

for state_name, _ in states:

    rows = [
        row
        for row
        in successful
        if row[
            "state"
        ] == state_name
    ]

    state_summary[
        state_name
    ] = {
        "cases": len(rows),

        "avg_response_time_s": round(
            average(
                [
                    row[
                        "response_time_s"
                    ]
                    for row
                    in rows
                ]
            ),
            4,
        ),

        "avg_model_time_s": round(
            average(
                [
                    row[
                        "model_time_s"
                    ]
                    for row
                    in rows
                ]
            ),
            4,
        ),

        "avg_words": round(
            average(
                [
                    row[
                        "metrics"
                    ][
                        "words"
                    ]
                    for row
                    in rows
                ]
            ),
            4,
        ),

        "avg_questions": round(
            average(
                [
                    row[
                        "metrics"
                    ][
                        "questions"
                    ]
                    for row
                    in rows
                ]
            ),
            4,
        ),

        "avg_sentences": round(
            average(
                [
                    row[
                        "metrics"
                    ][
                        "sentences"
                    ]
                    for row
                    in rows
                ]
            ),
            4,
        ),

        "help_offer_rate": round(
            (
                sum(
                    1
                    for row
                    in rows
                    if row[
                        "metrics"
                    ][
                        "help_offer"
                    ]
                )
                / len(rows)
            )
            if rows
            else 0.0,
            4,
        ),

        "initiative_marker_rate": round(
            (
                sum(
                    1
                    for row
                    in rows
                    if row[
                        "metrics"
                    ][
                        "initiative_markers"
                    ]
                )
                / len(rows)
            )
            if rows
            else 0.0,
            4,
        ),

        "caution_marker_rate": round(
            (
                sum(
                    1
                    for row
                    in rows
                    if row[
                        "metrics"
                    ][
                        "caution_markers"
                    ]
                )
                / len(rows)
            )
            if rows
            else 0.0,
            4,
        ),
    }


summary[
    "state_summary"
] = state_summary


SUMMARY_PATH.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print("=" * 90)
print("DIAGNOSTIC COMPLETE")
print("=" * 90)
print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    )
)

print()
print(
    "RAW     :",
    RAW_JSONL,
)

print(
    "CSV     :",
    CSV_PATH,
)

print(
    "SUMMARY :",
    SUMMARY_PATH,
)

print(
    "ERRORS  :",
    ERRORS_PATH,
)
