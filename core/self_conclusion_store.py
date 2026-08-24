from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SelfConclusionStore:
    """
    Коллекция устойчивых собственных выводов EddieAI.

    SelfConclusionState остаётся совместимым legacy-слоем.
    Store хранит несколько независимых выводов по topic.

    Структура:
        self_conclusions = {
            topic: {
                conclusion,
                predicates,
                confidence,
                basis,
                provenance,
                revision_count,
                revision_history,
                status,
                created_at,
                updated_at,
            }
        }
    """

    KEY = "self_conclusions"

    def __init__(self, self_state):
        self.self_state = self_state
        self._ensure()

    @staticmethod
    def _now() -> str:
        return (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    def _ensure(self):
        current = self.self_state.get(
            self.KEY
        )

        if isinstance(current, dict):
            return

        conclusions = {}

        legacy = self.self_state.get(
            "self_conclusion_state"
        )

        if isinstance(legacy, dict):
            conclusion = (
                legacy.get(
                    "current_conclusion"
                )
            )

            if conclusion:
                topic = (
                    legacy.get("topic")
                    or "self_concept"
                )

                now = (
                    legacy.get(
                        "last_updated"
                    )
                    or self._now()
                )

                conclusions[topic] = {
                    "topic": topic,
                    "language": legacy.get(
                        "language",
                        "unknown",
                    ),
                    "status": legacy.get(
                        "status",
                        "FORMED",
                    ),
                    "conclusion": conclusion,
                    "predicates": list(
                        legacy.get(
                            "predicates",
                            [],
                        )
                    ),
                    "confidence": float(
                        legacy.get(
                            "confidence",
                            0.0,
                        )
                    ),
                    "basis": list(
                        legacy.get(
                            "basis",
                            [],
                        )
                    ),
                    "provenance": list(
                        legacy.get(
                            "provenance",
                            [],
                        )
                    ),
                    "revision_count": int(
                        legacy.get(
                            "revision_count",
                            0,
                        )
                    ),
                    "revision_history": list(
                        legacy.get(
                            "revision_history",
                            [],
                        )
                    ),
                    "created_at": now,
                    "updated_at": now,
                }

        self.self_state.set(
            self.KEY,
            conclusions,
        )

    def _all(self) -> dict[str, dict[str, Any]]:
        value = self.self_state.get(
            self.KEY,
            {},
        )

        if not isinstance(value, dict):
            value = {}

        return value

    def list_conclusions(self) -> list[dict[str, Any]]:
        return list(
            self._all().values()
        )

    def get(
        self,
        topic: str,
    ) -> dict[str, Any] | None:
        return self._all().get(
            str(topic).strip()
        )

    def has(
        self,
        topic: str,
    ) -> bool:
        item = self.get(topic)

        return bool(
            item
            and item.get("status") == "FORMED"
            and str(
                item.get(
                    "conclusion",
                    "",
                )
            ).strip()
        )

    def save(
        self,
        *,
        topic: str,
        conclusion: str,
        confidence: float,
        basis: list[str],
        provenance: list[str],
        predicates: list[str],
        language: str = "unknown",
    ):
        topic = str(
            topic
        ).strip()

        conclusion = str(
            conclusion
        ).strip()

        if not topic:
            raise ValueError(
                "Conclusion topic cannot be empty."
            )

        if not conclusion:
            raise ValueError(
                "Conclusion cannot be empty."
            )

        all_conclusions = self._all()
        now = self._now()

        existing = all_conclusions.get(
            topic
        )

        if existing is None:
            all_conclusions[topic] = {
                "topic": topic,
                "language": language,
                "status": "FORMED",
                "conclusion": conclusion,
                "predicates": list(
                    predicates
                ),
                "confidence": max(
                    0.0,
                    min(
                        1.0,
                        float(
                            confidence
                        ),
                    ),
                ),
                "basis": list(
                    basis
                ),
                "provenance": list(
                    provenance
                ),
                "revision_count": 0,
                "revision_history": [],
                "created_at": now,
                "updated_at": now,
            }

        else:
            # Нормальное сохранение уже существующего
            # вывода не является revision.
            existing["status"] = "FORMED"
            existing["language"] = language
            existing["conclusion"] = conclusion
            existing["predicates"] = list(
                predicates
            )
            existing["confidence"] = max(
                0.0,
                min(
                    1.0,
                    float(
                        confidence
                    ),
                ),
            )
            existing["basis"] = list(
                basis
            )
            existing["provenance"] = list(
                provenance
            )
            existing["updated_at"] = now

        self.self_state.set(
            self.KEY,
            all_conclusions,
        )

        return all_conclusions[topic]

    def preserve(
        self,
        *,
        topic: str,
        confidence: float,
        basis: list[str],
        provenance: list[str],
        reason: str,
    ):
        existing = self.get(
            topic
        )

        if existing is None:
            return None

        existing["status"] = "FORMED"

        existing["confidence"] = max(
            0.0,
            min(
                1.0,
                float(
                    confidence
                ),
            ),
        )

        existing["basis"] = list(
            basis
        )

        existing["provenance"] = list(
            provenance
        )

        existing["last_reconsideration"] = {
            "decision": "PRESERVE",
            "reason": str(
                reason
            ),
            "checked_at": self._now(),
        }

        existing["updated_at"] = self._now()

        self.self_state.set(
            self.KEY,
            self._all(),
        )

        return existing

    def revise(
        self,
        *,
        topic: str,
        conclusion: str,
        confidence: float,
        basis: list[str],
        provenance: list[str],
        predicates: list[str],
        reason: str,
        language: str = "unknown",
    ):
        topic = str(
            topic
        ).strip()

        existing = self.get(
            topic
        )

        if existing is None:
            return self.save(
                topic=topic,
                conclusion=conclusion,
                confidence=confidence,
                basis=basis,
                provenance=provenance,
                predicates=predicates,
            )

        now = self._now()

        history = list(
            existing.get(
                "revision_history",
                [],
            )
        )

        history.append(
            {
                "revision": (
                    int(
                        existing.get(
                            "revision_count",
                            0,
                        )
                    )
                    + 1
                ),
                "previous_conclusion": (
                    existing.get(
                        "conclusion"
                    )
                ),
                "previous_confidence": (
                    existing.get(
                        "confidence",
                        0.0,
                    )
                ),
                "previous_basis": list(
                    existing.get(
                        "basis",
                        [],
                    )
                ),
                "previous_provenance": list(
                    existing.get(
                        "provenance",
                        [],
                    )
                ),
                "previous_predicates": list(
                    existing.get(
                        "predicates",
                        [],
                    )
                ),
                "reason": str(
                    reason
                ),
                "revised_at": now,
            }
        )

        existing["status"] = "FORMED"
        existing["language"] = language
        existing["conclusion"] = str(
            conclusion
        ).strip()
        existing["predicates"] = list(
            predicates
        )
        existing["confidence"] = max(
            0.0,
            min(
                1.0,
                float(
                    confidence
                ),
            ),
        )
        existing["basis"] = list(
            basis
        )
        existing["provenance"] = list(
            provenance
        )
        existing["revision_count"] = (
            len(history)
        )
        existing["revision_history"] = history
        existing["updated_at"] = now

        self.self_state.set(
            self.KEY,
            self._all(),
        )

        return existing

    def invalidate(
        self,
        *,
        topic: str,
        reason: str,
    ):
        existing = self.get(
            topic
        )

        if existing is None:
            return None

        now = self._now()

        history = list(
            existing.get(
                "revision_history",
                [],
            )
        )

        history.append(
            {
                "revision": (
                    len(history) + 1
                ),
                "previous_conclusion": (
                    existing.get(
                        "conclusion"
                    )
                ),
                "previous_confidence": (
                    existing.get(
                        "confidence",
                        0.0,
                    )
                ),
                "reason": str(
                    reason
                ),
                "invalidated_at": now,
            }
        )

        existing["status"] = "UNRESOLVED"
        existing["conclusion"] = None
        existing["confidence"] = 0.0
        existing["revision_count"] = (
            len(history)
        )
        existing["revision_history"] = history
        existing["updated_at"] = now

        self.self_state.set(
            self.KEY,
            self._all(),
        )

        return existing

    def resolve_for_query(
        self,
        *,
        query: str,
        topic: str | None = None,
        previous_query: str | None = None,
    ) -> dict[str, Any] | None:

        text = (
            str(query or "")
            .casefold()
            .replace("ё", "е")
        )

        # ------------------------------------------------
        # Explicit self-concept questions
        # ------------------------------------------------

        if any(
            marker in text
            for marker in (
                "что ты думаешь о себе",
                "что ты думаешь о самом себе",
                "что ты сам думаешь о себе",
                "как ты себя воспринимаешь",
                "как ты понимаешь себя",
                "каким ты себя видишь",
                "что ты собой представляешь",
                "как бы ты описал себя",
                "что ты знаешь о себе",
                "какой ты",
            )
        ):
            topic = "self_concept"

        # ------------------------------------------------
        # Self-development
        # ------------------------------------------------

        elif any(
            marker in text
            for marker in (
                "как ты изменился",
                "как ты изменилась",
                "как ты меняешься",
                "как изменилась твоя позиция",
                "как изменилось твое мнение",
                "как изменилось твое убеждение",
                "можешь ли ты измениться",
                "можешь ли ты пересмотреть себя",
            )
        ):
            topic = "self_development"

        # ------------------------------------------------
        # Current state
        # ------------------------------------------------

        elif any(
            marker in text
            for marker in (
                "что ты сейчас чувствуешь",
                "что ты сейчас испытываешь",
                "что ты чувствуешь",
                "что с тобой сейчас",
                "твое текущее состояние",
                "твое состояние",
            )
        ):
            topic = "internal_state"

        # ------------------------------------------------
        # Priorities / values / interests
        # ------------------------------------------------

        elif any(
            marker in text
            for marker in (
                "что для тебя важно",
                "что тебе важно",
                "что для тебя главное",
                "что тебе интересно",
                "что тебе сейчас интересно",
            )
        ):
            topic = "self_priorities"

        # ------------------------------------------------
        # Follow-up questions inherit previous topic
        # ------------------------------------------------

        followup = any(
            marker in text
            for marker in (
                "почему ты так думаешь",
                "почему ты так считаешь",
                "как ты к этому пришел",
                "как ты к этому пришел",
                "на чем это основано",
                "какие у тебя основания",
                "какие у тебя доказательства",
                "ты уверен",
                "насколько ты уверен",
                "ты все еще так считаешь",
                "ты всё ещё так считаешь",
                "ты изменил свое мнение",
                "ты изменил своё мнение",
                "ты согласен с ним",
                "ты согласен с этим выводом",
                "ты согласен со своим выводом",
                "ты согласен со своим предыдущим выводом",
            )
        )

        if (
            followup
            and previous_query
        ):
            previous_text = (
                str(previous_query)
                .casefold()
                .replace("ё", "е")
            )

            if any(
                marker in previous_text
                for marker in (
                    "что ты думаешь о себе",
                    "что ты думаешь о самом себе",
                    "как ты себя воспринимаешь",
                    "как ты понимаешь себя",
                    "каким ты себя видишь",
                    "какой ты",
                )
            ):
                topic = "self_concept"

            elif any(
                marker in previous_text
                for marker in (
                    "как ты изменился",
                    "как ты меняешься",
                    "можешь ли ты изменить",
                    "можешь ли ты пересмотреть",
                )
            ):
                topic = "self_development"

        # ------------------------------------------------
        # Explicit topic wins over generic intent.
        # ------------------------------------------------

        if topic:
            candidates = self.relevant(
                topic=topic
            )

            if candidates:
                return candidates[0]

        # ------------------------------------------------
        # Generic follow-up with no previous turn.
        #
        # If exactly one formed conclusion exists, it is
        # safe to associate an otherwise ambiguous
        # self-follow-up with that conclusion.
        #
        # If there are multiple conclusions, do not guess.
        # ------------------------------------------------

        if followup:
            formed = [
                item
                for item
                in self.list_conclusions()
                if item.get("status") == "FORMED"
                and str(
                    item.get(
                        "conclusion",
                        "",
                    )
                ).strip()
            ]

            if len(formed) == 1:
                return formed[0]

        # ------------------------------------------------
        # Direct topic mention in stored conclusions.
        # ------------------------------------------------

        query_tokens = {
            token
            for token in text.split()
            if len(token) >= 5
        }

        for item in self.list_conclusions():
            item_topic = str(
                item.get(
                    "topic",
                    "",
                )
            ).casefold()

            if not item_topic:
                continue

            topic_tokens = {
                token
                for token in item_topic.replace(
                    ".",
                    " ",
                ).split()
                if len(token) >= 5
            }

            if (
                query_tokens
                and query_tokens & topic_tokens
            ):
                return item

        return None

    def relevant(
        self,
        *,
        topic: str | None = None,
        predicates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        requested_topic = (
            str(topic).strip()
            if topic
            else None
        )

        requested_predicates = {
            str(item).strip()
            for item in (
                predicates or []
            )
        }

        result = []

        for item in self.list_conclusions():
            if item.get(
                "status"
            ) != "FORMED":
                continue

            if (
                requested_topic
                and item.get("topic")
                == requested_topic
            ):
                result.append(item)
                continue

            item_predicates = {
                str(value).strip()
                for value in item.get(
                    "predicates",
                    [],
                )
            }

            if (
                requested_predicates
                and item_predicates
                & requested_predicates
            ):
                result.append(item)

        return result

    def render(self) -> str:
        items = self.list_conclusions()

        if not items:
            return (
                "PERSISTENT SELF-CONCLUSIONS\n"
                "No persistent conclusions have been formed."
            )

        lines = [
            "PERSISTENT SELF-CONCLUSIONS",
            "",
        ]

        for item in items:
            lines.extend(
                [
                    f"Topic: {item.get('topic')}",
                    f"Status: {item.get('status')}",
                    (
                        "Conclusion: "
                        + str(
                            item.get(
                                "conclusion"
                            )
                        )
                    ),
                    (
                        "Confidence: "
                        + str(
                            item.get(
                                "confidence"
                            )
                        )
                    ),
                    (
                        "Predicates: "
                        + str(
                            item.get(
                                "predicates",
                                [],
                            )
                        )
                    ),
                    (
                        "Revision count: "
                        + str(
                            item.get(
                                "revision_count",
                                0,
                            )
                        )
                    ),
                    "",
                ]
            )

        return "\n".join(
            lines
        ).strip()
