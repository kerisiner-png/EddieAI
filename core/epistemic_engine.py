from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.text_relevance_matcher import TextRelevanceMatcher


@dataclass(frozen=True)
class EpistemicItem:
    value: str
    category: str
    status: str
    evidence_count: int
    provenance: str
    priority: float
    reason: str


class EpistemicEngine:
    """
    Deterministic epistemic layer.

    Не формирует убеждения и не изменяет self_state.
    Определяет только текущее эпистемическое состояние
    уже существующих self-claims.
    """

    STOPWORDS = {
        "что",
        "это",
        "они",
        "она",
        "он",
        "как",
        "есть",
        "было",
        "были",
        "быть",
        "мне",
        "мои",
        "мой",
        "моя",
        "моё",
        "у",
        "в",
        "на",
        "из",
        "про",
        "о",
        "об",
        "для",
        "и",
        "или",
        "не",
        "да",
        "нет",
        "ты",
        "я",
        "тебя",
        "себе",
        "свой",
        "своё",
    }

    def __init__(self, agent):
        self.agent = agent

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        return " ".join(
            str(value or "")
            .casefold()
            .split()
        )

    @classmethod
    def _significant_tokens(
        cls,
        value: str,
    ) -> set[str]:
        return TextRelevanceMatcher.tokens(
            value
        )

    def _belief_evidence_count(
        self,
        value: str,
    ) -> int:
        evidence = getattr(
            self.agent,
            "evidence",
            None,
        )

        if evidence is None:
            return 0

        memory = getattr(
            evidence,
            "memory",
            None,
        )

        connection = getattr(
            memory,
            "connection",
            None,
        )

        if connection is None:
            return 0

        try:
            rows = connection.execute(
                """
                SELECT
                    source,
                    independence_key,
                    weight
                FROM evidence_events
                WHERE category = 'belief'
                  AND lower(value) = lower(?)
                  AND weight > 0
                """,
                (value,),
            ).fetchall()
        except Exception:
            return 0

        return len(rows)

    def analyze(self) -> dict:
        self_state = self.agent.self_state

        beliefs = list(
            self_state.get(
                "beliefs",
                [],
            )
        )

        items: list[EpistemicItem] = []

        for belief in beliefs:
            evidence_count = (
                self._belief_evidence_count(
                    str(belief)
                )
            )

            if evidence_count == 0:
                status = "UNVERIFIED"
                provenance = "UNKNOWN"
                priority = 0.85
                reason = (
                    "Утверждение находится в self_state "
                    "как belief, но текущая система не "
                    "нашла связанного evidence."
                )
            else:
                status = "SUPPORTED"
                provenance = "EVIDENCE"
                priority = 0.20
                reason = (
                    "Для утверждения существуют "
                    "связанные evidence events."
                )

            items.append(
                EpistemicItem(
                    value=str(belief),
                    category="belief",
                    status=status,
                    evidence_count=evidence_count,
                    provenance=provenance,
                    priority=priority,
                    reason=reason,
                )
            )

        unresolved = [
            item
            for item in items
            if item.status == "UNVERIFIED"
        ]

        supported = [
            item
            for item in items
            if item.status == "SUPPORTED"
        ]

        return {
            "status": "OK",
            "items": items,
            "unresolved": unresolved,
            "supported": supported,
            "unresolved_count": len(
                unresolved
            ),
            "supported_count": len(
                supported
            ),
        }

    def relevant_unresolved_claims(
        self,
        user_message: str,
    ) -> list[dict]:
        """
        Возвращает unresolved claims, которые
        семантически связаны с текущим сообщением.

        Это НЕ определяет истинность claim.
        Это только определяет, стоит ли рассмотреть
        его как текущую epistemic issue.
        """

        if not self._significant_tokens(
            user_message
        ):
            return []

        result = []

        for item in self.analyze()[
            "unresolved"
        ]:
            relevance = (
                TextRelevanceMatcher.relevance(
                    user_message,
                    item.value,
                )
            )

            if not relevance["relevant"]:
                continue

            result.append(
                {
                    "claim": item.value,
                    "category": item.category,
                    "status": item.status,
                    "evidence_count": (
                        item.evidence_count
                    ),
                    "provenance": (
                        item.provenance
                    ),
                    "priority": item.priority,
                    "relevance": (
                        relevance["score"]
                    ),
                    "matched_terms": (
                        relevance["matches"]
                    ),
                    "reason": item.reason,
                }
            )

        result.sort(
            key=lambda item: (
                -item["relevance"],
                -item["priority"],
            )
        )

        return result

    def render(self) -> str:
        result = self.analyze()

        lines = [
            "CURRENT EPISTEMIC STATE",
            "",
            (
                "This layer describes the epistemic "
                "status of EddieAI's existing self-claims."
            ),
            (
                "It does not decide metaphysical questions "
                "and does not modify self_state."
            ),
            "",
            "UNRESOLVED SELF-CLAIMS:",
        ]

        unresolved = result["unresolved"]

        if not unresolved:
            lines.append(
                "none"
            )
        else:
            for item in unresolved:
                lines.extend(
                    [
                        f"- claim: {item.value}",
                        f"  category: {item.category}",
                        f"  status: {item.status}",
                        f"  evidence_count: "
                        f"{item.evidence_count}",
                        f"  provenance: "
                        f"{item.provenance}",
                        f"  priority: "
                        f"{item.priority}",
                        f"  reason: "
                        f"{item.reason}",
                    ]
                )

        lines.extend(
            [
                "",
                "SUPPORTED SELF-CLAIMS:",
            ]
        )

        supported = result["supported"]

        if not supported:
            lines.append(
                "none"
            )
        else:
            for item in supported:
                lines.extend(
                    [
                        f"- claim: {item.value}",
                        f"  status: {item.status}",
                        f"  evidence_count: "
                        f"{item.evidence_count}",
                    ]
                )

        lines.extend(
            [
                "",
                "EPISTEMIC RULE:",
                (
                    "A statement being present in self_state "
                    "does not by itself prove that it is an "
                    "established personal conclusion."
                ),
                (
                    "When provenance or evidence is missing, "
                    "EddieAI should recognize the claim as "
                    "unresolved rather than silently treating "
                    "it as a personal conclusion."
                ),
                (
                    "An unresolved claim may become a target "
                    "for investigation when it is relevant "
                    "and sufficiently important."
                ),
            ]
        )

        return "\n".join(lines)
