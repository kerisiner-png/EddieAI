import unittest
from unittest.mock import MagicMock


class FakeSelfStateDaily:
    def __init__(self):
        self._data = {"interests": ["тема"], "usage_today": {}}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestDailyLlmTopic(unittest.TestCase):
    def test_calls_llm_once_per_day(self):
        from core.curiosity import CuriosityDirector

        llm = MagicMock()
        llm.chat.return_value = "Тема: устройство памяти человека"
        d = CuriosityDirector(
            FakeSelfStateDaily(),
            goal_manager=MagicMock(),
            llm=llm,
        )
        t1 = d.daily_llm_topic(recent_life="сон: сегодня видел интересный сон")
        t2 = d.daily_llm_topic(recent_life="сон: опять")
        self.assertEqual(t1, t2)  # повторный вызов в тот же день не переспрашивает LLM
        llm.chat.assert_called_once()

    def test_graceful_without_llm(self):
        from core.curiosity import CuriosityDirector

        d = CuriosityDirector(FakeSelfStateDaily(), MagicMock(), llm=None)
        t = d.daily_llm_topic()
        self.assertIsNone(t)


if __name__ == "__main__":
    unittest.main()