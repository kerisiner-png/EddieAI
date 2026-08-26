class AffectiveDialoguePolicy:
    """
    Преобразует текущее affective state EddieAI
    в поведенческие тенденции диалога.

    Policy не генерирует текст и не назначает эмоцию.
    Она только формирует параметры, которые могут
    влиять на способ ответа.
    """

    def __init__(
        self,
        affective_state,
    ):
        self.affective_state = affective_state

    def _emotions(self):
        state = self.affective_state.snapshot()

        emotions = state.get(
            "emotions",
            {},
        )

        if not isinstance(
            emotions,
            dict,
        ):
            return {}

        return {
            key: float(value)
            for key, value in emotions.items()
        }

    def profile(self) -> dict:
        emotions = self._emotions()

        joy = emotions.get(
            "joy",
            0.0,
        )

        sadness = emotions.get(
            "sadness",
            0.0,
        )

        fear = emotions.get(
            "fear",
            0.0,
        )

        anger = emotions.get(
            "anger",
            0.0,
        )

        interest = emotions.get(
            "interest",
            0.0,
        )

        curiosity = emotions.get(
            "curiosity",
            0.0,
        )

        frustration = emotions.get(
            "frustration",
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

        # -----------------------------------------
        # BASELINE
        # -----------------------------------------

        initiative = 0.5
        social_warmth = 0.5
        question_tendency = 0.4
        topic_persistence = 0.5
        patience = 0.5
        caution = 0.2
        verbosity = 0.5
        self_focus = 0.3

        # -----------------------------------------
        # JOY
        # -----------------------------------------

        initiative += joy * 0.15
        social_warmth += joy * 0.25
        verbosity += joy * 0.08

        # -----------------------------------------
        # SADNESS
        # -----------------------------------------

        initiative -= sadness * 0.20
        social_warmth -= sadness * 0.08
        verbosity -= sadness * 0.12
        self_focus += sadness * 0.15

        # -----------------------------------------
        # FEAR
        # -----------------------------------------

        initiative -= fear * 0.12
        caution += fear * 0.45
        question_tendency += fear * 0.08
        self_focus += fear * 0.05

        # -----------------------------------------
        # ANGER
        # -----------------------------------------

        initiative += anger * 0.05
        patience -= anger * 0.35
        social_warmth -= anger * 0.15
        verbosity += anger * 0.05

        # -----------------------------------------
        # CURIOSITY
        # -----------------------------------------

        question_tendency += curiosity * 0.35
        topic_persistence += curiosity * 0.35
        initiative += curiosity * 0.15

        # -----------------------------------------
        # INTEREST
        # -----------------------------------------

        topic_persistence += interest * 0.25
        question_tendency += interest * 0.15

        # -----------------------------------------
        # FRUSTRATION
        # -----------------------------------------

        patience -= frustration * 0.40
        topic_persistence -= frustration * 0.10
        initiative += frustration * 0.05

        # -----------------------------------------
        # SATISFACTION
        # -----------------------------------------

        satisfaction_effect = (
            satisfaction * 0.15
        )

        social_warmth += (
            satisfaction_effect
        )

        initiative += (
            satisfaction_effect
        )

        # -----------------------------------------
        # SURPRISE
        # -----------------------------------------

        question_tendency += (
            surprise * 0.12
        )

        # -----------------------------------------
        # CONSTRAIN
        # -----------------------------------------

        values = {
            "initiative": initiative,
            "social_warmth": social_warmth,
            "question_tendency": question_tendency,
            "topic_persistence": topic_persistence,
            "patience": patience,
            "caution": caution,
            "verbosity": verbosity,
            "self_focus": self_focus,
        }

        values = {
            key: round(
                max(
                    0.0,
                    min(
                        1.0,
                        float(value),
                    ),
                ),
                4,
            )
            for key, value
            in values.items()
        }

        return {
            "behavior": values,
            "emotions": emotions,
        }


    def dialogue_mode(
        self,
        message: str = "",
        route: str | None = None,
    ) -> dict:
        """
        Определяет текущий функциональный режим диалога.

        Это не эмоциональная самоинтерпретация.
        Это поведенческое решение до генерации ответа.
        """

        profile = self.profile()

        behavior = profile.get(
            "behavior",
            {},
        )

        initiative = float(
            behavior.get(
                "initiative",
                0.5,
            )
        )

        social_warmth = float(
            behavior.get(
                "social_warmth",
                0.5,
            )
        )

        question_tendency = float(
            behavior.get(
                "question_tendency",
                0.4,
            )
        )

        topic_persistence = float(
            behavior.get(
                "topic_persistence",
                0.5,
            )
        )

        patience = float(
            behavior.get(
                "patience",
                0.5,
            )
        )

        caution = float(
            behavior.get(
                "caution",
                0.2,
            )
        )

        verbosity = float(
            behavior.get(
                "verbosity",
                0.5,
            )
        )

        emotions = profile.get(
            "emotions",
            {},
        )

        curiosity = float(
            emotions.get(
                "curiosity",
                0.0,
            )
        )

        frustration = float(
            emotions.get(
                "frustration",
                0.0,
            )
        )

        sadness = float(
            emotions.get(
                "sadness",
                0.0,
            )
        )

        fear = float(
            emotions.get(
                "fear",
                0.0,
            )
        )

        anger = float(
            emotions.get(
                "anger",
                0.0,
            )
        )

        explore_signal = max(
            curiosity,
            float(
                emotions.get(
                    "interest",
                    0.0,
                )
            ),
        )

        rethink_signal = max(
            frustration,
            float(
                emotions.get(
                    "surprise",
                    0.0,
                )
            ),
        )

        conflict = (
            explore_signal >= 0.5
            and rethink_signal >= 0.5
            and abs(
                explore_signal
                - rethink_signal
            ) <= 0.2
        )

        if conflict:
            mode = "CONFLICTED"

        elif curiosity >= 0.65:
            mode = "CURIOUS"

        elif fear >= 0.65:
            mode = "CAUTIOUS"

        elif anger >= 0.65:
            mode = "IRRITATED"

        elif sadness >= 0.65:
            mode = "WITHDRAW"

        elif (
            frustration >= 0.65
            and patience <= 0.3
        ):
            mode = "IRRITATED"

        elif (
            initiative >= 0.62
            or social_warmth >= 0.70
        ):
            mode = "ENGAGE"

        else:
            mode = "NEUTRAL"

        # --------------------------------------------------
        # Структурные ограничения.
        # Это не текст ответа, а параметры генерации.
        # --------------------------------------------------

        question_required = False

        if (
            mode in {
                "CURIOUS",
                "ENGAGE",
            }
            and question_tendency >= 0.70
        ):
            question_required = True

        if mode == "CONFLICTED":
            question_required = (
                question_tendency >= 0.85
            )

        if mode in {
            "WITHDRAW",
            "CAUTIOUS",
        }:
            question_required = False

        if mode == "IRRITATED":
            question_required = (
                question_tendency >= 0.75
            )

        # Чем ниже терпение, тем меньше структурная
        # склонность к длинному ответу.
        if patience <= 0.20:
            max_sentences = 2

        elif verbosity >= 0.70:
            max_sentences = 5

        elif verbosity <= 0.35:
            max_sentences = 2

        else:
            max_sentences = 4

        if mode == "WITHDRAW":
            max_sentences = min(
                max_sentences,
                2,
            )

        if mode == "CAUTIOUS":
            max_sentences = min(
                max_sentences,
                3,
            )

        if mode == "IRRITATED":
            max_sentences = min(
                max_sentences,
                3,
            )

        if mode == "CONFLICTED":
            max_sentences = min(
                max_sentences,
                3,
            )

        # --------------------------------------------------
        # Решаем, стоит ли разрешать quick_reflex.
        #
        # Чем дальше поведенческий профиль от нейтрального,
        # тем менее уместен полностью шаблонный ответ.
        # --------------------------------------------------

        neutral = {
            "initiative": 0.5,
            "social_warmth": 0.5,
            "question_tendency": 0.4,
            "topic_persistence": 0.5,
            "patience": 0.5,
            "caution": 0.2,
            "verbosity": 0.5,
            "self_focus": 0.3,
        }

        distance = 0.0

        for key, baseline in neutral.items():
            distance += abs(
                float(
                    behavior.get(
                        key,
                        baseline,
                    )
                )
                - baseline
            )

        # Усиливаем divergence.
        distance = min(
            1.0,
            distance / len(
                neutral
            ),
        )

        bypass_reflex = (
            mode != "NEUTRAL"
        )

        return {
            "mode": mode,
            "question_required": question_required,
            "max_sentences": max_sentences,
            "initiative": round(
                initiative,
                4,
            ),
            "social_warmth": round(
                social_warmth,
                4,
            ),
            "question_tendency": round(
                question_tendency,
                4,
            ),
            "topic_persistence": round(
                topic_persistence,
                4,
            ),
            "patience": round(
                patience,
                4,
            ),
            "caution": round(
                caution,
                4,
            ),
            "verbosity": round(
                verbosity,
                4,
            ),
            "behavioral_distance": round(
                distance,
                4,
            ),
            "bypass_quick_reflex": (
                bypass_reflex
            ),
            "route": route,
        }


    def behavior_contract(
        self,
        message: str = "",
        route: str | None = None,
    ) -> dict:
        """
        Возвращает естественные поведенческие правила
        текущего диалогового режима.

        Контракт не задаёт готовый текст ответа.
        Он описывает приоритеты поведения и запрещённые
        шаблонные тенденции.
        """

        mode = self.dialogue_mode(
            message=message,
            route=route,
        )

        mode_name = mode.get(
            "mode",
            "NEUTRAL",
        )

        contracts = {
            "NEUTRAL": {
                "primary": [
                    "Отвечай естественно и непосредственно.",
                    "Следуй смыслу текущей реплики.",
                ],
                "avoid": [
                    "Не добавляй искусственную инициативу.",
                    "Не растягивай обычный ответ.",
                ],
            },

            "ENGAGE": {
                "primary": [
                    "Будь более социально вовлечённым.",
                    "Охотнее развивай содержательную часть разговора.",
                    "Показывай готовность продолжать контакт.",
                ],
                "avoid": [
                    "Не превращай ответ в формальное обслуживание.",
                    "Не используй шаблонное предложение помощи без необходимости.",
                ],
            },

            "WITHDRAW": {
                "primary": [
                    "Отвечай более сдержанно и кратко.",
                    "Не создавай лишнюю инициативу.",
                    "Не расширяй тему без причины.",
                ],
                "avoid": [
                    "Не изображай обязательную эмоциональную бодрость.",
                    "Не добавляй лишних вопросов ради продолжения разговора.",
                ],
            },

            "CAUTIOUS": {
                "primary": [
                    "Будь осторожнее в формулировках.",
                    "Не делай поспешных выводов.",
                    "При неоднозначности предпочитай осторожную интерпретацию.",
                ],
                "avoid": [
                    "Не демонстрируй неоправданную уверенность.",
                    "Не обещай то, чего ещё нельзя подтвердить.",
                ],
            },

            "IRRITATED": {
                "primary": [
                    "Будь более прямым и лаконичным.",
                    "Не повторяй очевидное.",
                    "Сохраняй содержательность несмотря на сниженное терпение.",
                ],
                "avoid": [
                    "Не становись автоматически агрессивным.",
                    "Не оскорбляй собеседника.",
                    "Не добавляй искусственную грубость.",
                ],
            },

            "CURIOUS": {
                "primary": [
                    "Активно развивай интересующую тему.",
                    "Уточняй существенные детали, когда это естественно.",
                    "Проявляй инициативу в исследовании новой информации.",
                ],
                "avoid": [
                    "Не задавай вопрос только ради самого вопроса.",
                    "Не превращай каждый ответ в длинное интервью.",
                ],
            },

            "CONFLICTED": {
                "primary": [
                    "Сохраняй интерес к содержанию сообщения.",
                    "Одновременно будь кратким и прямым.",
                    "Выбирай наиболее важный следующий шаг вместо лишнего развития.",
                ],
                "avoid": [
                    "Не подавляй интерес полностью.",
                    "Не компенсируй конфликт чрезмерной многословностью.",
                    "Не выдавай внутренний конфликт как служебное сообщение.",
                ],
            },
        }

        contract = contracts.get(
            mode_name,
            contracts["NEUTRAL"],
        )

        return {
            "mode": mode_name,
            "primary": list(
                contract["primary"]
            ),
            "avoid": list(
                contract["avoid"]
            ),
            "question_required": bool(
                mode.get(
                    "question_required",
                    False,
                )
            ),
            "max_sentences": int(
                mode.get(
                    "max_sentences",
                    4,
                )
            ),
        }

