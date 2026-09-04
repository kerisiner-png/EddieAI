from memory.events import Event


class SharedLife:
    SYSTEM_PROMPT = (
        "Ты — EddieAI. Определи, является ли этот момент значимым для совместной жизни "
        "с Эдди. Ответ: YES если это совместная активность (фильм, игра, музыка, проект, "
        "разговор, совместная работа) или значимый момент рядом. "
        "NO если это просто рабочий экран без совместного контекста. "
        "Формат: YES: [описание] или NO"
    )

    def __init__(self, model_orchestrator=None, memory=None, retrieval=None):
        self._orchestrator = model_orchestrator
        self._memory = memory
        self._retrieval = retrieval

    def observe(self, screen_description, eddie_present=True):
        if not eddie_present:
            return {"is_shared": False, "description": "", "activity_type": "none"}
        if self._orchestrator is None:
            return {"is_shared": False, "description": "", "activity_type": "none"}
        try:
            result = self._orchestrator.execute(
                system=self.SYSTEM_PROMPT,
                user=f"Скриншот: {screen_description}",
                task="conversation"
            )
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            is_shared = text.upper().startswith("YES")
            description = text.split(":", 1)[1].strip() if ":" in text else text
            activity_type = self._detect_activity_type(screen_description)
            if is_shared:
                self.record(description, activity_type, "neutral")
            return {"is_shared": is_shared, "description": description, "activity_type": activity_type}
        except Exception:
            return {"is_shared": False, "description": "", "activity_type": "none"}

    def record(self, content, activity_type="unknown", mood="neutral"):
        if self._memory is None:
            return
        event = Event.create(
            content=content,
            event_type="SHARED_EXPERIENCE",
            source_type="SHARED_EXPERIENCE",
            source=f"shared_life:{activity_type}",
        )
        self._memory.remember(event)

    def get_recent(self, limit=10):
        if self._retrieval is None:
            return []
        try:
            rows = self._retrieval.shared_events(limit=limit)
            return [{"content": r["content"], "activity_type": r.get("activity_type", ""),
                      "mood": r.get("mood", ""), "timestamp": r.get("timestamp", "")} for r in rows]
        except Exception:
            return []

    def build_feed(self, limit=5):
        recent = self.get_recent(limit=limit)
        if not recent:
            return "Совместный опыт: пока пусто."
        lines = []
        for r in recent:
            lines.append(f"- [{r['activity_type']}] {r['content']}")
        return "Совместный опыт:\n" + "\n".join(lines)

    def _detect_activity_type(self, screen_description):
        desc = screen_description.lower()
        if any(w in desc for w in ["youtube", "видео", "фильм", "кино", "video", "movie"]):
            return "video"
        if any(w in desc for w in ["spotify", "музыка", "music", "аудио"]):
            return "music"
        if any(w in desc for w in ["game", "игра", "steam", "blizzard"]):
            return "game"
        if any(w in desc for w in ["code", "код", "vscode", "pycharm", "git"]):
            return "coding"
        if any(w in desc for w in ["browser", "браузер", "chrome", "firefox"]):
            return "browsing"
        return "other"
