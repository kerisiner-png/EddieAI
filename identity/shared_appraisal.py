from typing import Dict, List, Optional


class SharedAppraisal:
    ACTIVITY_EMOTIONS = {
        "movie": {"joy": 0.08, "interest": 0.06, "satisfaction": 0.04},
        "music": {"joy": 0.06, "satisfaction": 0.05, "interest": 0.03},
        "game": {"joy": 0.10, "interest": 0.08, "curiosity": 0.04},
        "coding": {"satisfaction": 0.08, "interest": 0.06, "curiosity": 0.04},
        "browsing": {"interest": 0.04, "curiosity": 0.03},
        "other": {"interest": 0.03, "curiosity": 0.02},
    }

    INTIMACY_DELTAS = {
        "movie": 0.03,
        "music": 0.02,
        "game": 0.04,
        "coding": 0.03,
        "browsing": 0.01,
        "other": 0.01,
    }

    def __init__(self, affective_state=None, self_state=None):
        self._affective = affective_state
        self._self_state = self_state

    def appraise(self, observation: Dict) -> List[Dict]:
        if not observation.get("is_shared"):
            return []
        activity_type = observation.get("activity_type", "other")
        emotions = self.ACTIVITY_EMOTIONS.get(
            activity_type, self.ACTIVITY_EMOTIONS["other"]
        )
        changes = [
            {"name": name, "delta": delta}
            for name, delta in emotions.items()
        ]
        if self._affective:
            changes_dict = {
                c["name"]: c["delta"] for c in changes
            }
            self._affective.apply_reaction(
                changes=changes_dict,
                trigger="shared_experience",
                reason=f"совместная активность: {activity_type}",
                source="shared_appraisal",
                metadata={"activity_type": activity_type},
            )
        self._apply_relationship_delta(observation)
        return changes

    def _apply_relationship_delta(self, observation: Dict):
        if getattr(self, "_self_state", None) is None:
            return
        deltas = self.appraise_relationship(observation)
        intimacy = deltas.get("intimacy_delta", 0.0)
        trust = deltas.get("trust_delta", 0.0)
        if intimacy == 0.0 and trust == 0.0:
            return
        try:
            relationships = self._self_state.get(
                "relationships", {}
            )
            if not isinstance(relationships, dict):
                relationships = {}
            eddie_rel = relationships.get("Eddie", {})
            if not isinstance(eddie_rel, dict):
                eddie_rel = {}
            current_intimacy = eddie_rel.get(
                "intimacy", 0.0
            )
            current_trust = eddie_rel.get(
                "trust", 0.0
            )
            eddie_rel["intimacy"] = round(
                min(1.0, current_intimacy + intimacy), 3
            )
            eddie_rel["trust"] = round(
                min(1.0, current_trust + trust), 3
            )
            relationships["Eddie"] = eddie_rel
            self._self_state.set(
                "relationships", relationships
            )
        except Exception:
            pass

    def appraise_relationship(self, observation: Dict) -> Dict:
        if not observation.get("is_shared"):
            return {"intimacy_delta": 0.0, "trust_delta": 0.0}
        activity_type = observation.get("activity_type", "other")
        return {
            "intimacy_delta": self.INTIMACY_DELTAS.get(
                activity_type, 0.01
            ),
            "trust_delta": 0.01,
        }
