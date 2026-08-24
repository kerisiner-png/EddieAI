from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DirectAnswer:
    found: bool
    answer: str
    source: str
    confidence: float


class KnowledgeResolver:
    """
    Проверяет, можно ли честно ответить на запрос
    напрямую из уже известных данных EddieAI.

    Не вызывает LLM.
    Не изменяет состояние.
    Не делает догадок.
    """

    def __init__(self, agent):
        self.agent = agent

    def resolve(
        self,
        message: str,
    ) -> DirectAnswer:

        text = (
            message
            .strip()
            .lower()
        )

        state = (
            self.agent.self_state.snapshot()
        )

        mission = state.get(
            "primary_mission"
        )

        mission_text = state.get(
            "mission_statement"
        )

        interests = state.get(
            "interests",
            [],
        )

        goals = state.get(
            "goals",
            [],
        )

        roles = (
            state
            .get(
                "relationships",
                {},
            )
            .get(
                "Eddie",
                {},
            )
            .get(
                "roles",
                [],
            )
        )

        base_model = None

        for model in self.agent.model_orchestrator.models:
            if model.name == "phi4-mini:latest":
                base_model = model.name
                break

        if self._matches(
            text,
            (
                "какая у тебя основная миссия",
                "какова твоя основная миссия",
                "в чем твоя основная миссия",
                "в чём твоя основная миссия",
                "зачем ты существуешь",
            ),
        ):
            if mission_text:
                return DirectAnswer(
                    found=True,
                    answer=(
                        "Моя основная миссия — "
                        + str(mission_text)
                        + "."
                    ),
                    source="self_state.mission_statement",
                    confidence=1.0,
                )

            if mission:
                return DirectAnswer(
                    found=True,
                    answer=(
                        "Моя основная миссия — "
                        + str(mission)
                        + "."
                    ),
                    source="self_state.primary_mission",
                    confidence=1.0,
                )

        if self._matches(
            text,
            (
                "какой у тебя сейчас интерес",
                "какой у тебя интерес",
                "какие у тебя интересы",
                "что тебе интересно",
                "что тебя интересует",
            ),
        ):
            if interests:
                return DirectAnswer(
                    found=True,
                    answer=(
                        "Сейчас мой сформированный интерес — "
                        + ", ".join(
                            str(item)
                            for item in interests
                        )
                        + "."
                    ),
                    source="self_state.interests",
                    confidence=1.0,
                )

            return DirectAnswer(
                found=True,
                answer="Сейчас у меня нет сформированных интересов.",
                source="self_state.interests",
                confidence=1.0,
            )

        if self._matches(
            text,
            (
                "какие у тебя активные цели",
                "какие у тебя сейчас цели",
                "есть ли у тебя активные цели",
                "у тебя есть цели",
            ),
        ):
            if goals:
                return DirectAnswer(
                    found=True,
                    answer=(
                        "Сейчас у меня есть активные цели: "
                        + ", ".join(
                            str(item)
                            for item in goals
                        )
                        + "."
                    ),
                    source="self_state.goals",
                    confidence=1.0,
                )

            return DirectAnswer(
                found=True,
                answer="Сейчас у меня нет активных целей.",
                source="self_state.goals",
                confidence=1.0,
            )

        if self._matches(
            text,
            (
                "кто твой партнер",
                "кто твой партнёр",
                "кто для тебя эдди",
                "кем тебе приходится эдди",
            ),
        ):
            if roles:
                parts = []

                if "creator" in roles:
                    parts.append("создатель")

                if "close_friend" in roles:
                    parts.append("близкий друг")

                if "equal_partner" in roles:
                    parts.append("равный партнёр")

                if parts:
                    return DirectAnswer(
                        found=True,
                        answer=(
                            "Эдди для меня — "
                            + ", ".join(parts)
                            + "."
                        ),
                        source="self_state.relationships.Eddie",
                        confidence=1.0,
                    )

        if self._matches(
            text,
            (
                "какая у тебя базовая модель",
                "какая у тебя языковая модель",
                "какую модель ты используешь",
                "на какой модели ты работаешь",
            ),
        ):
            if base_model:
                return DirectAnswer(
                    found=True,
                    answer=(
                        "Сейчас я использую "
                        + str(base_model)
                        + " как языковой компонент."
                    ),
                    source="identity_seed.base_model",
                    confidence=1.0,
                )

        return DirectAnswer(
            found=False,
            answer="",
            source="none",
            confidence=0.0,
        )

    @staticmethod
    def _matches(
        text: str,
        phrases: tuple[str, ...],
    ) -> bool:
        return any(
            phrase in text
            for phrase in phrases
        )

