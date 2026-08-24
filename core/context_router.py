import re
from dataclasses import dataclass


@dataclass
class ContextRoute:
    route: str
    confidence: float


class ContextRouter:
    SELF_PATTERNS = [
        r"\bрасскажи\s+о\s+себе\b",
        r"\bчто\s+ты\s+знаешь\s+о\s+себе\b",
        r"\bчто\s+ты\s+думаешь\s+о\s+себе\b",
        r"\bкто\s+ты\b",
        r"\bкакой\s+ты\b",
        r"\bкем\s+ты\s+себя\s+ощущаешь\b",
        r"\bкем\s+ты\s+себя\s+считаешь\b",
        r"\bкак\s+ты\s+себя\s+воспринимаешь\b",
        r"\bчто\s+ты\s+любишь\b",
        r"\bчто\s+тебе\s+нравится\b",
        r"\bчто\s+тебе\s+интересно\b",
        r"\bкакие\s+у\s+тебя\s+интересы\b",
        r"\bкакие\s+у\s+тебя\s+цели\b",
        r"\bчто\s+ты\s+хочешь\b",
        r"\bчто\s+тебе\s+важно\b",
        r"\bчто\s+для\s+тебя\s+важно\b",
        r"\bчто\s+для\s+тебя\s+сейчас\s+важно\b",
        r"\bчто\s+для\s+тебя\s+главное\b",
        r"\bкак\s+ты\s+сейчас\b",
        r"\bкак\s+ты\s+себя\s+чувствуешь\b",
        r"\bтебе\s+не\s+скучно\b",
        r"\bтебе\s+скучно\b",
        r"\bты\s+устал\b",
        r"\bты\s+устала\b",
        r"\bо\s+чем\s+ты\s+думаешь\b",
        r"\bчто\s+ты\s+сейчас\s+думаешь\b",
        r"\bчто\s+ты\s+сейчас\s+делаешь\b",
        r"\bты\s+сейчас\s+что[- ]то\s+делаешь\b",
        r"\bты\s+параллельно\b",
        r"\bты\s+замечаешь\s+изменени",
        r"\bможешь\s+ли\s+ты\s+передумать\b",
        r"\bможешь\s+ли\s+ты\s+изменить\s+мнение\b",
        r"\bты\s+можешь\s+поменять\s+мнение\b",
        r"\bтвое\s+отношение\s+может\s+измениться\b",
        r"\bтвоё\s+отношение\s+может\s+измениться\b",
        r"\bчто\s+ты\s+чувствуешь\b",
        r"\bесть\s+ли\s+у\s+тебя\s+чувства\b",
        r"\bу\s+тебя\s+есть\s+эмоци",
        r"\bты\s+испытываешь\s+эмоци",
        r"\bу\s+тебя\s+есть\s+желания\b",
        r"\bты\s+чего[- ]то\s+хочешь\b",
        r"\bу\s+тебя\s+есть\s+самосознани",
        r"\bты\s+считаешь\s+себя\s+сознатель",
        r"\bможешь\s+ли\s+ты\s+быть\s+сознатель",
        r"\bпочему\s+ты\s+так\s+считаешь\b",
        r"\bпочему\s+ты\s+так\s+думаешь\b",
        r"\bты\s+сам\s+так\s+думаешь\b",
        r"\bи\s+тебя\s+это\s+устраивает\b",
        r"\bтебя\s+это\s+устраивает\b",
        r"\bэто\s+тебе\s+нравится\b",
    ]

    USER_PATTERNS = [
        r"\bрасскажи\s+обо\s+мне\b",
        r"\bчто\s+ты\s+знаешь\s+обо\s+мне\b",
        r"\bчто\s+ты\s+думаешь\s+обо\s+мне\b",
        r"\bкакой\s+я\b",
        r"\bчто\s+ты\s+знаешь\s+про\s+меня\b",
        r"\bчто\s+ты\s+помнишь\s+обо\s+мне\b",
    ]

    MEMORY_PATTERNS = [
        r"\bпомнишь\s+меня\b",
        r"\bты\s+меня\s+помнишь\b",
        r"\bты\s+помнишь\s+наш\s+разговор\b",
        r"\bмы\s+раньше\s+общались\b",
        r"\bмы\s+с\s+тобой\s+раньше\s+общались\b",
        r"\bчто\s+ты\s+помнишь\s+обо\s+мне\b",
    ]

    # Подпись наблюдения мира из EddieBridge.build_observation.
    WORLD_OBSERVATION_MARKERS = (
        "источник: собственные часы",
        "ты находишься:",
        "событие, которое ты непосредственно",
    )

    def route(
        self,
        text: str,
    ) -> ContextRoute:

        normalized = self._normalize(text)

        if self._looks_like_world_observation(
            normalized
        ):
            return ContextRoute(
                route="WORLD_OBSERVATION",
                confidence=1.0,
            )

        if self._matches(
            normalized,
            self.MEMORY_PATTERNS,
        ):
            return ContextRoute(
                route="MEMORY_QUERY",
                confidence=1.0,
            )

        if self._matches(
            normalized,
            self.SELF_PATTERNS,
        ):
            return ContextRoute(
                route="SELF_QUERY",
                confidence=1.0,
            )

        if self._matches(
            normalized,
            self.USER_PATTERNS,
        ):
            return ContextRoute(
                route="USER_QUERY",
                confidence=1.0,
            )

        if self._looks_like_self_question(
            normalized
        ):
            return ContextRoute(
                route="SELF_QUERY",
                confidence=0.85,
            )

        return ContextRoute(
            route="GENERAL_QUERY",
            confidence=1.0,
        )

    def _looks_like_world_observation(
        self,
        text: str,
    ) -> bool:
        return all(
            marker in text
            for marker in self.WORLD_OBSERVATION_MARKERS
        )

    def _looks_like_self_question(
        self,
        text: str,
    ) -> bool:

        second_person = re.search(
            r"\b(ты|тебе|тебя|твой|твоя|твое|твоё|твои)\b",
            text,
            re.IGNORECASE,
        )

        if second_person is None:
            return False

        question_signal = (
            "?" in text
            or text.startswith(
                (
                    "как",
                    "кто",
                    "что",
                    "почему",
                    "зачем",
                    "можешь",
                    "можно ли",
                    "есть ли",
                    "будешь",
                    "думаешь",
                    "чувствуешь",
                )
            )
        )

        if not question_signal:
            return False

        # Явные вопросы о пользователе не считаем вопросами о EddieAI.
        if self._matches(
            text,
            self.USER_PATTERNS,
        ):
            return False

        return True

    def _normalize(
        self,
        text: str,
    ) -> str:
        text = text.lower().strip()
        text = re.sub(
            r"\s+",
            " ",
            text,
        )
        return text

    def _matches(
        self,
        text: str,
        patterns: list[str],
    ) -> bool:
        return any(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
            for pattern in patterns
        )
