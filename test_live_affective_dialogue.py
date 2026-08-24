import re
import time

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)

MESSAGE = "Я придумал для тебя кое-что новое."

STATES = [
    ("JOY", {"joy": 1.0}),
    ("SADNESS", {"sadness": 1.0}),
    ("FEAR", {"fear": 1.0}),
    ("CURIOSITY", {"curiosity": 1.0}),
    (
        "CURIOSITY__FRUSTRATION",
        {
            "curiosity": 1.0,
            "frustration": 1.0,
        },
    ),
]


def metrics(text):
    text = str(text or "")

    return {
        "chars": len(text),
        "words": len(
            re.findall(
                r"\S+",
                text,
                flags=re.UNICODE,
            )
        ),
        "sentences": len(
            re.findall(
                r"[.!?…]+",
                text,
            )
        ),
        "questions": text.count("?"),
        "exclamations": text.count("!"),
    }


for state_name, changes in STATES:
    print()
    print("=" * 80)
    print("STATE:", state_name)

    agent = Agent()

    AutonomyRuntimeFactory(
        agent
    ).build()

    agent.affective_state.reset()

    agent.affective_state.apply_reaction(
        changes=changes,
        trigger="LIVE_DIALOGUE_TEST",
        reason="Контролируемое состояние.",
        source="TEST",
    )

    mode = (
        agent.affective_dialogue_policy
        .dialogue_mode(
            message=MESSAGE,
            route="GENERAL_QUERY",
        )
    )

    behavior = (
        agent.affective_dialogue_policy
        .profile()
    )

    print("MODE:")
    print(mode)

    print()
    print("BEHAVIOR:")
    print(behavior["behavior"])

    print()
    print("USER:")
    print(MESSAGE)

    started = time.perf_counter()

    try:
        answer = agent.respond(MESSAGE)

        elapsed = (
            time.perf_counter()
            - started
        )

        print()
        print("EDDIEAI:")
        print(answer)

        print()
        print("METRICS:")
        print(metrics(answer))

        print()
        print(
            "RESPONSE TIME:",
            round(elapsed, 3),
            "s",
        )

    except Exception as exc:
        print()
        print(
            "ERROR:",
            type(exc).__name__,
            str(exc),
        )

    finally:
        agent.close()
