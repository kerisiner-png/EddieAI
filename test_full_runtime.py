from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)


agent = Agent()

runtime = (
    AutonomyRuntimeFactory(
        agent
    ).build()
)

print("=== RUNTIME ===")
print(
    runtime.snapshot()
)

print()
print("=== COMPONENTS ===")
print(
    type(runtime.goal_manager).__name__
)

print(
    type(runtime.goal_planner).__name__
)

print(
    type(runtime.motivation).__name__
)

print(
    type(runtime.orchestrator).__name__
)

print(
    type(runtime.tool_runner).__name__
)

print()
print("=== TICK ===")

result = runtime.tick()

print(result)

print()
print("=== FINAL STATE ===")
print(
    runtime.snapshot()
)

agent.close()
