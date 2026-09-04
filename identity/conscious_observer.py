import json
from datetime import datetime, timezone

from memory.events import Event


AFFECT_MARKERS = (
    "настроение",
    "настроени",
    "эмоции",
    "эмоци",
    "чувства",
    "чувств",
    "аффект",
)

CAPABILITY_MARKERS = (
    "умею",
    "умеешь",
    "могу",
    "способности",
    "способност",
    "возможности",
    "возможност",
)

LIMITATION_MARKERS = (
    "ограничения",
    "ограничени",
    "не могу",
    "слабости",
    "слабост",
    "не умею",
    "чего мне не хватает",
)

WORK_MARKERS = (
    "что я дела",
    "недавн",
    "дневник",
    "работа",
    "проект",
    "чем я занят",
)

FOCUS_MARKERS = (
    "цели",
    "целях",
    "фокус",
    "на чём я",
    "план",
    "задачи",
)


class ConsciousObserver:
    """
    Осознанное самонаблюдение EddieAI.

    Собирает в `self_state.conscious_state`
    единый снимок осознания себя:
    - affect: аффективное состояние;
    - self_model: самооценка (модель себя);
    - recent_diary: последняя запись дневника;
    - recent_feed: недавние события жизни;
    - active_focus: активные цели и исследование.

    `ask(question)` — осознанный запрос к себе,
    возвращающий релевантную часть состояния.

    История самонаблюдений пишется в память как
    CONSCIOUS_OBSERVATION-события от имени SELF.

    Детерминированно, без LLM.
    """

    HISTORY_EVENT_TYPE = "CONSCIOUS_OBSERVATION"

    def __init__(
        self,
        self_state,
        agent=None,
        db_path=None,
        memory=None,
    ):
        self.self_state = self_state
        self.agent = agent
        self.db_path = db_path
        self.memory = memory
        self._history = []

    def observe(self):
        snapshot = {
            "observed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "affect": self._affect(),
            "self_model": self._self_model(),
            "recent_diary": self._recent_diary(),
            "recent_feed": self._recent_feed(),
            "active_focus": self._active_focus(),
        }

        self.self_state.set(
            "conscious_state",
            snapshot,
        )

        self._record_history(snapshot)

        return snapshot

    def ask(self, question):
        question = (question or "").strip().lower()

        if not question:
            return self.render_consciousness()

        marker = self._match_marker(question)

        if marker == "affect":
            return self._projection(
                "МОЁ АФФЕКТИВНОЕ СОСТОЯНИЕ",
                ["affect"],
            )

        if marker == "capability":
            return self._projection(
                "МОИ СПОСОБНОСТИ",
                ["self_model"],
            )

        if marker == "limitation":
            return self._projection(
                "МОИ ОГРАНИЧЕНИЯ",
                ["self_model"],
            )

        if marker == "work":
            return self._projection(
                "МОЯ НЕДАВНЯЯ РАБОТА",
                [
                    "recent_diary",
                    "recent_feed",
                    "active_focus",
                ],
            )

        if marker == "focus":
            return self._projection(
                "МОЙ АКТИВНЫЙ ФОКУС",
                ["active_focus"],
            )

        return self.render_consciousness()

    def snapshot(self):
        state = self.self_state.get(
            "conscious_state",
            None,
        )

        if state is None:
            return {}

        return state

    def render_consciousness(self):
        state = self.snapshot()

        affect = state.get(
            "affect",
            {},
        )

        affect_text = (
            affect
            if isinstance(affect, dict)
            else {}
        )

        self_model = state.get(
            "self_model",
            {},
        )

        caps = [
            item.get("name", "?")
            for item in (
                self_model.get(
                    "capabilities",
                    [],
                )
                if isinstance(
                    self_model,
                    dict,
                )
                else []
            )
        ]

        lines = [
            "МОЁ СОСТОЯНИЕ СОЗНАНИЯ",
            (
                "Аффект: "
                f"{affect_text or 'нет данных'}"
            ),
            (
                "Самооценка (способности): "
                f"{', '.join(caps) or 'нет данных'}"
            ),
            (
                "Последняя запись дневника: "
                f"{state.get('recent_diary', '') or 'нет'}"
            ),
            (
                "Недавние события: "
                f"{state.get('recent_feed', '') or 'нет'}"
            ),
            (
                "Активный фокус: "
                f"{state.get('active_focus', {}) or 'нет'}"
            ),
        ]

        return "\n".join(lines)

    def history(self, limit=10):
        items = list(reversed(self._history))

        return items[:limit]

    def _projection(
        self,
        title,
        keys,
    ):
        state = self.snapshot()

        parts = [title]

        for key in keys:
            value = state.get(key)

            if value in (
                None,
                "",
                {},
                [],
            ):
                continue

            parts.append(
                f"{key}: {value}"
            )

        if len(parts) == 1:
            parts.append(
                "пока нет данных об этом аспекте"
            )

        return "\n".join(parts)

    def _match_marker(self, question):
        for marker in LIMITATION_MARKERS:
            if marker in question:
                return "limitation"

        for marker in CAPABILITY_MARKERS:
            if marker in question:
                return "capability"

        for marker in AFFECT_MARKERS:
            if marker in question:
                return "affect"

        for marker in WORK_MARKERS:
            if marker in question:
                return "work"

        for marker in FOCUS_MARKERS:
            if marker in question:
                return "focus"

        return None

    def _affect(self):
        if self.agent is None:
            return {}

        affective = getattr(
            self.agent,
            "affective_state",
            None,
        )

        if affective is None:
            return {}

        try:
            value = affective.snapshot()
        except Exception:
            value = {}

        if not isinstance(value, dict):
            return {}

        return value

    def _self_model(self):
        value = self.self_state.get(
            "self_model",
            {},
        )

        if not isinstance(value, dict):
            return {}

        return value

    def _recent_diary(self):
        db_path = self._db_path()

        if not db_path:
            return ""

        try:
            from identity.personal_diary import (
                PersonalDiary,
            )

            diary = PersonalDiary(db_path)

            recent = diary.recent(1)

            if not recent:
                return ""

            return recent[0].get(
                "entry",
                "",
            )

        except Exception:
            return ""

    def _recent_feed(self):
        memory = self._memory()

        if memory is None:
            return ""

        feed = getattr(
            memory,
            "recent_life_feed",
            None,
        )

        if feed is None:
            return ""

        try:
            value = feed(limit=3)
        except Exception:
            value = ""

        if not isinstance(value, str):
            return ""

        return value

    def _active_focus(self):
        goals = self._goals()

        research = self.self_state.get(
            "current_research",
            {},
        )

        if isinstance(
            research,
            dict,
        ):
            research_topic = research.get(
                "topic",
                "",
            )
        else:
            research_topic = ""

        return {
            "goals": goals,
            "research": research_topic,
        }

    def _goals(self):
        if self.agent is None:
            return []

        manager = getattr(
            self.agent,
            "goal_manager",
            None,
        )

        if manager is None:
            return []

        active = getattr(
            manager,
            "active",
            None,
        )

        if active is None:
            return []

        try:
            items = active()
        except Exception:
            items = []

        result = []

        for item in items:
            if isinstance(item, str):
                value = item
            else:
                value = getattr(
                    item,
                    "value",
                    None,
                )

                if value is None:
                    value = (
                        item.get("value")
                        if isinstance(item, dict)
                        else None
                    )

            if value:
                result.append(str(value))

        return result

    def _memory(self):
        if self.memory is not None:
            return self.memory

        if self.agent is not None:
            return getattr(
                self.agent,
                "memory",
                None,
            )

        return None

    def _db_path(self):
        if self.db_path:
            return str(self.db_path)

        memory = self._memory()

        if memory is not None:
            value = getattr(
                memory,
                "db_path",
                None,
            )

            if value:
                return str(value)

        return None

    def _record_history(
        self,
        snapshot,
    ):
        self._history.append(snapshot)

        memory = self._memory()

        if memory is None:
            return

        remember = getattr(
            memory,
            "remember",
            None,
        )

        if remember is None:
            return

        try:
            remember(
                Event.create(
                    content=json.dumps(
                        snapshot,
                        ensure_ascii=False,
                    ),
                    event_type=(
                        self.HISTORY_EVENT_TYPE
                    ),
                    source_type="SELF",
                    source="SELF",
                    personal_experience=True,
                    confidence=0.8,
                    verified=False,
                )
            )
        except Exception:
            pass


def conscious_state_text(self_state):
    """
    Read-only проекция осознанного самонаблюдения
    для промптов. Возвращает '', если наблюдение
    ещё не проводилось.
    """
    state = self_state.get(
        "conscious_state",
        None,
    )

    if state is None:
        return ""

    return ConsciousObserver(self_state).render_consciousness()


def conscious_state_summary_text(self_state):
    """
    Однострочная проекция осознанного самонаблюдения
    для компактных промптов (bullets).
    """
    state = self_state.get(
        "conscious_state",
        None,
    )

    if state is None:
        return ""

    affect = state.get(
        "affect",
        {},
    )

    if not isinstance(affect, dict):
        affect = {}

    self_model = state.get(
        "self_model",
        {},
    )

    caps = [
        item.get("name", "?")
        for item in (
            self_model.get(
                "capabilities",
                [],
            )
            if isinstance(
                self_model,
                dict,
            )
            else []
        )
    ]

    active_focus = state.get(
        "active_focus",
        {},
    )

    if not isinstance(
        active_focus,
        dict,
    ):
        active_focus = {}

    focus_goals = active_focus.get(
        "goals",
        [],
    )

    if not isinstance(
        focus_goals,
        list,
    ):
        focus_goals = []

    return (
        f"аффект: {affect}; "
        "способности: "
        f"{', '.join(caps) or 'нет данных'}; "
        "активный фокус: "
        f"{', '.join(focus_goals) or 'нет активных целей'}"
    )
