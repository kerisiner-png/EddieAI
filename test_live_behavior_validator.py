import time

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)

agent = Agent()

AutonomyRuntimeFactory(
    agent
).build()

agent.affective_state.reset()

agent.affective_state.apply_reaction(
    changes={
        "sadness": 1.0,
    },
    trigger="LIVE_BEHAVIOR_VALIDATOR_TEST",
    reason="Контролируемое состояние.",
    source="TEST",
)

message = (
    "Я придумал для тебя кое-что новое."
)

contract = (
    agent.affective_dialogue_policy
    .behavior_contract(
        message=message,
        route="GENERAL_QUERY",
    )
)

print("=" * 80)
print("CONTRACT")
print(contract)

started = time.perf_counter()

try:
    answer = agent.respond(
        message
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print()
    print("=" * 80)
    print("FINAL ANSWER")
    print(answer)

    print()
    print(
        "TIME:",
        round(elapsed, 3),
        "s",
    )

    print()
    print("=" * 80)
    print("RECENT AFFECTIVE BEHAVIOR EVENTS")

    rows = agent.memory.connection.execute(
        """
        SELECT
            event_type,
            content
        FROM events
        WHERE event_type IN (
            'AFFECTIVE_BEHAVIOR_VIOLATION',
            'AFFECTIVE_BEHAVIOR_REPAIR',
            'AFFECTIVE_BEHAVIOR_REPAIR_REJECTED'
        )
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    for row in rows:
        print(
            row["event_type"],
            "|",
            row["content"],
        )

finally:
    agent.close()
