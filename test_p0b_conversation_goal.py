import json
from core.agent import Agent
from identity.identity_manager import IdentityManager
from memory.database import Memory

# Создаём агента
agent = Agent()

# Имитация диалога: агент говорит "Я решаю изучить Python"
message = "Я решаю изучить Python"

# Хук P4 должен сработать в respond
print("Input message:", message)
response = agent.respond(message)
print("Response:", response)

# Проверяем pending_proposals
pending = agent.memory.pending_proposals()
print("Pending proposals:", json.dumps([dict(p) for p in pending], ensure_ascii=False, indent=2))

# Проверяем self_state.goals
goals = agent.self_state.get("goals", [])
print("\nSelf_state goals:", json.dumps(goals, ensure_ascii=False, indent=2))

# Проверяем, что proposal принят
if goals and any("изучить Python" in g for g in goals):
    print("\n✅ P0-b FIXED: Цель из диалога принята!")
else:
    print("\n❌ P0-b FAILED: Цель не принята")
