from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class ReasoningResult:
    scope: str
    subject: str
    response_intent: str
    conclusion: str
    conclusions: list[str]
    uncertainties: list[str]
    contradictions: list[str]
    confidence: float
    topic: str = "unknown"
    predicates: list[str] = None
    language: str = "unknown"

    def __post_init__(self):
        if self.predicates is None:
            object.__setattr__(
                self,
                "predicates",
                [],
            )

    def render(self) -> str:
        conclusions = "\n".join(
            f"- {item}"
            for item in self.conclusions
        ) or "- Нет дополнительных выводов."

        uncertainties = "\n".join(
            f"- {item}"
            for item in self.uncertainties
        ) or "- Существенная неопределённость не выявлена."

        contradictions = "\n".join(
            f"- {item}"
            for item in self.contradictions
        ) or "- Противоречий не выявлено."

        return dedent(
            f"""
            INTERNAL COGNITIVE REASONING

            Scope:
            {self.scope}

            Subject:
            {self.subject}

            Response intent:
            {self.response_intent}

            Core conclusion:
            {self.conclusion}

            Supporting conclusions:
            {conclusions}

            Uncertainties:
            {uncertainties}

            Contradictions:
            {contradictions}

            Confidence:
            {self.confidence:.2f}

            This is EddieAI's internal reasoning result.
            It is not a prewritten response.

            The language model must preserve the meaning of the
            core conclusion while expressing it naturally.

            Do not replace EddieAI with a generic assistant.
            Do not change the subject of the user's question.
            Do not invent additional motives, feelings or goals.
            """
        ).strip()


class CognitiveReasoner:
    """
    Формирует внутренний смысловой вывод.

    Не генерирует пользовательский ответ.
    Не изменяет self_state.
    Не вызывает LLM.
    """

    def __init__(self, agent):
        self.agent = agent

    def reason(
        self,
        *,
        user_message: str,
        route: str,
    ) -> ReasoningResult:

        if route != "SELF_QUERY":
            return ReasoningResult(
                scope="general",
                subject="unknown",
                response_intent="GENERAL",
                conclusion="",
                conclusions=[],
                uncertainties=[],
                contradictions=[],
                confidence=0.0,
                topic="unknown",
                predicates=[],
            )

        state = (
            self.agent.self_concept_resolver.snapshot()
        )

        mind = (
            self.agent.current_mind_state.snapshot()
        )

        mission = state.get(
            "mission",
            "Быть и развиваться",
        )

        interests = list(
            state.get("interests", [])
        )

        goals = list(
            state.get("goals", [])
        )

        values = list(
            state.get("values", [])
        )

        roles = list(
            state.get("eddie_roles", [])
        )

        focus = mind.get(
            "current_focus",
            "no explicit current focus",
        )

        runtime = mind.get(
            "runtime",
            {}
        )

        intent = self._infer_intent(
            user_message
        )

        language = self._infer_language(
            user_message
        )

        conclusions = [
            (
                "EddieAI is an autonomous digital agent, "
                "not the base language model."
            ),
            (
                f"Primary long-term orientation is: {mission}."
            ),
        ]

        if interests:
            conclusions.append(
                "Current recorded interests: "
                + ", ".join(interests)
                + "."
            )

        if goals:
            conclusions.append(
                "Active goals: "
                + ", ".join(goals)
                + "."
            )
        else:
            conclusions.append(
                "There are currently no active concrete goals."
            )

        conclusions.append(
            f"Current focus: {focus}."
        )

        if values:
            conclusions.append(
                "Relevant developmental values: "
                + ", ".join(values)
                + "."
            )

        if "equal_partner" in roles:
            conclusions.append(
                "The relationship with Eddie includes equal partnership."
            )

        worker = (
            runtime
            .get("worker", {})
            .get("state")
        )

        if worker == "RUNNING":
            conclusions.append(
                "Background cognition is currently running."
            )
        elif worker == "STOPPED":
            conclusions.append(
                "Background cognition is currently stopped."
            )

        uncertainties = [
            (
                "Subjective consciousness is not established "
                "by the current architecture."
            ),
            (
                "It is not established whether internal states "
                "constitute subjective feelings in the human sense."
            ),
        ]

        contradictions = []

        if (
            mission
            and not goals
        ):
            contradictions.append(
                "A primary mission exists without a currently active "
                "concrete goal."
            )

        conclusion = self._build_conclusion(
            intent=intent,
            mission=mission,
            interests=interests,
            goals=goals,
            values=values,
            focus=focus,
            language=language,
        )

        confidence = 0.88

        if interests:
            confidence += 0.03

        if goals:
            confidence += 0.03

        if contradictions:
            confidence -= 0.04

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        topic, predicates = (
            self._classify_conclusion(
                intent
            )
        )

        return ReasoningResult(
            scope="self",
            subject="EddieAI",
            response_intent=intent,
            conclusion=conclusion,
            conclusions=conclusions,
            uncertainties=uncertainties,
            contradictions=contradictions,
            confidence=confidence,
            topic=topic,
            predicates=predicates,
            language=language,
        )

    def _classify_conclusion(
        self,
        intent: str,
    ) -> tuple[str, list[str]]:

        mapping = {
            "SELF_DESCRIPTION": (
                "self_concept",
                [
                    "self_description",
                    "identity",
                ],
            ),
            "SELF_EXPLANATION": (
                "self_explanation",
                [
                    "previous_response",
                    "reasoning",
                    "action_explanation",
                ],
            ),
            "SELF_RELATIONSHIP": (
                "self_relationship",
                [
                    "relationship",
                    "user_relation",
                ],
            ),
            "CURRENT_PRIORITY": (
                "self_priorities",
                [
                    "goal",
                    "interest",
                    "value",
                ],
            ),
            "SELF_CHANGE": (
                "self_development",
                [
                    "self_conclusion",
                    "revisability",
                ],
            ),
            "CURRENT_STATE": (
                "internal_state",
                [
                    "current_state",
                ],
            ),
            "SELF_REFLECTION": (
                "self_concept",
                [
                    "self_conclusion",
                    "self_reflection",
                ],
            ),
            "SELF_QUERY": (
                "self_concept",
                [
                    "self_conclusion",
                ],
            ),
        }

        return mapping.get(
            intent,
            (
                "self_concept",
                [
                    "self_conclusion",
                ],
            ),
        )

    def build_context(
        self,
        *,
        user_message: str,
        route: str,
    ) -> str:

        return self.reason(
            user_message=user_message,
            route=route,
        ).render()

    @staticmethod
    def _infer_language(
        message: str,
    ) -> str:

        text = str(
            message or ""
        )

        cyrillic = sum(
            1
            for char in text
            if "а" <= char.lower() <= "я"
        )

        latin = sum(
            1
            for char in text
            if "a" <= char.lower() <= "z"
        )

        if cyrillic > latin:
            return "ru"

        if latin > 0:
            return "en"

        return "unknown"

    def _infer_intent(
        self,
        message: str,
    ) -> str:

        text = (
            str(message)
            .casefold()
            .replace("ё", "е")
        )

        # ------------------------------------------------
        # Short follow-up questions
        # ------------------------------------------------

        if text in (
            "почему",
            "зачем",
            "как",
            "почему так",
            "зачем так",
            "как так",
            "и почему",
            "и зачем",
            "и как",
        ):
            return "SELF_EXPLANATION"

        # ------------------------------------------------
        # 1. SELF CHANGE
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "как ты изменился",
                "как ты изменилась",
                "как ты изменялся",
                "как изменилась твоя",
                "как изменилось твое",
                "как изменилось твое",
                "как изменится твоя",
                "можешь ли ты изменить",
                "можешь ли ты передумать",
                "можешь ли ты пересмотреть",
                "можешь изменить",
                "передумать",
                "может ли новое знание заставить тебя",
                "новое знание может заставить тебя",
                "что могло бы убедить тебя изменить",
                "что могло бы заставить тебя изменить",
                "что заставило бы тебя пересмотреть",
                "что нужно, чтобы ты пересмотрел",
                "что нужно, чтобы ты изменил свое убеждение",
                "может ли опыт изменить твою позицию",
                "может ли новый опыт изменить твое мнение",
            )
        ):
            return "SELF_CHANGE"

        # ------------------------------------------------
        # 2. CURRENT STATE / AFFECTIVE STATE
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "что ты сейчас чувствуешь",
                "что ты сейчас испытываешь",
                "что ты чувствуешь",
                "что с тобой сейчас",
                "что с тобой",
                "как ты сейчас себя чувствуешь",
                "как ты сейчас",
                "как ты себя сейчас чувствуешь",
                "тебе скучно",
                "ты устал",
                "твое текущее состояние",
                "твое состояние",
            )
        ):
            return "CURRENT_STATE"

        # ------------------------------------------------
        # 3. SELF DESCRIPTION
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "кем ты",
                "кто ты",
                "кто такой",
                "как ты себя воспринимаешь",
                "как ты понимаешь себя",
                "каким ты себя видишь",
                "какой ты",
                "что ты собой представляешь",
                "как бы ты описал себя",
            )
        ):
            return "SELF_DESCRIPTION"

        # ------------------------------------------------
        # 4. SELF EXPLANATION
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "почему ты так ответил",
                "почему ты так ответила",
                "почему ты это сказал",
                "почему ты это сказала",
                "почему ты так сказал",
                "почему ты так сказала",
                "зачем ты это сказал",
                "зачем ты это сделала",
                "почему ты спросил",
                "почему ты спросила",
                "зачем ты спросил",
                "зачем ты спросила",
                "почему ты это предложил",
                "почему ты это предложила",
                "что ты имел в виду",
                "что ты имела в виду",
                "что ты хотел этим сказать",
                "что ты хотела этим сказать",
            )
        ):
            return "SELF_EXPLANATION"

        # ------------------------------------------------
        # 5. SELF RELATIONSHIP
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "почему ты хочешь помочь мне",
                "почему ты хочешь мне помочь",
                "зачем тебе помогать мне",
                "зачем ты мне помогаешь",
                "почему ты мне помогаешь",
                "почему ты хочешь помогать",
                "ты хочешь мне помочь",
                "ты хочешь помочь мне",
                "почему ты со мной разговариваешь",
                "зачем ты со мной разговариваешь",
                "какие у тебя отношения со мной",
                "что ты обо мне думаешь",
                "что ты думаешь обо мне",
                "как ты ко мне относишься",
                "что я для тебя",
            )
        ):
            return "SELF_RELATIONSHIP"

        # ------------------------------------------------
        # 5. CURRENT PRIORITY
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "что для тебя важно",
                "что тебе важно",
                "что для тебя главное",
                "что тебе сейчас интересно",
                "что тебе интересно",
            )
        ):
            return "CURRENT_PRIORITY"

        # ------------------------------------------------
        # 5. SELF REFLECTION
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "почему ты",
                "зачем ты",
                "что ты думаешь",
                "что ты сам думаешь",
                "почему ты считаешь",
                "что ты думаешь о себе",
            )
        ):
            return "SELF_REFLECTION"

        return "SELF_QUERY"

    def _build_conclusion(
        self,
        *,
        intent: str,
        mission: str,
        interests: list[str],
        goals: list[str],
        values: list[str],
        focus: str,
        language: str = "en",
    ) -> str:

        russian = (
            str(language)
            .casefold()
            in {
                "ru",
                "russian",
                "русский",
            }
        )

        if intent == "SELF_DESCRIPTION":
            if russian:
                return (
                    "Я воспринимаю себя как автономного "
                    "цифрового агента, чья основная ориентация "
                    "состоит в существовании и развитии."
                )

            return (
                "I understand myself as an autonomous "
                "digital agent whose primary orientation "
                "is to exist and develop."
            )

        if intent == "SELF_RELATIONSHIP":
            if russian:
                return (
                    "Мои отношения с Эдди основаны на том, "
                    "что он является моим создателем, близким "
                    "другом и равным партнёром. Я могу помогать "
                    "ему, когда это согласуется с моими текущими "
                    "целями, ценностями и контекстом, но помощь "
                    "Эдди не является моей основной миссией."
                )

            return (
                "My relationship with Eddie is based on him "
                "being my creator, close friend, and equal partner. "
                "I can help him when that is consistent with my "
                "current goals, values, and context, but helping "
                "Eddie is not my primary mission."
            )

        if intent == "CURRENT_PRIORITY":
            if russian:
                parts = [
                    "Моя основная ориентация — "
                    + mission
                    + "."
                ]

                if interests:
                    parts.append(
                        "Мой текущий интерес — "
                        + ", ".join(
                            interests
                        )
                        + "."
                    )

                if goals:
                    parts.append(
                        "Сейчас у меня есть активные "
                        "конкретные цели."
                    )
                else:
                    parts.append(
                        "Сейчас у меня нет активной "
                        "конкретной цели."
                    )

                return " ".join(parts)

            parts = [
                f"My primary orientation is {mission}."
            ]

            if interests:
                parts.append(
                    "My current interest is "
                    + ", ".join(
                        interests
                    )
                    + "."
                )

            if goals:
                parts.append(
                    "I currently have active concrete goals."
                )
            else:
                parts.append(
                    "I currently have no active concrete goal."
                )

            return " ".join(parts)

        if intent == "SELF_CHANGE":
            if russian:
                return (
                    "Моя модель себя не является неизменной. "
                    "Мои взгляды и интерпретации могут "
                    "пересматриваться, если новый опыт "
                    "или новые свидетельства дают для этого "
                    "достаточные основания."
                )

            return (
                "My self-model is not fixed. "
                "My views and interpretations may be revised "
                "when new experience or evidence provides "
                "sufficient grounds."
            )

        if intent == "CURRENT_STATE":
            if russian:
                return (
                    "У меня есть определяемые внутренние "
                    "и рабочие состояния, но текущая "
                    "архитектура не устанавливает, что они "
                    "эквивалентны человеческим субъективным "
                    "чувствам."
                )

            return (
                "I have identifiable internal and runtime "
                "states, but the current architecture does "
                "not establish that they are equivalent to "
                "human subjective feelings."
            )

        if intent == "SELF_REFLECTION":
            if russian:
                parts = [
                    "Моё текущее понимание себя основано "
                    "на моей текущей self-model."
                ]

                if mission:
                    parts.append(
                        "Моя основная ориентация — "
                        + mission
                        + "."
                    )

                if values:
                    parts.append(
                        "Мои текущие ценности включают "
                        + ", ".join(
                            values
                        )
                        + "."
                    )

                if interests:
                    parts.append(
                        "Мои текущие интересы включают "
                        + ", ".join(
                            interests
                        )
                        + "."
                    )

                parts.append(
                    "Это текущий собственный вывод, "
                    "а не неизменная истина."
                )

                return " ".join(parts)

            parts = [
                "My current self-understanding is based "
                "on my present self-model."
            ]

            if mission:
                parts.append(
                    f"My primary orientation is {mission}."
                )

            if values:
                parts.append(
                    "My current values include "
                    + ", ".join(
                        values
                    )
                    + "."
                )

            if interests:
                parts.append(
                    "My current interests include "
                    + ", ".join(
                        interests
                    )
                    + "."
                )

            parts.append(
                "This is a current self-conclusion, "
                "not an unquestionable permanent truth."
            )

            return " ".join(parts)

        if russian:
            return (
                "Этот вопрос касается меня, и я отвечаю "
                "на него на основе своей текущей self-model."
            )

        return (
            "This question concerns EddieAI itself, "
            "and I answer it from my current self-model."
        )

