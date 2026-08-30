import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone


class FakeSelfState:
    def __init__(self):
        self._data = {
            "interests": [
                "понимание устройства мира",
                "исследование своей природы",
            ],
            "usage_today": {},
        }

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def make_director(**kw):
    from core.curiosity import CuriosityDirector

    ss = kw.pop("self_state", FakeSelfState())
    gm = kw.pop("goal_manager", MagicMock())
    return CuriosityDirector(ss, gm, **kw)


class TestCuriosityDirector(unittest.TestCase):
    def test_returns_wait_during_cooldown(self):
        d = make_director()
        d.last_step_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        res = d.evaluate(asleep=False)
        self.assertFalse(res["should_act"])
        self.assertIn("кулдаун", res["reason"].lower())

    def test_returns_wait_while_asleep(self):
        d = make_director()
        res = d.evaluate(asleep=True)
        self.assertFalse(res["should_act"])
        self.assertIn("спит", res["reason"].lower())

    def test_selects_topic_from_interests(self):
        d = make_director()
        topic = d.select_topic()
        self.assertTrue(topic["title"].startswith("Исследовать тему:"))
        self.assertIn(topic["topic"], ["понимание устройства мира", "исследование своей природы"])

    def test_no_llm_in_select_topic(self):
        llm = MagicMock()
        d = make_director(llm=llm)
        d.select_topic()
        llm.chat.assert_not_called()

    def test_waits_when_ram_low(self):
        d = make_director()
        res = d.evaluate(asleep=False, available_ram_mb=400)
        self.assertFalse(res["should_act"])
        self.assertIn("память", res["reason"].lower())

    def test_uses_goal_manager_for_topic(self):
        d = make_director()
        topic = d.select_topic()
        d.topic_goal(topic)
        d.goal_manager.add_candidate.assert_called()

    def test_updates_usage_counters(self):
        d = make_director()
        d.track_action("web")
        usage = d.self_state.get("usage_today", {})
        self.assertEqual(usage.get("web_searches", 0), 1)

    def test_waits_when_many_web_searches(self):
        d = make_director()
        res = d.evaluate(
            asleep=False,
            available_ram_mb=4000,
            web_searches_today=30,
            llm_calls_today=0,
        )
        self.assertFalse(res["should_act"])
        self.assertIn(
            "много внешних действий",
            res["reason"].lower(),
        )

    def test_waits_when_many_llm_calls(self):
        d = make_director()
        res = d.evaluate(
            asleep=False,
            available_ram_mb=4000,
            web_searches_today=0,
            llm_calls_today=15,
        )
        self.assertFalse(res["should_act"])
        self.assertIn(
            "много внешних действий",
            res["reason"].lower(),
        )

    def test_marks_step_cooling(self):
        d = make_director()
        d.mark_acted()
        res = d.evaluate(asleep=False)
        self.assertFalse(res["should_act"])
        self.assertIn("кулдаун", res["reason"].lower())


if __name__ == "__main__":
    unittest.main()