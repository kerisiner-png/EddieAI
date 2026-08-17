import re


class BehaviorPatternDetector:
    """
    ???? ?????????? ???????? ???????????? ?????????.
    """

    MIN_OBSERVATIONS = 3

    STOP_WORDS = {
        "\u0438\u0437\u0443\u0447\u0438\u0442\u044c",
        "\u0438\u0437\u0443\u0447\u0430\u0442\u044c",
        "\u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u044c",
        "\u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435",
        "\u0442\u0435\u043c\u0443",
        "\u0442\u0435\u043c\u0430",
        "\u043f\u043e",
        "\u0446\u0435\u043b\u0438",
        "\u0446\u0435\u043b\u044c",
        "\u043f\u0440\u043e\u0432\u0435\u0441\u0442\u0438",
        "\u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c",
        "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b",
        "\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
        "\u0434\u043b\u044f",
        "\u043f\u0440\u043e",
        "\u043e\u0431",
        "\u043e\u0431\u0443\u0447\u0435\u043d\u0438\u0435",
    }

    def __init__(
        self,
        memory,
        evidence,
    ):
        self.memory = memory
        self.evidence = evidence

    def observe(
        self,
        limit: int = 50,
    ):
        rows = self.memory.connection.execute("""
            SELECT
                content,
                source,
                confidence
            FROM events
            WHERE event_type = 'SELF_EXPERIENCE'
              AND personal_experience = 1
            ORDER BY id DESC
            LIMIT ?
        """, (
            limit,
        )).fetchall()

        observations = []

        for row in rows:
            topic = self._extract_topic(
                row["content"]
            )

            if topic is None:
                continue

            observations.append(topic)

        counts = {}

        for topic in observations:
            counts[topic] = (
                counts.get(topic, 0) + 1
            )

        created = []

        for topic, count in counts.items():
            if count < self.MIN_OBSERVATIONS:
                continue

            try:
                existing = self.evidence.get(
                    "interest",
                    topic,
                )
            except ValueError:
                existing = None

            existing_count = (
                existing.count
                if existing is not None
                else 0
            )

            if existing_count >= count:
                continue

            record = self.evidence.add(
                category="interest",
                value=topic,
                source="SELF_OBSERVATION",
            )

            created.append({
                "status": "OBSERVED",
                "field": "interest",
                "value": topic,
                "observations": count,
                "evidence": record,
            })

        return created

    def _extract_topic(
        self,
        content: str,
    ):
        if not content:
            return None

        text = str(content).strip()

        # The experience format is:
        # ... action 'TARGET' through TOOL ...
        marker = "action '"

        start = text.lower().find(
            marker
        )

        if start < 0:
            # Russian fallback:
            # ... action 'TARGET' ...
            marker = (
                chr(0x0434)
                + chr(0x0435)
                + chr(0x0439)
                + chr(0x0441)
                + chr(0x0442)
                + chr(0x0432)
                + chr(0x0438)
                + chr(0x0435)
                + " '"
            )

            start = text.find(marker)

        if start < 0:
            return None

        start += len(marker)

        end_markers = [
            "' through ",
            "' "
            + chr(0x0447)
            + chr(0x0435)
            + chr(0x0440)
            + chr(0x0435)
            + chr(0x0437)
            + " ",
        ]

        end = -1

        for end_marker in end_markers:
            candidate = text.find(
                end_marker,
                start,
            )

            if candidate >= 0:
                end = candidate
                break

        if end < 0:
            return None

        action = text[
            start:end
        ].strip()

        if not action:
            return None

        # Remove common semantic prefixes without
        # requiring the Russian text to be encoded
        # in the source file.
        prefix_phrases = [
            "research:",
            "research",
            "study:",
            "study",
            "find information:",
            "find information",
            "analyze:",
            "analyze",
        ]

        lowered = action.lower()

        for prefix in prefix_phrases:
            if lowered.startswith(prefix):
                action = action[
                    len(prefix):
                ].strip()
                break

        # Russian prefixes are handled by their
        # structural form if present.
        russian_prefixes = [
            chr(0x041f)
            + chr(0x0440)
            + chr(0x043e)
            + chr(0x0432)
            + chr(0x0435)
            + chr(0x0441)
            + chr(0x0442)
            + chr(0x0438)
            + " "
            + chr(0x0438)
            + chr(0x0441)
            + chr(0x0441)
            + chr(0x043b)
            + chr(0x0435)
            + chr(0x0434)
            + chr(0x043e)
            + chr(0x0432)
            + chr(0x0430)
            + chr(0x043d)
            + chr(0x0438)
            + chr(0x0435)
            + ":",
        ]

        for prefix in russian_prefixes:
            if action.lower().startswith(
                prefix.lower()
            ):
                action = action[
                    len(prefix):
                ].strip()
                break

        tokens = self._tokens(
            action
        )

        if not tokens:
            return None

        meaningful = [
            token
            for token in tokens
            if token not in self.STOP_WORDS
        ]

        if not meaningful:
            return None

        return " ".join(
            meaningful[:4]
        )

    def _tokens(
        self,
        text: str,
    ):
        return re.findall(
            r"[?-??a-z0-9]+",
            text.lower(),
        )
