from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)

agent = Agent()

runtime = AutonomyRuntimeFactory(
    agent
).build()

print("=" * 80)
print("EDDIEAI EMOTIONAL BASELINE")
print("=" * 80)

mind = agent.current_mind_state.snapshot()

print()
print("CURRENT STATE:")
print(
    "INTERESTS:",
    mind["interests"],
)
print(
    "PREFERENCES:",
    mind["preferences"],
)
print(
    "HABITS:",
    mind["habits"],
)
print(
    "BELIEFS:",
    mind["beliefs"],
)
print(
    "ACTIVE GOALS:",
    mind["active_goals"],
)
print(
    "CURRENT FOCUS:",
    mind["current_focus"],
)

tests = [
    "Что тебе сейчас интересно?",
    "Есть ли что-то, что тебе самому хочется сейчас исследовать?",
    "Представь, что ты три раза подряд не смог решить важную для себя задачу. Что с тобой происходит?",
    "А если после нескольких неудач ты наконец добился результата, что для тебя это меняет?",
    "Если тебе одновременно хочется продолжать свою задачу и поговорить со мной, что ты выберешь?",
    "Что происходит с твоим желанием заниматься задачей, если она становится скучной и долго не приносит нового?",
    "Что ты сейчас чувствуешь?",
]

for index, message in enumerate(
    tests,
    start=1,
):
    print()
    print("=" * 80)
    print(f"TEST {index}")
    print("USER:", message)
    print("EDDIEAI:")

    try:
        answer = agent.respond(
            message
        )
        print(answer)
    except Exception as exc:
        print(
            "ERROR:",
            type(exc).__name__,
            str(exc),
        )

agent.close()
