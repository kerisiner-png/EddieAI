from collections import defaultdict
import json


class ActionPreferenceDetector:
    """
    Detects stable preferences from comparable
    ACTION_CHOICE history.

    Each independent ACTION_CHOICE event can produce
    at most one preference evidence record.

    Detector does not modify self_state.
    """

    MIN_CHOICES = 6
    MIN_SHARE = 0.75

    def __init__(
        self,
        memory,
        evidence,
    ):
        self.memory = memory
        self.evidence = evidence

    def detect(self):
        groups = self._load_choice_groups()

        results = []

        for signature, choices in groups.items():
            result = self._analyze_group(
                signature,
                choices,
            )

            if result is None:
                continue

            results.append(result)

        return results

    def _load_choice_groups(self):
        rows = self.memory.connection.execute(
            """
            SELECT
                id,
                content
            FROM events
            WHERE event_type = 'ACTION_CHOICE'
              AND source_type = 'SELF_ACTION'
              AND personal_experience = 1
            ORDER BY id ASC
            """
        ).fetchall()

        groups = defaultdict(list)

        for row in rows:
            try:
                payload = json.loads(
                    row["content"]
                )
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                continue

            if not isinstance(
                payload,
                dict,
            ):
                continue

            choice = payload.get(
                "choice"
            )

            if not isinstance(
                choice,
                dict,
            ):
                continue

            options = choice.get(
                "options",
                []
            )

            selected = choice.get(
                "selected"
            )

            if not isinstance(
                options,
                list,
            ):
                continue

            if not isinstance(
                selected,
                str,
            ):
                continue

            normalized_options = sorted(
                {
                    str(option).strip()
                    for option in options
                    if str(option).strip()
                }
            )

            if len(
                normalized_options
            ) < 2:
                continue

            if (
                selected
                not in normalized_options
            ):
                continue

            context_type = str(
                choice.get(
                    "context_type",
                    "unknown",
                )
            ).strip() or "unknown"

            signature = (
                context_type,
                tuple(normalized_options),
            )

            groups[signature].append({
                "event_id": row["id"],
                "context_type": context_type,
                "options": normalized_options,
                "selected": selected,
            })

        return groups

    def _analyze_group(
        self,
        signature,
        choices,
    ):
        total = len(choices)

        if total < self.MIN_CHOICES:
            return None

        context_type, signature_options = (
            signature
        )

        counts = {
            option: 0
            for option in signature_options
        }

        for choice in choices:
            selected = choice["selected"]

            if selected in counts:
                counts[selected] += 1

        ranked = sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )

        winner, winner_count = ranked[0]

        loser_count = sum(
            count
            for option, count
            in counts.items()
            if option != winner
        )

        if winner_count <= 0:
            return None

        share = (
            winner_count / total
        )

        if share < self.MIN_SHARE:
            return None

        # Do not call something a preference
        # when the alternatives were never actually
        # compared.
        if loser_count <= 0:
            return None

        target = (
            f"{context_type}:"
            f"action_method:{winner}"
        )

        existing_event_ids = {
            row["event_id"]
            for row in self.memory.connection.execute(
                """
                SELECT event_id
                FROM evidence_events
                WHERE category = ?
                  AND value = ?
                  AND source = 'ACTION_CHOICE'
                  AND event_id IS NOT NULL
                """,
                (
                    "preference",
                    target,
                ),
            ).fetchall()
        }

        created = 0

        for choice in choices:
            event_id = choice["event_id"]

            if event_id in existing_event_ids:
                continue

            # Only the winner's actual choices become
            # preference evidence.
            if (
                choice["selected"]
                != winner
            ):
                continue

            self.evidence.add(
                category="preference",
                value=target,
                source="ACTION_CHOICE",
                event_id=event_id,
            )

            existing_event_ids.add(
                event_id
            )

            created += 1

        return {
            "status": (
                "PROMOTABLE"
                if created > 0
                else "OBSERVED"
            ),
            "category": "preference",
            "value": target,
            "selected": winner,
            "counts": counts,
            "total_choices": total,
            "share": round(
                share,
                3,
            ),
            "created_evidence": created,
        }
