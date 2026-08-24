class AffectiveBehaviorPolicy:
    """
    Преобразует affective state в поведенческие и
    стратегические смещения.

    Policy не выбирает цель и не принимает окончательное
    решение. Она только формирует внутренние biases.
    """

    def __init__(
        self,
        affective_state,
    ):
        self.affective_state = affective_state

    def _emotions(self) -> dict[str, float]:
        state = self.affective_state.snapshot()

        raw = state.get(
            "emotions",
            {},
        )

        if not isinstance(
            raw,
            dict,
        ):
            return {}

        return {
            key: float(value)
            for key, value in raw.items()
        }

    def strategic_state(self) -> dict:
        """
        Возвращает текущее стратегическое состояние.

        Стратегическое состояние является функциональным
        результатом взаимодействия текущих affective signals.
        Оно не является сознательным решением.
        """

        emotions = self._emotions()

        curiosity = emotions.get(
            "curiosity",
            0.0,
        )

        interest = emotions.get(
            "interest",
            0.0,
        )

        frustration = emotions.get(
            "frustration",
            0.0,
        )

        fear = emotions.get(
            "fear",
            0.0,
        )

        satisfaction = emotions.get(
            "satisfaction",
            0.0,
        )

        surprise = emotions.get(
            "surprise",
            0.0,
        )

        explore = max(
            curiosity,
            interest,
        )

        rethink = max(
            frustration,
            surprise,
        )

        cautious = fear

        continue_score = (
            satisfaction * 0.5
            + max(
                0.0,
                1.0 - frustration,
            ) * 0.2
        )

        scores = {
            "CONTINUE": round(
                continue_score,
                4,
            ),
            "EXPLORE": round(
                explore,
                4,
            ),
            "RETHINK": round(
                rethink,
                4,
            ),
            "CAUTIOUS": round(
                cautious,
                4,
            ),
        }

        # -----------------------------------------
        # CONFLICT DETECTION
        # -----------------------------------------
        #
        # Сильные и близкие по величине exploration
        # и rethink signals означают не выбор одного
        # из них, а внутреннее стратегическое напряжение.
        #

        conflict_delta = abs(
            explore - rethink
        )

        conflict_strength = min(
            explore,
            rethink,
        )

        conflicted = (
            conflict_strength >= 0.50
            and conflict_delta <= 0.20
        )

        if conflicted:
            state = "CONFLICTED"

        else:
            state = max(
                scores,
                key=scores.get,
            )

            if max(
                scores.values()
            ) < 0.15:
                state = "CONTINUE"

        return {
            "state": state,
            "scores": scores,
            "emotions": emotions,
            "conflict": {
                "active": conflicted,
                "strength": round(
                    conflict_strength,
                    4,
                ),
                "delta": round(
                    conflict_delta,
                    4,
                ),
                "signals": {
                    "explore": round(
                        explore,
                        4,
                    ),
                    "rethink": round(
                        rethink,
                        4,
                    ),
                },
            },
        }

    def biases(
        self,
        options,
        task=None,
    ) -> dict[str, float]:

        emotions = self._emotions()

        curiosity = emotions.get(
            "curiosity",
            0.0,
        )

        interest = emotions.get(
            "interest",
            0.0,
        )

        frustration = emotions.get(
            "frustration",
            0.0,
        )

        fear = emotions.get(
            "fear",
            0.0,
        )

        satisfaction = emotions.get(
            "satisfaction",
            0.0,
        )

        strategy = (
            self.strategic_state()
        )

        strategic_mode = strategy[
            "state"
        ]

        biases = {}

        for option in options:

            action_type = str(
                option.action_type
            ).upper()

            bias = 0.0

            # -----------------------------------------
            # BASE AFFECTIVE BIAS
            # -----------------------------------------

            if action_type == "RESEARCH":
                bias += (
                    curiosity * 0.20
                    + interest * 0.10
                )

            elif action_type == "WEB_SEARCH":
                bias += (
                    curiosity * 0.10
                    + interest * 0.05
                )

            elif action_type == "THINK":
                bias += (
                    curiosity * 0.05
                )

            if frustration > 0.0:

                if action_type == "RESEARCH":
                    bias -= (
                        frustration * 0.12
                    )

                elif action_type == "WEB_SEARCH":
                    bias -= (
                        frustration * 0.08
                    )

                elif action_type == "THINK":
                    bias += (
                        frustration * 0.08
                    )

            if fear > 0.0:

                if action_type == "THINK":
                    bias += (
                        fear * 0.08
                    )

                elif action_type in {
                    "RUN_COMMAND",
                    "WRITE_FILE",
                }:
                    bias -= (
                        fear * 0.08
                    )

            if satisfaction > 0.0:

                if action_type == "RESEARCH":
                    bias -= (
                        satisfaction * 0.04
                    )

            # -----------------------------------------
            # STRATEGIC BIAS
            # -----------------------------------------

            if strategic_mode == "EXPLORE":

                if action_type == "RESEARCH":
                    bias += 0.10

                elif action_type == "WEB_SEARCH":
                    bias += 0.06

            elif strategic_mode == "RETHINK":

                if action_type == "THINK":
                    bias += 0.12

                elif action_type in {
                    "RESEARCH",
                    "WEB_SEARCH",
                }:
                    bias -= 0.04

            elif strategic_mode == "CONFLICTED":

                # При конфликте не выбираем сторону
                # автоматически. Сначала повышаем
                # привлекательность переосмысления.
                if action_type == "THINK":
                    bias += 0.20

                elif action_type == "RESEARCH":
                    bias -= 0.03

                elif action_type == "WEB_SEARCH":
                    bias -= 0.02

            elif strategic_mode == "CAUTIOUS":

                if action_type == "THINK":
                    bias += 0.10

                elif action_type in {
                    "RUN_COMMAND",
                    "WRITE_FILE",
                }:
                    bias -= 0.10

            elif strategic_mode == "CONTINUE":

                # Никакой дополнительной коррекции.
                pass

            biases[action_type] = round(
                bias,
                4,
            )

        return biases

    def goal_bias(
        self,
        goal,
    ) -> float:
        """
        Affectively biases a goal using EddieAI's
        accumulated emotional experience with that
        exact goal.

        No goal-name keyword heuristics are used.
        """

        memory = getattr(
            self,
            "goal_affective_memory",
            None,
        )

        if memory is None:
            return 0.0

        return memory.bias(
            goal=str(
                getattr(
                    goal,
                    "value",
                    "",
                )
            )
        )
