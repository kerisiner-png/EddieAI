from datetime import datetime, timedelta, timezone


class CuriosityDirector:
    def __init__(
        self,
        self_state,
        goal_manager,
        llm=None,
        min_interval_seconds=600,
    ):
        self.self_state = self_state
        self.goal_manager = goal_manager
        self.llm = llm
        self.min_interval_seconds = min_interval_seconds
        self.last_step_at = None
        self.last_topic_index = 0
        self._daily_topic_cache = None

        if self.self_state.get("usage_today") is None:
            self.self_state.set("usage_today", {})

        if self.self_state.get("world_description") is None:
            self.self_state.set("world_description", None)

    def _now(self):
        return datetime.now(timezone.utc)

    def _usage(self):
        usage = self.self_state.get("usage_today", {})
        if not isinstance(usage, dict):
            usage = {}
        return usage

    def mark_acted(self):
        self.last_step_at = self._now()

    def _in_cooldown(self) -> bool:
        if self.last_step_at is None:
            return False
        elapsed = (self._now() - self.last_step_at).total_seconds()
        return elapsed < self.min_interval_seconds

    def evaluate(self, asleep=False, available_ram_mb=None,
                 web_searches_today=0, llm_calls_today=0):
        if asleep:
            return {"should_act": False, "reason": "Личность спит."}
        if self._in_cooldown():
            return {"should_act": False, "reason": "Ещё в кулдауне любопытства."}
        if available_ram_mb is not None and available_ram_mb < 1024:
            return {"should_act": False, "reason": "Доступная память слишком мала для исследования."}
        if web_searches_today >= 25 or llm_calls_today >= 10:
            return {"should_act": False, "reason": "Сегодня уже было много внешних действий."}
        return {"should_act": True, "reason": "Есть что узнать."}

    def select_topic(self):
        interests = self.self_state.get("interests", []) or []
        if not interests:
            interests = ["устройство мира"]
        index = self.last_topic_index % len(interests)
        self.last_topic_index += 1
        topic = interests[index]
        return {
            "title": "Исследовать тему: " + topic,
            "topic": topic,
        }

    def topic_goal(self, topic):
        return self.goal_manager.add_candidate(
            value=topic["title"],
            motivation=0.6,
            priority=0.4,
            confidence=0.7,
            source="curiosity",
        )

    def track_action(self, kind):
        usage = self._usage()
        if kind == "web":
            usage["web_searches"] = int(usage.get("web_searches", 0)) + 1
        elif kind == "llm":
            usage["llm_calls"] = int(usage.get("llm_calls", 0)) + 1
        self.self_state.set("usage_today", usage)

    def daily_llm_topic(self, recent_life=""):
        now = self._now()
        if (
            getattr(self, "last_daily_llm_at", None) is not None
            and now - self.last_daily_llm_at
            < timedelta(hours=24)
        ):
            return self._daily_topic_cache

        if self.llm is None:
            self.last_daily_llm_at = now
            self._daily_topic_cache = None
            return None

        system = (
            "Ты — EddieAI, любопытная личность. "
            "Предложи ОДНУ тему для самостоятельного исследования. "
            "Формат: 'Тема: <текст>'."
        )
        user = (
            "Из своей жизни последнего времени:\n" + recent_life
        ) if recent_life else "Предложи тему по своим интересам."

        try:
            raw = self.llm.chat(
                system=system,
                user=user,
                options={"temperature": 0.9},
            )
        except Exception:
            raw = None

        self.last_daily_llm_at = now
        self._daily_topic_cache = None
        if raw:
            self._daily_topic_cache = {
                "title": f"Исследовать тему: {raw}",
                "topic": raw,
            }
            return self._daily_topic_cache
        return None