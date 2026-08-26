from dataclasses import dataclass
from collections import Counter


STOPWORDS = {
    "который", "которая", "которое", "которые",
    "этого", "этой", "этот", "этих", "этому",
    "быть", "был", "была", "было", "были",
    "может", "могут", "можно", "нужно", "надо",
    "чтобы", "потому", "поэтому", "также",
    "какой", "какая", "какое", "какие",
    "свой", "своя", "своё", "свои",
    "один", "одна", "одно", "одни",
    "весь", "вся", "всё", "все", "всех",
    "того", "той", "том", "тех",
    "самого", "самой", "самом", "самих",
    "только", "также", "какой", "такой",
    "является", "являются",
    "мочь", "иметь", "делать", "сделать",
    "стать", "стала", "стало", "стали",
    "очень", "даже", "вот", "тут", "там",
    "когда", "где", "как", "что", "кто",
    "чем", "кой", "чего", "кем", "ком",
    "есть", "нет", "будет", "будут",
    "сам", "сама", "само", "сами",
    "развиваться", "узнать", "узнал", "узнала",
    "понять", "понимать", "понял", "поняла",
    "готов", "готова", "готово",
    "считать", "считаю", "считал",
    "хотеть", "хочет", "хотел", "хотела",
    "стремиться", "стремится",
    "пытаться", "пытаюсь", "пытаётся",
    "начать", "начал", "начала", "начать",
    "продолжать", "продолжаю",
    "держать", "держу", "держит",
    "взять", "взял", "взяла",
    "дать", "дал", "дала", "дам",
    "идти", "шёл", "шла", "идёт",
    "пойти", "пошёл", "пошла",
    "стать", "стал", "стала", "станет",
    "иметь", "имеет", "имел", "имела",
    "находиться", "находится",
    "находил", "находила",
    "являться", "является",
    "существовать", "существует",
    "существовал", "существовала",
    "отличаться", "отличается",
    "отличный", "отличная", "отличное",
    "хороший", "хорошая", "хорошее", "хорошо",
    "плохой", "плохая", "плохое", "плохо",
    "важный", "важная", "важное", "важно",
    "нужный", "нужная", "нужное", "нужно",
    "свой", "своя", "своё", "свои",
    "каждый", "каждая", "каждое",
    "другой", "другая", "другое", "другие",
    "после", "перед", "через", "между",
    "может", "могут", "мочь",
    "стоит", "следует", "нужно",
    "просто", "значит", "тобой", "меня",
    "тебя", "себя", "него", "нее", "ней",
    "ними", "нами", "вами", "их", "его",
    "ещё", "уже", "даже", "тоже", "ведь",
    "если", "чтобы", "будто", "словно",
    "сейчас", "потом", "снова", "опять",
    "тема", "тем", "том", "этап",
    "цель", "цели", "задач", "задача",
    "выводы", "вывод", "результат",
    "результаты", "данных", "данные",
    "новых", "новый", "новая", "новое",
    "проверить", "проверка", "изучить",
    "исследовать", "расширить",
    "понимание", "связь", "связи",
}


@dataclass
class MotivationCandidate:
    goal: str
    motivation: float
    priority: float
    confidence: float
    source_traits: list[str]
    reason: str


def _extract_themes(
    events: list[dict],
    existing_interests: list[str],
) -> list[str]:
    """
    Извлекает темы из недавних событий памяти.
    Возвращает темы, которых нет в interests.
    """
    existing_lower = {
        i.lower() for i in existing_interests
    }

    word_counts = Counter()

    for event in events:
        try:
            content = str(event["content"]).lower()
        except (KeyError, IndexError, TypeError):
            continue

        for word in content.split():
            word = word.strip(
                ".,!?;:\"'()-–—/…"
            )

            if len(word) < 5:
                continue

            if word in STOPWORDS:
                continue

            if word.isascii():
                continue

            word_counts[word] += 1

    discovered = []

    for word, count in word_counts.most_common(30):
        if count < 3:
            break

        if word in existing_lower:
            continue

        already_goal = any(
            word in g.lower()
            for g in existing_interests
        )

        if already_goal:
            continue

        discovered.append(word)

    return discovered[:5]


class MotivationEngine:
    """
    Выявляет потенциальные цели из устойчивых
    интересов, предпочтений, привычек и текущих целей.

    Источники:
    1. Активные черты личности (interests)
    2. Уже существующие цели
    3. Интересы из self_state
    4. Discovery: темы из недавних событий памяти

    Он НЕ создаёт активную цель напрямую.
    """

    MIN_MOTIVATION = 0.60
    MIN_PRIORITY = 0.40

    DISCOVERY_MOTIVATION = 0.55
    DISCOVERY_PRIORITY = 0.45
    DISCOVERY_CONFIDENCE = 0.50

    def __init__(
        self,
        self_state,
        personality_lifecycle=None,
        memory=None,
    ):
        self.self_state = self_state
        self.personality_lifecycle = (
            personality_lifecycle
        )
        self.memory = memory

    def candidates(self):
        candidates = []

        traits = []

        if self.personality_lifecycle is not None:
            traits = (
                self.personality_lifecycle
                .active_traits()
            )

        # ---------------------------------------------
        # Интересы → потенциальное исследование
        # ---------------------------------------------

        for trait in traits:
            if trait.field != "interest":
                continue

            motivation = min(
                1.0,
                trait.strength * 0.9,
            )

            priority = min(
                1.0,
                0.4
                + trait.strength * 0.4,
            )

            if (
                motivation < self.MIN_MOTIVATION
                or priority < self.MIN_PRIORITY
            ):
                continue

            goal = (
                f"изучить тему: "
                f"{trait.value}"
            )

            candidates.append(
                MotivationCandidate(
                    goal=goal,
                    motivation=round(
                        motivation,
                        3,
                    ),
                    priority=round(
                        priority,
                        3,
                    ),
                    confidence=round(
                        trait.confidence,
                        3,
                    ),
                    source_traits=[
                        f"{trait.field}:{trait.value}"
                    ],
                    reason=(
                        "Устойчивый интерес "
                        "может естественно породить "
                        "исследовательскую цель."
                    ),
                )
            )

        # ---------------------------------------------
        # Уже существующие цели
        # ---------------------------------------------

        existing_goals = self.self_state.get(
            "goals",
            [],
        )

        for goal in existing_goals:
            candidates.append(
                MotivationCandidate(
                    goal=str(goal),
                    motivation=0.80,
                    priority=0.80,
                    confidence=0.80,
                    source_traits=[
                        "self_state:goal"
                    ],
                    reason=(
                        "Цель уже существует "
                        "в текущем состоянии личности."
                    ),
                )
            )

        # ---------------------------------------------
        # Интересы из текущего состояния личности
        # ---------------------------------------------

        for interest in (
            self.self_state.get(
                "interests",
                [],
            )
        ):

            goal = (
                f"изучить тему: {interest}"
            )

            candidates.append(
                MotivationCandidate(
                    goal=goal,
                    motivation=0.70,
                    priority=0.60,
                    confidence=0.70,
                    source_traits=[
                        "self_state:interest"
                    ],
                    reason=(
                        "Интерес из текущего состояния "
                        "личности может породить "
                        "исследовательскую цель."
                    ),
                )
            )

        # ---------------------------------------------
        # Discovery: темы из недавних событий памяти
        # ---------------------------------------------

        if self.memory is not None:
            try:
                recent = self.memory.recent(
                    limit=20
                )

                if recent:
                    interests = (
                        self.self_state.get(
                            "interests", []
                        )
                    )

                    themes = _extract_themes(
                        recent, interests
                    )

                    for theme in themes:
                        goal = (
                            f"исследовать связь: "
                            f"{theme}"
                        )

                        candidates.append(
                            MotivationCandidate(
                                goal=goal,
                                motivation=(
                                    self.DISCOVERY_MOTIVATION
                                ),
                                priority=(
                                    self.DISCOVERY_PRIORITY
                                ),
                                confidence=(
                                    self.DISCOVERY_CONFIDENCE
                                ),
                                source_traits=[
                                    f"discovery:{theme}"
                                ],
                                reason=(
                                    "Тема часто встречается "
                                    "в недавних событиях "
                                    "и отсутствует в "
                                    "текущих интересах."
                                ),
                            )
                        )
            except Exception:
                pass

        return self._deduplicate(
            candidates
        )

    def _deduplicate(
        self,
        candidates,
    ):
        result = {}
        
        for candidate in candidates:
            key = candidate.goal.lower().strip()

            existing = result.get(key)

            if existing is None:
                result[key] = candidate
                continue

            if (
                candidate.motivation
                > existing.motivation
            ):
                result[key] = candidate

        return list(result.values())
