from time import perf_counter

from core.agent import Agent
from core.autonomy_runtime_factory import AutonomyRuntimeFactory


agent = Agent()
AutonomyRuntimeFactory(agent).build()

generation_calls = 0
original_generate = agent._generate


def tracked_generate(*args, **kwargs):
    global generation_calls
    generation_calls += 1
    return original_generate(*args, **kwargs)


agent._generate = tracked_generate

try:
    agent.respond(
        "а ты хочешь мне помочь?"
    )

    agent.respond(
        "тогда почему ты спросил про помощь?"
    )

    agent.respond(
        "почему ты так ответил?"
    )

    before = generation_calls

    start = perf_counter()

    answer = agent.respond(
        "почему?"
    )

    elapsed = perf_counter() - start

    print("=" * 80)
    print("ANSWER:")
    print(answer)

    print()
    print("TIME:", round(elapsed, 3), "sec")
    print(
        "NEW LLM CALLS:",
        generation_calls - before,
    )

finally:
    agent.close()
