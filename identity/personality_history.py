from datetime import datetime, timezone


class PersonalityHistory:
    """
    Persistent history of personality trait changes.
    """

    def __init__(self, memory):
        self.memory = memory

    def record(
        self,
        field,
        value,
        event_type,
        status_before=None,
        status_after=None,
        strength_before=None,
        strength_after=None,
        confidence_before=None,
        confidence_after=None,
        evidence_count=None,
        contradictions=None,
        reason=None,
    ):
        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        self.memory.connection.execute(
            """
            INSERT INTO personality_history (
                field,
                value,
                event_type,
                status_before,
                status_after,
                strength_before,
                strength_after,
                confidence_before,
                confidence_after,
                evidence_count,
                contradictions,
                reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                field,
                value,
                event_type,
                status_before,
                status_after,
                strength_before,
                strength_after,
                confidence_before,
                confidence_after,
                evidence_count,
                contradictions,
                reason,
                timestamp,
            ),
        )

        self.memory.connection.commit()

    def recent(
        self,
        limit=50,
    ):
        cursor = self.memory.connection.execute(
            """
            SELECT *
            FROM personality_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        return cursor.fetchall()

    def for_trait(
        self,
        field,
        value,
        limit=100,
    ):
        cursor = self.memory.connection.execute(
            """
            SELECT *
            FROM personality_history
            WHERE field = ?
              AND value = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                field,
                value,
                limit,
            ),
        )

        return cursor.fetchall()


    def trait_summary(
        self,
        field,
        value,
        limit=100,
    ):
        rows = self.for_trait(
            field,
            value,
            limit=limit,
        )

        if not rows:
            return None

        first = rows[0]
        last = rows[-1]

        event_types = [
            row["event_type"]
            for row in rows
        ]

        strengths = [
            row["strength_after"]
            for row in rows
            if row["strength_after"] is not None
        ]

        confidences = [
            row["confidence_after"]
            for row in rows
            if row["confidence_after"] is not None
        ]

        return {
            "field": field,
            "value": value,
            "first_seen": first["created_at"],
            "last_changed": last["created_at"],
            "initial_status": first["status_after"],
            "current_status": last["status_after"],
            "initial_strength": (
                first["strength_after"]
            ),
            "current_strength": (
                last["strength_after"]
            ),
            "initial_confidence": (
                first["confidence_after"]
            ),
            "current_confidence": (
                last["confidence_after"]
            ),
            "max_strength": (
                max(strengths)
                if strengths
                else None
            ),
            "min_strength": (
                min(strengths)
                if strengths
                else None
            ),
            "max_confidence": (
                max(confidences)
                if confidences
                else None
            ),
            "event_count": len(rows),
            "event_types": event_types,
            "reinforcements": event_types.count(
                "REINFORCED"
            ),
            "contradictions": event_types.count(
                "CONTRADICTED"
            ),
            "decays": event_types.count(
                "DECAYED"
            ),
            "evidence_count": (
                last["evidence_count"]
            ),
        }

    def summary(
        self,
        field=None,
        value=None,
        limit=100,
    ):
        if field is not None and value is not None:
            rows = self.for_trait(
                field,
                value,
                limit=limit,
            )
        else:
            rows = self.recent(
                limit=limit
            )

        result = []

        for row in rows:
            result.append({
                "field": row["field"],
                "value": row["value"],
                "event_type": row["event_type"],
                "status_before": row["status_before"],
                "status_after": row["status_after"],
                "strength_before": row["strength_before"],
                "strength_after": row["strength_after"],
                "confidence_before": row["confidence_before"],
                "confidence_after": row["confidence_after"],
                "evidence_count": row["evidence_count"],
                "contradictions": row["contradictions"],
                "reason": row["reason"],
                "created_at": row["created_at"],
            })

        return result
