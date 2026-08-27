from core.eddie_server import EddieServer
from core.decision_core import (
    DecisionCore,
    VALID_KINDS,
)
from core.autonomy_orchestrator import (
    AutonomyOrchestrator,
    OrchestrationResult,
)
from communication.call_engine import (
    CallDirector,
    EDDIEAI_SPEAKING,
    IN_CALL,
    IDLE,
)


class FakeHistory:
    def __init__(self):
        self.next_id = 1

    def chat_add(self, sender, text):
        msg_id = self.next_id
        self.next_id += 1
        return msg_id


class FakeAgent:
    def __init__(self):
        self.memory = None


class _Stub:
    def __init__(self):
        for name in (
            "active",
            "planner",
            "best_candidate",
            "get",
            "add_candidate",
            "activate",
            "sync_progress",
            "all",
        ):
            setattr(self, name, lambda *a, **k: None)


# 1. decision_core принимает CALL
assert "CALL" in VALID_KINDS

# parse_action узнаёт CALL
core = object.__new__(DecisionCore)
action = core._parse_action(
    '{"kind":"CALL","payload":{"text":"Эй!"}}'
)
assert action is not None and action.kind == "CALL"
assert action.payload == {"text": "Эй!"}

# 2. server.initiate_call стартует звонок через call_director
server = EddieServer(FakeAgent(), history_store=FakeHistory())
director = CallDirector()
server.call_director = director

server.initiate_call("Привет, это я!")
assert director.state() != IDLE, "звонок не стартовал"
assert server.pending_initiative is not None
assert "Привет" in server.pending_initiative["text"]

# 3. Cooldown: повторный авто-звонок не перезапускает звонок,
#    а только шлёт инициативу (уже в звонке / таймаут)
server2 = EddieServer(FakeAgent(), history_store=FakeHistory())
director2 = CallDirector()
server2.call_director = director2
server2.initiate_call("Раз")
server2.initiate_call("Два")
assert director2.state() == EDDIEAI_SPEAKING or \
    director2.state() == IN_CALL
assert server2.pending_initiative is not None

# 4. orchestrator маршрутизирует CALL -> server.initiate_call
stub = _Stub()
orchestrator = AutonomyOrchestrator(
    goal_manager=stub,
    goal_generator=stub,
    goal_plan_generator=stub,
    agent_loop=stub,
    server=server2,
)
result = orchestrator._apply_action(
    action,
    {},
)
assert isinstance(result, OrchestrationResult)
assert result.status == "CALLED", result.status
assert server2.pending_initiative is not None

print("ALL PASS")