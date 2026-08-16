class ReflectionScheduler:
    """
    Решает, когда EddieAI стоит остановиться
    и пересмотреть накопленный опыт.
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

    def run_reflection(self):
        result = self.agent.reflect()
        self.events_since_reflection = 0
        return result

    def session_end(self):
        if self.events_since_reflection <= 0:
            return None

        return self.run_reflection()

    def sleep_cycle(self):
        return self.run_reflection()
