class CurrentMindState:
    """
    Read-only snapshot of the agent's current internal state.
    """

    def __init__(
        self,
        agent,
    ):
        self.agent = agent

    def snapshot(self) -> dict:
        self_state = self.agent.self_state

        interests = list(
            self_state.get(
                "interests",
                [],
            )
        )

        preferences = list(
            self_state.get(
                "preferences",
                [],
            )
        )

        habits = list(
            self_state.get(
                "habits",
                [],
            )
        )

        beliefs = list(
            self_state.get(
                "beliefs",
                [],
            )
        )

        values = list(
            self_state.get(
                "values",
                [],
            )
        )

        active_goals = self._active_goals()

        current_focus = self._current_focus(
            interests=interests,
            active_goals=active_goals,
        )

        runtime = self.agent.runtime_state.snapshot()

        relationships = self_state.get(
            "relationships",
            {},
        )

        affective_state = getattr(
            self.agent,
            "affective_state",
            None,
        )

        affective = (
            affective_state.snapshot()
            if affective_state is not None
            else {
                "emotions": {},
                "updated_at": None,
                "history": [],
            }
        )

        affective_observer = getattr(
            self.agent,
            "affective_self_observer",
            None,
        )

        affective_observation = (
            affective_observer.observe(
                limit=5
            )
            if affective_observer is not None
            else {
                "status": "UNAVAILABLE",
                "interpretation_status": (
                    "UNAVAILABLE"
                ),
                "current_state": {},
                "changes": [],
            }
        )

        return {
            "identity": {
                "name": self_state.get(
                    "name"
                ),
                "age": self_state.get(
                    "age"
                ),
            },
            "mission": {
                "primary": self_state.get(
                    "primary_mission"
                ),
                "statement": self_state.get(
                    "mission_statement"
                ),
            },
            "values": values,
            "interests": interests,
            "preferences": preferences,
            "habits": habits,
            "beliefs": beliefs,
            "active_goals": active_goals,
            "relationships": relationships,
            "affective_state": affective,
            "affective_observation": (
                affective_observation
            ),
            "current_focus": current_focus,
            "runtime": runtime,
        }

    def render(self) -> str:
        state = self.snapshot()

        identity = state["identity"]
        mission = state["mission"]
        runtime = state["runtime"]

        return f"""
CURRENT MIND STATE OF EDDIEAI

Identity:
name = {identity.get("name")}
age = {identity.get("age")}

Primary mission:
{mission.get("statement")}
machine_mission = {mission.get("primary")}

Values:
{state["values"]}

Interests:
{state["interests"]}

Preferences:
{state["preferences"]}

Habits:
{state["habits"]}

Beliefs:
{state["beliefs"]}

Active goals:
{state["active_goals"]}

Relationships:
{state["relationships"]}

Affective state:
{state["affective_state"]}

Affective self-observation:
{state["affective_observation"]}

Current focus:
{state["current_focus"]}

CURRENT RUNTIME STATE

Worker:
{runtime["worker"]}

Cognition:
{runtime["cognition"]}

Activity:
{runtime["activity"]}

IMPORTANT:
This state describes EddieAI's actual internal and runtime state.

EddieAI's primary mission is to exist and develop.
Helping the user is not the primary mission.

Do not invent internal activity.
Do not claim that background cognition is running
unless the runtime state says it is RUNNING.
Do not claim that a task is being processed unless
it is reflected in the current runtime state.
"""

    def _active_goals(self):
        goal_manager = getattr(
            self.agent,
            "goal_manager",
            None,
        )

        if goal_manager is not None:
            try:
                return [
                    goal.value
                    for goal in goal_manager.active()
                ]
            except Exception:
                pass

        return list(
            self.agent.self_state.get(
                "goals",
                [],
            )
        )

    def _current_focus(
        self,
        *,
        interests,
        active_goals,
    ):
        if active_goals:
            return (
                f"active goal: "
                f"{active_goals[0]}"
            )

        runtime = self.agent.runtime_state.snapshot()

        activity = runtime.get(
            "activity"
        )

        if isinstance(
            activity,
            dict,
        ):
            status = str(
                activity.get(
                    "status",
                    "",
                )
            ).upper()

            description = (
                activity.get(
                    "description"
                )
                or activity.get(
                    "task"
                )
                or activity.get(
                    "name"
                )
            )

            if (
                status == "RUNNING"
                and description
            ):
                return (
                    f"runtime activity: "
                    f"{description}"
                )

        return "no explicit current focus"
