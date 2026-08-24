from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)

agent = Agent()

runtime = AutonomyRuntimeFactory(
    agent
).build()

agent.self_state.set(
    "goals_state",
    {},
)

agent.self_state.set(
    "goal_plans",
    {},
)

goal = agent.goal_manager.add_candidate(
    value="изучать гравитационные волны",
    motivation=0.95,
    priority=1.0,
    confidence=0.9,
)

agent.goal_manager.activate(
    goal.value
)

print("=" * 70)
print("TICK 1 — PLAN")

runtime.scheduler.reset()

result_1 = runtime.orchestrator.tick()

print("RESULT:")
print(result_1)

print()
print("STATE AFTER TICK 1:")
print(agent.autonomy_execution_state)

print()
print("=" * 70)
print("TICK 2 — EXECUTION")

runtime.scheduler.reset()

result_2 = runtime.orchestrator.tick()

print("RESULT:")
print(result_2)

print()
print("STATE AFTER TICK 2:")
print(agent.autonomy_execution_state)

agent.close()
