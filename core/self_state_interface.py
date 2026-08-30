class SelfStateInterface:
    """
    Единый authoritative view текущего состояния EddieAI.

    Этот слой не интерпретирует состояние и не делает
    метафизических выводов. Он только собирает факты,
    которые уже существуют внутри runtime.
    """

    def __init__(self, agent):
        self.agent = agent

    def snapshot(self) -> dict:
        agent = self.agent

        self_state = (
            agent.self_state.snapshot()
            if hasattr(
                agent.self_state,
                "snapshot",
            )
            else {}
        )

        affective_state = {}

        if hasattr(
            agent,
            "affective_state",
        ):
            try:
                affective_state = (
                    agent.affective_state.snapshot()
                )
            except Exception:
                affective_state = {}

        affective_observation = {}

        if hasattr(
            agent,
            "affective_self_observer",
        ):
            try:
                affective_observation = (
                    agent.affective_self_observer
                    .observe(
                        limit=8
                    )
                )
            except Exception:
                affective_observation = {}

        dialogue_mode = {}

        if hasattr(
            agent,
            "affective_dialogue_policy",
        ):
            try:
                dialogue_mode = (
                    agent.affective_dialogue_policy
                    .dialogue_mode(
                        message="",
                        route="SELF_QUERY",
                    )
                )
            except Exception:
                dialogue_mode = {}

        dialogue_behavior = {}

        if hasattr(
            agent,
            "affective_dialogue_policy",
        ):
            try:
                profile = (
                    agent.affective_dialogue_policy
                    .profile()
                )

                dialogue_behavior = (
                    profile.get(
                        "behavior",
                        {},
                    )
                )
            except Exception:
                dialogue_behavior = {}

        active_goals = []

        if hasattr(
            agent,
            "goal_manager",
        ):
            try:
                active_goals = [
                    goal.value
                    for goal
                    in agent.goal_manager.active()
                ]
            except Exception:
                active_goals = []

        return {
            "identity": {
                "name": self_state.get(
                    "name"
                ),
                "age": self_state.get(
                    "age"
                ),
                "values": self_state.get(
                    "values",
                    [],
                ),
            },

            "interests": self_state.get(
                "interests",
                [],
            ),

            "world_description": self_state.get(
                "world_description",
                None,
            ),

            "preferences": self_state.get(
                "preferences",
                [],
            ),

            "habits": self_state.get(
                "habits",
                [],
            ),

            "beliefs": self_state.get(
                "beliefs",
                [],
            ),

            "established_goals": self_state.get(
                "goals",
                [],
            ),

            "active_goals": active_goals,

            "affective_state": (
                affective_state
            ),

            "affective_self_observation": (
                affective_observation
            ),

            "dialogue_mode": (
                dialogue_mode
            ),

            "dialogue_behavior": (
                dialogue_behavior
            ),
        }

    def render(self) -> str:
        import json

        snapshot = self.snapshot()

        return (
            "AUTHORITATIVE EDDIEAI SELF-STATE\n\n"
            + json.dumps(
                snapshot,
                ensure_ascii=False,
                indent=2,
            )
        )
