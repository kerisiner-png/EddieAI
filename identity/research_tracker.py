from datetime import datetime, timezone


MIN_SOURCES_THRESHOLD = 4


def current_research_text(self_state):
    """
    Читаемая сводка текущего исследования из self_state,
    без изменения состояния (для промптов).
    """
    current = self_state.get("current_research")
    if not current:
        return ""
    parts = [
        f"тема: {current.get('topic')}"
    ]
    sources = current.get("sources")
    steps = current.get("steps")
    notes = current.get("notes") or []
    if sources:
        parts.append(
            f"источников: {sources}"
        )
    if steps:
        parts.append(
            f"шагов: {steps}"
        )
    if notes:
        parts.append(
            f"заметок: {len(notes)}"
        )
    return "; ".join(parts)


class ResearchTracker:
    """
    Ведёт персистентное текущее исследование (А-2/А-1).

    Хранит тему, накопленные источники/шаги, дневник заметок.
    Определяет, углубляться ли дальше (глубина < порога) или
    завершить и перейти к следующей теме.
    """

    def __init__(self, self_state):
        self.self_state = self_state
        if self.self_state.get("current_research") is None:
            self.self_state.set("current_research", None)
        if self.self_state.get("research_history") is None:
            self.self_state.set("research_history", [])

    def current(self):
        return self.self_state.get("current_research")

    def history(self):
        return self.self_state.get("research_history", [])

    def start(self, topic, source="self"):
        current = self.current()
        if current is not None and current["topic"] == topic:
            return current
        research = {
            "topic": topic,
            "source": source,
            "sources": 0,
            "steps": 0,
            "notes": [],
            "updated_at": self._now(),
        }
        self.self_state.set("current_research", research)
        return research

    def record_findings(
        self,
        num_sources=0,
        num_steps=0,
    ):
        current = self.current()
        if current is None:
            return None
        current["sources"] += max(
            0, int(num_sources)
        )
        current["steps"] += max(
            0, int(num_steps)
        )
        current["updated_at"] = self._now()
        self._save(current)
        return current

    def add_note(self, text, finding_type="note"):
        current = self.current()
        if current is None:
            return None
        current["notes"].append({
            "text": text,
            "type": finding_type,
            "at": self._now(),
        })
        self._save(current)
        return current

    def should_deepen(self):
        current = self.current()
        if current is None:
            return False
        return (
            current["sources"]
            < MIN_SOURCES_THRESHOLD
        )

    def resume_candidate(self):
        current = self.current()
        if current is None:
            return None
        if self.should_deepen():
            return current
        return None

    def complete(self):
        current = self.current()
        if current is None:
            return None
        history = self.history()
        history.append(current)
        self.self_state.set(
            "research_history",
            history,
        )
        self.self_state.set(
            "current_research",
            None,
        )
        return current

    def progress_text(self):
        current = self.current()
        if current is None:
            return ""
        parts = [
            f"тема: {current['topic']}"
        ]
        if current["sources"]:
            parts.append(
                f"источников: {current['sources']}"
            )
        if current["steps"]:
            parts.append(
                f"шагов: {current['steps']}"
            )
        notes = current.get("notes") or []
        if notes:
            parts.append(
                f"заметок: {len(notes)}"
            )
        return "; ".join(parts)

    def _save(self, research):
        self.self_state.set(
            "current_research",
            research,
        )

    def _now(self):
        return datetime.now(
            timezone.utc
        ).isoformat()
