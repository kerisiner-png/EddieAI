from datetime import datetime, timezone
from typing import Dict, Optional


ACTIVITY_TYPES = (
    "movie",
    "music",
    "game",
    "coding",
    "reading",
    "conversation",
    "other",
)

MOOD_ACTIVITY_MAP = {
    "joy": ["movie", "music", "game"],
    "curiosity": ["reading", "coding", "game"],
    "interest": ["coding", "reading", "movie"],
    "satisfaction": ["coding", "conversation"],
    "calm": ["music", "reading", "movie"],
    "low": ["movie", "music"],
}

INTEREST_ACTIVITY_MAP = {
    "астрофизика": "reading",
    "космос": "reading",
    "наука": "reading",
    "технологии": "coding",
    "программирование": "coding",
    "музыка": "music",
    "фильмы": "movie",
    "игры": "game",
}


class SharedActivityManager:
    def __init__(self, self_state=None):
        self._self_state = self_state
        self._current = self._load()

    def _load(self):
        if self._self_state is None:
            return None
        data = self._self_state.get(
            "current_shared_activity"
        )
        if data and isinstance(data, dict) and data.get(
            "status"
        ) == "active":
            return data
        return None

    def _save(self):
        if self._self_state is None:
            return
        if self._current is not None:
            self._self_state["current_shared_activity"] = (
                self._current
            )
        else:
            if "current_shared_activity" in self._self_state:
                del self._self_state[
                    "current_shared_activity"
                ]

    def start_activity(
        self,
        activity_type,
        title="",
        source="chat",
    ):
        if activity_type not in ACTIVITY_TYPES:
            activity_type = "other"
        now = datetime.now(timezone.utc).isoformat()
        self._current = {
            "type": activity_type,
            "title": title,
            "status": "active",
            "started_at": now,
            "source": source,
        }
        self._save()
        return self._current

    def stop_activity(self, reason="user"):
        if self._current is None:
            return None
        activity = self._current.copy()
        now = datetime.now(timezone.utc).isoformat()
        activity["status"] = "ended"
        activity["ended_at"] = now
        activity["end_reason"] = reason
        self._current = None
        self._save()
        return activity

    def get_current(self):
        return self._current

    def is_active(self):
        return (
            self._current is not None
            and self._current.get("status") == "active"
        )

    def activity_summary(self):
        if not self.is_active():
            return "Совместная активность: нет."
        c = self._current
        parts = [
            c.get("type", "?"),
        ]
        if c.get("title"):
            parts.append(c["title"])
        return "Совместная активность: " + " — ".join(
            parts
        )

    def suggest_activity(
        self,
        affective_state=None,
        interests=None,
        recent_history=None,
    ):
        candidates = {}
        if affective_state:
            emotions = getattr(
                affective_state, "emotions", {}
            )
            if isinstance(emotions, dict):
                for emotion, value in emotions.items():
                    if value > 0.3 and emotion in MOOD_ACTIVITY_MAP:
                        for act in MOOD_ACTIVITY_MAP[emotion]:
                            candidates[act] = (
                                candidates.get(act, 0)
                                + value
                            )
        if interests:
            for interest in interests:
                name = (
                    interest.get("name", "")
                    if isinstance(interest, dict)
                    else str(interest)
                )
                lower = name.lower()
                for keyword, act in INTEREST_ACTIVITY_MAP.items():
                    if keyword in lower:
                        candidates[act] = (
                            candidates.get(act, 0) + 0.2
                        )
        if recent_history:
            seen_types = set()
            for event in recent_history:
                etype = (
                    event.get("activity_type", "")
                    if isinstance(event, dict)
                    else ""
                )
                if etype:
                    seen_types.add(etype)
            for act in seen_types:
                if act in candidates:
                    candidates[act] *= 0.7
        if not candidates:
            return None
        best = max(candidates, key=candidates.get)
        return {
            "activity_type": best,
            "reason_score": round(candidates[best], 2),
        }
