class ReflectionScheduler:
    """
    Управляет периодическими циклами рефлексии личности.

    Обычные сообщения не изменяют силу черт напрямую.
    Изменения происходят во время reflection/sleep cycle.
    """

    def __init__(
        self,
        agent,
        event_threshold: int = 8,
    ):
        self.agent = agent
        self.event_threshold = event_threshold
        self.events_since_reflection = 0

    def event_happened(
        self,
        significant: bool = True,
    ):
        if not significant:
            return False

        self.events_since_reflection += 1

        if (
            self.events_since_reflection
            >= self.event_threshold
        ):
            return self.run_reflection()

        return False

    def _reinforce_confirmed_traits(self):
        """
        Подкрепляет уже активные свойства, если
        evidence снова подтверждает их.
        """

        results = []

        traits = (
            self.agent.personality_lifecycle
            .all_traits()
        )

        for trait in traits:
            if trait.status == "REJECTED":
                continue

            category = trait.field

            evidence = self.agent.evidence.get(
                category,
                trait.value,
            )

            if evidence is None:
                continue

            if evidence.confidence <= 0:
                continue

            updated = (
                self.agent
                .personality_lifecycle
                .reinforce(
                    field=trait.field,
                    value=trait.value,
                    amount=0.02,
                )
            )

            if updated is not None:
                results.append(updated)

        return results

    def run_reflection(self):
        """
        Полный reflection cycle:

        1. Анализ опыта.
        2. Анализ кандидатов.
        3. Применение подтверждённых изменений.
        4. Подкрепление существующих черт.
        5. Медленное затухание.
        """

        cycle_result = (
            self.agent.reflection_cycle.run()
        )

        application_result = (
            self.agent.apply_reflection_cycle(
                cycle_result
            )
        )

        reinforced = (
            self._reinforce_confirmed_traits()
        )

        # Одно небольшое затухание за цикл.
        self.agent.personality_lifecycle.decay(
            amount=0.02
        )

        self.events_since_reflection = 0

        return {
            "cycle": cycle_result,
            "applied": application_result,
            "reinforced": reinforced,
        }

    def session_end(self):
        """
        Reflection при завершении сессии.
        """

        if self.events_since_reflection <= 0:
            return None

        return self.run_reflection()

    def sleep_cycle(self):
        """
        Будущий полноценный цикл сна.

        Пока делает обычный reflection cycle,
        но может отдельно расширяться до:
        - консолидации памяти;
        - забывания;
        - анализа долгосрочных целей;
        - эмоциональной переработки.
        """

        return self.run_reflection()
