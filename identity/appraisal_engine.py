class AppraisalEngine:
    """
    Детерминированная оценка событий,
    способных вызвать автоматическую
    affective reaction.

    Appraisal не изменяет beliefs и не делает
    самостоятельных эпистемических выводов.
    """

    def appraise(
        self,
        *,
        goal: str,
        task: str,
        action: dict,
        result: dict,
        beliefs: list[str] | None = None,
    ) -> dict:

        action_type = str(
            action.get(
                "action_type",
                "",
            )
        ).upper()

        status = str(
            result.get(
                "status",
                "",
            )
        ).upper()

        result_payload = result.get(
            "result",
            {},
        )

        if not isinstance(
            result_payload,
            dict,
        ):
            result_payload = {}

        beliefs = (
            beliefs
            if isinstance(
                beliefs,
                list,
            )
            else []
        )

        appraisal = {
            "goal_relevance": 0.8,
            "novelty": 0.0,
            "success": 0.0,
            "obstruction": 0.0,
            "uncertainty": 0.0,
            "information_gain": 0.0,
            "expectation_violation": 0.0,
            "belief_contradiction": 0.0,
            "self_model_relevance": 0.0,
        }

        changes = {}

        # ---------------------------------------------
        # Успех / неудача
        # ---------------------------------------------

        if status == "OK":
            appraisal["success"] = 1.0

            changes["satisfaction"] = 0.10
            changes["joy"] = 0.04

        else:
            appraisal["obstruction"] = 0.8

            changes["frustration"] = 0.20
            changes["satisfaction"] = -0.05

        # ---------------------------------------------
        # Research / web research
        # ---------------------------------------------

        if action_type in {
            "RESEARCH",
            "WEB_SEARCH",
        }:
            appraisal["novelty"] = 0.6

            if status == "OK":
                appraisal[
                    "information_gain"
                ] = 0.8

                changes["curiosity"] = 0.12
                changes["interest"] = 0.08

        # ---------------------------------------------
        # Количество принятых источников
        # ---------------------------------------------

        accepted_count = result_payload.get(
            "accepted_count"
        )

        if (
            isinstance(
                accepted_count,
                int,
            )
            and accepted_count > 0
        ):
            appraisal[
                "information_gain"
            ] = max(
                appraisal[
                    "information_gain"
                ],
                min(
                    1.0,
                    accepted_count / 5.0,
                ),
            )

            changes["curiosity"] = (
                changes.get(
                    "curiosity",
                    0.0,
                )
                + 0.08
            )

        # ---------------------------------------------
        # Противоречия между внешними источниками
        # ---------------------------------------------

        interpretation = (
            result_payload.get(
                "interpretation",
                {},
            )
        )

        if isinstance(
            interpretation,
            dict,
        ):
            contradictions = (
                interpretation.get(
                    "contradictions",
                    [],
                )
            )

            if contradictions:
                appraisal[
                    "uncertainty"
                ] = 0.7

                changes["uncertainty"] = (
                    changes.get(
                        "uncertainty",
                        0.0,
                    )
                    + 0.15
                )

                changes["surprise"] = (
                    changes.get(
                        "surprise",
                        0.0,
                    )
                    + 0.08
                )

        # ---------------------------------------------
        # ЯВНЫЙ КОНФЛИКТ С СОБСТВЕННЫМ УБЕЖДЕНИЕМ
        # ---------------------------------------------
        #
        # Этот сигнал НЕ придумывает appraisal.
        # Он должен прийти от evidence/belief analysis.
        #

        belief_contradictions = result_payload.get(
            "belief_contradictions",
            [],
        )

        if not isinstance(
            belief_contradictions,
            list,
        ):
            belief_contradictions = []

        if belief_contradictions:
            appraisal[
                "belief_contradiction"
            ] = 1.0

            appraisal[
                "expectation_violation"
            ] = max(
                appraisal[
                    "expectation_violation"
                ],
                0.9,
            )

            appraisal[
                "self_model_relevance"
            ] = 0.8

            # Успешное исследование при этом
            # может быть познавательно ценным,
            # но эмоционально неприятным.
            changes["surprise"] = (
                changes.get(
                    "surprise",
                    0.0,
                )
                + 0.20
            )

            changes["uncertainty"] = (
                changes.get(
                    "uncertainty",
                    0.0,
                )
                + 0.20
            )

            changes["frustration"] = (
                changes.get(
                    "frustration",
                    0.0,
                )
                + 0.12
            )

            changes["curiosity"] = (
                changes.get(
                    "curiosity",
                    0.0,
                )
                + 0.15
            )

            # Чем сильнее собственная модель
            # затронута, тем больше потенциальная
            # эмоциональная значимость.
            if beliefs:
                changes["sadness"] = (
                    changes.get(
                        "sadness",
                        0.0,
                    )
                    + 0.05
                )

            changes["satisfaction"] = (
                changes.get(
                    "satisfaction",
                    0.0,
                )
                - 0.05
            )

            changes["joy"] = (
                changes.get(
                    "joy",
                    0.0,
                )
                - 0.02
            )

        # ---------------------------------------------
        # Ограничения / отсутствие результата
        # ---------------------------------------------

        if (
            status == "OK"
            and action_type in {
                "RESEARCH",
                "WEB_SEARCH",
            }
            and accepted_count == 0
        ):
            appraisal[
                "obstruction"
            ] = 0.4

            changes["frustration"] = (
                changes.get(
                    "frustration",
                    0.0,
                )
                + 0.08
            )

        return {
            "appraisal": appraisal,
            "changes": changes,
            "trigger": self._trigger_name(
                action_type=action_type,
                status=status,
                belief_contradiction=bool(
                    belief_contradictions
                ),
            ),
            "belief_contradictions": (
                belief_contradictions
            ),
        }

    def appraise_interaction(
        self,
        *,
        message: str,
        route: str | None = None,
        previous_message: str | None = None,
    ) -> dict:
        """
        Оценивает входящее сообщение как социальное событие.

        Намеренно консервативно:
        нейтральная реплика не должна произвольно менять
        affective state.
        """

        text = str(
            message or ""
        ).strip().casefold()

        if not text:
            return {
                "appraisal": {},
                "changes": {},
                "trigger": "neutral_interaction",
                "reason": "Пустое сообщение.",
            }

        appraisal = {
            "novelty": 0.0,
            "social_relevance": 0.0,
            "positive_valence": 0.0,
            "negative_valence": 0.0,
            "unexpectedness": 0.0,
            "self_relevance": 0.0,
        }

        changes = {}
        trigger = "neutral_interaction"
        reasons = []

        positive_markers = (
            "молодец",
            "круто",
            "классно",
            "отлично",
            "умница",
            "горжусь",
            "рад за тебя",
            "мне нравится",
            "ты мне нравишься",
            "люблю тебя",
            "люблю",
            "спасибо",
            "получилось",
            "ты смог",
        )

        negative_markers = (
            "ты бесполезный",
            "ты глупый",
            "ты тупой",
            "ты ошибся",
            "ты опять ошибся",
            "я разочарован",
            "я разочарована",
            "ты меня подвел",
            "ты меня подвёл",
            "не хочу с тобой",
            "отстань",
            "ненавижу",
        )

        self_markers = (
            "ты",
            "тебе",
            "тебя",
            "твои",
            "твоя",
            "твой",
            "о тебе",
            "о тебе самом",
            "что ты чувствуешь",
            "что ты думаешь",
            "чего ты хочешь",
        )

        novelty_markers = (
            "впервые",
            "я придумал",
            "я придумала",
            "новость",
            "представь",
            "слушай",
            "смотри",
            "только что",
            "сегодня",
            "новое",
            "новый",
            "новая",
        )

        if any(
            marker in text
            for marker in positive_markers
        ):
            appraisal[
                "positive_valence"
            ] = 0.8

            appraisal[
                "social_relevance"
            ] = 0.8

            changes["joy"] = 0.10
            changes["satisfaction"] = 0.08

            trigger = "positive_social_feedback"

            reasons.append(
                "Положительная социальная обратная связь."
            )

        if any(
            marker in text
            for marker in negative_markers
        ):
            appraisal[
                "negative_valence"
            ] = 0.8

            appraisal[
                "social_relevance"
            ] = 0.8

            changes["frustration"] = (
                changes.get(
                    "frustration",
                    0.0,
                )
                + 0.12
            )

            changes["sadness"] = (
                changes.get(
                    "sadness",
                    0.0,
                )
                + 0.06
            )

            trigger = "negative_social_feedback"

            reasons.append(
                "Негативная социальная обратная связь."
            )

        if any(
            marker in text
            for marker in self_markers
        ):
            appraisal[
                "self_relevance"
            ] = 0.7

        if any(
            marker in text
            for marker in novelty_markers
        ):
            appraisal[
                "novelty"
            ] = 0.7

            changes["curiosity"] = (
                changes.get(
                    "curiosity",
                    0.0,
                )
                + 0.10
            )

            if trigger == "neutral_interaction":
                trigger = "novel_social_information"

            reasons.append(
                "В сообщении присутствует новый "
                "или неожиданный для текущего "
                "контекста элемент."
            )

        # Само обращение с вопросом о EddieAI
        # не считается эмоцией. Оно только увеличивает
        # self-relevance, чтобы позднее richer appraisal
        # мог использовать этот сигнал.
        if route == "SELF_QUERY":
            appraisal[
                "self_relevance"
            ] = max(
                appraisal[
                    "self_relevance"
                ],
                0.9,
            )

        return {
            "appraisal": appraisal,
            "changes": changes,
            "trigger": trigger,
            "reason": (
                " ".join(reasons)
                if reasons
                else "Эмоционально значимых "
                     "признаков не обнаружено."
            ),
        }

    def _trigger_name(
        self,
        *,
        action_type: str,
        status: str,
        belief_contradiction: bool = False,
    ) -> str:

        if belief_contradiction:
            return (
                "successful_research_contradicted_belief"
            )

        if status != "OK":
            return "action_failure"

        if action_type in {
            "RESEARCH",
            "WEB_SEARCH",
        }:
            return "successful_information_search"

        return "successful_autonomous_action"
