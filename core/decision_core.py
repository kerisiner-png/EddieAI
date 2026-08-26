import json

from core.situation import encode_situation
from identity.llm_access import CloudFirstLlm


NEEDS_NEW_PATTERN = "__NEEDS_NEW_PATTERN__"


VALID_KINDS = {
    "EXECUTE",
    "GENERATE_PLAN",
    "ACTIVATE_GOAL",
    "COMPLETE_GOAL",
    "ASK",
    "REFLECT",
    "CHECK_INBOX",
    "READ_INBOX",
    "IDLE",
}


MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 200,
    "temperature": 0.3,
}


class Action:
    def __init__(
        self,
        kind,
        payload=None,
    ):
        self.kind = kind
        self.payload = payload

    def to_dict(self):
        return {
            "kind": self.kind,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(data):
        return Action(
            kind=data.get("kind", "IDLE"),
            payload=data.get("payload"),
        )

    def __eq__(self, other):
        if not isinstance(other, Action):
            return NotImplemented

        return (
            self.kind == other.kind
            and self.payload == other.payload
        )

    def __hash__(self):
        return hash(
            (self.kind, repr(self.payload))
        )

    def __repr__(self):
        return (
            f"Action({self.kind}, "
            f"{self.payload!r})"
        )


class DecisionCore:
    def __init__(
        self,
        memory,
        goal_manager,
        model_orchestrator=None,
        task_controller=None,
        agent_loop=None,
        outbox=None,
        server=None,
        evidence=None,
    ):
        self.memory = memory
        self.goal_manager = goal_manager
        self.task_controller = task_controller
        self.agent_loop = agent_loop
        self.outbox = outbox
        self.server = server
        self.evidence = evidence

        self.llm = CloudFirstLlm(
            model_orchestrator
        )

        self.llm_calls = 0

    def key(self, state):
        return encode_situation(state)

    def decide(self, state):
        local = self._local_rules(state)

        if local is not None:
            return local

        key = encode_situation(state)

        pattern = self.memory.pattern_lookup(key)

        if pattern is not None:
            self.memory.pattern_bump(key)

            try:
                data = json.loads(pattern["action"])
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                data = {"kind": "IDLE"}

            return Action.from_dict(data)

        learned = self._learn_from_memory_for(
            state,
            key,
        )

        if learned is not None:
            return learned

        rebuilt = self._rebuild_pattern_from_habit(
            state,
            key,
        )

        if rebuilt is not None:
            return rebuilt

        return NEEDS_NEW_PATTERN

    def learn_from_memory(self):
        key = self._idle_key()

        if self.memory.pattern_lookup(key) is not None:
            return 0

        interest = self._first_interest()

        if not interest:
            return 0

        action = Action(
            "ACTIVATE_GOAL",
            payload={
                "value": f"изучить тему: {interest}",
            },
        )

        self.memory.pattern_record(
            key,
            json.dumps(
                action.to_dict(),
                ensure_ascii=False,
            ),
            confidence=0.5,
        )

        return 1

    def consolidate_habits(
        self,
        min_uses: int = 3,
    ):
        if self.evidence is None:
            return 0

        rows = self.memory.connection.execute("""
            SELECT situation_key, action, times_used
            FROM situation_patterns
            WHERE times_used >= ?
        """, (min_uses,)).fetchall()

        created = 0

        for row in rows:
            action_kind = "IDLE"

            try:
                action_data = json.loads(
                    row["action"]
                )
                action_kind = str(
                    action_data.get(
                        "kind",
                        "IDLE",
                    )
                ).upper()
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                pass

            value = (
                f"situation_action:"
                f"{row['situation_key']}"
                f":::{action_kind}"
            )

            try:
                existing = self.evidence.get(
                    "habit",
                    value,
                )
            except ValueError:
                existing = None

            if existing is not None:
                continue

            self.evidence.add(
                category="habit",
                value=value,
                source="DECISION_PATTERN",
                independence_key=(
                    f"situation:{row['situation_key']}"
                ),
            )

            created += 1

        return created

    def _learn_from_memory_for(
        self,
        state,
        key,
    ):
        if self.memory.pattern_lookup(key) is not None:
            return None

        interest = self._first_interest()

        if not interest:
            return None

        action = Action(
            "ACTIVATE_GOAL",
            payload={
                "value": f"изучить тему: {interest}",
            },
        )

        self.memory.pattern_record(
            key,
            json.dumps(
                action.to_dict(),
                ensure_ascii=False,
            ),
            confidence=0.5,
        )

        return action

    def _rebuild_pattern_from_habit(
        self,
        state,
        key,
    ):
        self_state = getattr(
            self.goal_manager,
            "self_state",
            None,
        )

        if self_state is None:
            return None

        traits = self_state.get(
            "personality_traits",
            {},
        )

        prefix = f"situation_action:{key}:::"

        for data in traits.values():
            if not isinstance(data, dict):
                continue

            if data.get("status") != "ACTIVE":
                continue

            value = str(
                data.get("value", "")
            )

            if not value.startswith(prefix):
                continue

            kind = value[len(prefix):]

            if kind not in VALID_KINDS:
                continue

            action = Action(kind)

            self.memory.pattern_record(
                key,
                json.dumps(
                    action.to_dict(),
                    ensure_ascii=False,
                ),
                confidence=0.5,
            )

            return action

        return None

    def _first_interest(self):
        self_state = getattr(
            self.goal_manager,
            "self_state",
            None,
        )

        if self_state is None:
            return None

        interests = self_state.get(
            "interests",
            [],
        )

        if not interests:
            return None

        value = str(interests[0]).strip()

        return value or None

    def _idle_key(self):
        return encode_situation({
            "goal": None,
            "task_type": None,
            "inbox_unread": 0,
            "affect": None,
            "freshness": 0,
        })

    def learn(
        self,
        key,
        context,
    ):
        self.llm_calls += 1

        prompt = self._learn_prompt(context)

        raw = self.llm.chat(
            system=(
                "Ты — локальный советник автономного "
                "агента EddieAI. Ты решаешь, какое "
                "действие ему сделать в новой ситуации. "
                "Верни только JSON."
            ),
            user=prompt,
            options=MODEL_OPTIONS,
            task="plan",
        )

        action = self._parse_action(raw)

        if action is None:
            action = Action("IDLE")

        self.memory.pattern_record(
            key,
            json.dumps(
                action.to_dict(),
                ensure_ascii=False,
            ),
            confidence=0.6,
        )

        return action

    def _learn_prompt(self, context):
        options = ", ".join(sorted(VALID_KINDS))

        return f"""
Текущая ситуация EddieAI:

{context}

Выбери одно действие из допустимых:

{options}

EXECUTE — выполнить следующий шаг активной цели.
GENERATE_PLAN — создать план для активной цели.
ACTIVATE_GOAL — активировать кандидата цели.
COMPLETE_GOAL — завершить текущую цель.
ASK — спросить Эдди о направлении.
REFLECT — подвести итог накопленного опыта.
CHECK_INBOX — проверить и ответить на почту Эдди.
IDLE — сейчас ничего не делать.

Верни только JSON:

{{
  "kind": "IDLE",
  "payload": null
}}

Для GENERATE_PLAN payload:
{{"goal": "текст цели"}}

Для ACTIVATE_GOAL payload:
{{"value": "текст цели"}}

Для COMPLETE_GOAL payload:
{{"goal": "текст цели"}}

Для остальных payload — null.
Без markdown.
"""

    def _parse_action(self, raw):
        if not raw:
            return None

        text = str(raw).strip()

        start = text.find("{")
        end = text.rfind("}")

        if start < 0 or end < start:
            return None

        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        kind = str(data.get("kind", "IDLE")).upper()

        if kind not in VALID_KINDS:
            return None

        payload = data.get("payload")

        return Action(kind, payload)

    def _top_goal(self, active):
        return max(
            active,
            key=lambda goal: (
                float(goal.priority) * 0.50
                + float(goal.motivation) * 0.30
                + float(goal.confidence) * 0.20
            ),
        )

    def _local_rules(self, state):
        emotions = state.get(
            "emotions",
            {},
        )

        try:
            frustration = float(
                emotions.get("frustration", 0.0)
            )
        except (TypeError, ValueError):
            frustration = 0.0

        active = self.goal_manager.active()

        if active:
            goal = self._top_goal(active)
            value = goal.value

            plan = self.goal_manager.planner.get_plan(
                value
            )

            if plan is None:
                return Action(
                    "GENERATE_PLAN",
                    payload={"goal": value},
                )

            next_task = (
                self.goal_manager.planner.next_task(
                    value
                )
            )

            if next_task is not None:
                return Action(
                    "EXECUTE",
                    payload={
                        "goal": value,
                        "task": getattr(
                            next_task,
                            "title",
                            None,
                        ),
                    },
                )

            return Action(
                "COMPLETE_GOAL",
                payload={"goal": value},
            )

        inbox = state.get("inbox_unread", 0)

        try:
            inbox = int(inbox)
        except (TypeError, ValueError):
            inbox = 0

        if inbox > 0 and frustration < 0.70:
            return Action("READ_INBOX")

        candidate = self.goal_manager.best_candidate()

        if candidate is not None:
            if frustration >= 0.70:
                return Action("IDLE")

            return Action(
                "ACTIVATE_GOAL",
                payload={"value": candidate.value},
            )

        return None
