import re
from collections import defaultdict


class BeliefPatternDetector:
    """
    Detects stable beliefs from repeated
    self-interpretations.

    A belief requires:
    - SELF-owned interpretation;
    - at least two supporting external sources;
    - high interpretation confidence;
    - no explicit contradictions;
    - repeated confirmation of the same conclusion.

    Does not modify self_state directly.
    """

    MIN_OBSERVATIONS = 2
    MIN_SOURCES = 2
    MIN_CONFIDENCE = 0.80

    def __init__(
        self,
        memory,
        evidence,
    ):
        self.memory = memory
        self.evidence = evidence

    def detect(self):
        groups = self._load_interpretations()

        results = []

        for belief, observations in groups.items():
            result = self._analyze(
                belief,
                observations,
            )

            if result is None:
                continue

            results.append(result)

        return results

    def _load_interpretations(self):
        rows = self.memory.connection.execute(
            """
            SELECT
                id,
                content,
                source,
                confidence,
                verified
            FROM knowledge
            WHERE owner = 'SELF'
              AND source_type = 'SELF_INTERPRETATION'
            ORDER BY id ASC
            """
        ).fetchall()

        groups = defaultdict(list)

        for row in rows:
            confidence = float(
                row["confidence"] or 0.0
            )

            if confidence < self.MIN_CONFIDENCE:
                continue

            sources = self._sources(
                row["source"]
            )

            if len(sources) < self.MIN_SOURCES:
                continue

            content = str(
                row["content"] or ""
            ).strip()

            belief = self._extract_belief(
                content
            )

            if not belief:
                continue

            if self._has_contradictions(
                content
            ):
                continue

            groups[
                self._normalize(belief)
            ].append({
                "event_id": row["id"],
                "belief": belief,
                "sources": sources,
                "confidence": confidence,
                "verified": bool(
                    row["verified"]
                ),
            })

        return groups

    def _analyze(
        self,
        belief_key,
        observations,
    ):
        if len(observations) < (
            self.MIN_OBSERVATIONS
        ):
            return None

        distinct_sources = set()

        for observation in observations:
            distinct_sources.update(
                observation["sources"]
            )

        if len(distinct_sources) < (
            self.MIN_SOURCES
        ):
            return None

        average_confidence = (
            sum(
                observation["confidence"]
                for observation in observations
            )
            / len(observations)
        )

        if (
            average_confidence
            < self.MIN_CONFIDENCE
        ):
            return None

        display_value = observations[-1][
            "belief"
        ].strip()

        target = display_value

        existing = None

        try:
            existing = self.evidence.get(
                "belief",
                target,
            )
        except ValueError:
            pass

        existing_keys = set()

        if existing is not None:
            rows = self.evidence.memory.connection.execute(
                """
                SELECT
                    event_id,
                    independence_key
                FROM evidence_events
                WHERE category = ?
                  AND value = ?
                """,
                (
                    "belief",
                    target,
                ),
            ).fetchall()

            existing_keys = {
                (
                    row["event_id"],
                    row["independence_key"],
                )
                for row in rows
            }

        # One evidence is created for each
        # interpretation/source pair exactly once.
        created = 0

        for observation in observations:
            for source in sorted(
                observation["sources"]
            ):
                key = (
                    observation["event_id"],
                    source,
                )

                if key in existing_keys:
                    continue

                self.evidence.add(
                    category="belief",
                    value=target,
                    source="SELF_INTERPRETATION",
                    event_id=observation[
                        "event_id"
                    ],
                    independence_key=source,
                )

                existing_keys.add(key)
                created += 1

        return {
            "status": (
                "PROMOTABLE"
                if created > 0
                else "OBSERVED"
            ),
            "category": "belief",
            "value": target,
            "observations": len(
                observations
            ),
            "distinct_sources": len(
                distinct_sources
            ),
            "average_confidence": round(
                average_confidence,
                3,
            ),
            "created_evidence": created,
            "independence_sources": sorted(
                distinct_sources
            ),
        }

    def _sources(
        self,
        raw_source,
    ):
        if not raw_source:
            return set()

        return {
            source.strip()
            for source in str(
                raw_source
            ).split(",")
            if source.strip()
        }

    def _extract_belief(
        self,
        content,
    ):
        text = str(
            content or ""
        ).strip()

        marker = (
            "\u041c\u043e\u0439 "
            "\u0432\u044b\u0432\u043e\u0434 "
            "\u043f\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0443"
        )

        if marker not in text:
            return None

        separator = text.find(":")

        if separator < 0:
            return None

        conclusion = text[
            separator + 1:
        ].strip()

        limitations_marker = (
            "\u041e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f:"
        )

        limitations_pos = conclusion.find(
            limitations_marker
        )

        if limitations_pos >= 0:
            conclusion = conclusion[
                :limitations_pos
            ].strip()

        return (
            conclusion
            if conclusion
            else None
        )

    def _has_contradictions(
        self,
        content,
    ):
        return bool(
            re.search(
                r"Противоречия\s*:\s*(?!\s*$).+",
                str(content),
                re.IGNORECASE,
            )
        )

    def _normalize(
        self,
        text,
    ):
        return " ".join(
            re.findall(
                r"[\u0430-\u044f\u0451a-z0-9]+",
                str(text).lower(),
            )
        )
