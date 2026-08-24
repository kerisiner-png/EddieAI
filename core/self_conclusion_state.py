from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEFAULT_SELF_CONCLUSION_STATE = {
    "status": "UNRESOLVED",
    "current_conclusion": None,
    "topic": None,
    "predicates": [],
    "confidence": 0.0,
    "basis": [],
    "provenance": [],
    "revision_count": 0,
    "revision_history": [],
    "unresolved_reasons": [
        "Целостный собственный вывод о себе ещё не сформирован."
    ],
    "last_updated": None,
}


class SelfConclusionState:
    """
    Явное состояние текущего собственного вывода EddieAI.

    Важно:
    - не является personality trait;
    - не является belief;
    - не является preference;
    - не утверждает наличие сознания;
    - может оставаться UNRESOLVED.
    """

    KEY = "self_conclusion_state"

    def __init__(self, self_state):
        self.self_state = self_state
        self._ensure()

    def _ensure(self):
        current = self.self_state.get(
            self.KEY
        )

        if not isinstance(current, dict):
            self.self_state.set(
                self.KEY,
                DEFAULT_SELF_CONCLUSION_STATE,
            )
            return

        changed = False

        for key, value in (
            DEFAULT_SELF_CONCLUSION_STATE.items()
        ):
            if key not in current:
                current[key] = value
                changed = True

        if changed:
            self.self_state.set(
                self.KEY,
                current,
            )

    def snapshot(self) -> dict[str, Any]:
        value = self.self_state.get(
            self.KEY,
            DEFAULT_SELF_CONCLUSION_STATE,
        )

        return {
            key: value[key]
            for key in value
        }

    def render(self) -> str:
        state = self.snapshot()

        return f"""
SELF-CONCLUSION STATE

status:
{state["status"]}

current_conclusion:
{state["current_conclusion"]}

confidence:
{state["confidence"]}

basis:
{state["basis"]}

unresolved_reasons:
{state["unresolved_reasons"]}

last_updated:
{state["last_updated"]}
""".strip()

    def set_unresolved(
        self,
        *,
        reasons: list[str],
        basis: list[str] | None = None,
    ):
        state = self.snapshot()

        state["status"] = "UNRESOLVED"
        state["current_conclusion"] = None
        state["confidence"] = 0.0
        state["basis"] = list(
            basis or []
        )
        state["provenance"] = []
        state["unresolved_reasons"] = list(
            reasons
        )
        state["last_updated"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.self_state.set(
            self.KEY,
            state,
        )

    def set_conclusion(
        self,
        *,
        conclusion: str,
        confidence: float,
        basis: list[str],
        provenance: list[str] | None = None,
        topic: str | None = None,
        predicates: list[str] | None = None,
    ):
        state = self.snapshot()

        conclusion = str(
            conclusion
        ).strip()

        if not conclusion:
            raise ValueError(
                "Conclusion cannot be empty."
            )

        confidence = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )

        now = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        previous = (
            state.get(
                "current_conclusion"
            )
        )

        if previous is not None:
            state.setdefault(
                "revision_history",
                [],
            )

            state.setdefault(
                "revision_count",
                0,
            )

            state["revision_history"].append(
                {
                    "revision": (
                        state["revision_count"] + 1
                    ),
                    "previous_conclusion": previous,
                    "previous_confidence": (
                        state.get(
                            "confidence",
                            0.0,
                        )
                    ),
                    "previous_basis": list(
                        state.get(
                            "basis",
                            [],
                        )
                    ),
                    "previous_provenance": list(
                        state.get(
                            "provenance",
                            [],
                        )
                    ),
                    "replaced_at": now,
                }
            )

            state["revision_count"] += 1

        state["status"] = "FORMED"
        state["current_conclusion"] = conclusion
        state["topic"] = (
            str(topic).strip()
            if topic
            else state.get("topic")
        )
        state["predicates"] = list(
            predicates
            if predicates is not None
            else state.get(
                "predicates",
                [],
            )
        )
        state["confidence"] = confidence
        state["basis"] = list(
            basis
        )
        state["provenance"] = list(
            provenance or []
        )
        state["unresolved_reasons"] = []
        state["last_updated"] = now

        self.self_state.set(
            self.KEY,
            state,
        )

    def has_conclusion(
        self,
    ) -> bool:
        state = self.snapshot()

        return (
            state.get("status") == "FORMED"
            and bool(
                str(
                    state.get(
                        "current_conclusion"
                    )
                    or ""
                ).strip()
            )
        )

    @staticmethod
    def _tokens(
        text: str,
    ) -> set[str]:
        import re

        normalized = (
            str(text)
            .casefold()
            .replace("ё", "е")
        )

        return {
            token
            for token in re.findall(
                r"[a-zа-я0-9]+",
                normalized,
            )
            if len(token) >= 4
        }

    def relevance(
        self,
        query: str,
    ) -> dict:
        conclusion = self.get_conclusion()

        if conclusion is None:
            return {
                "relevant": False,
                "score": 0.0,
                "matches": [],
                "reason": "no_persistent_conclusion",
            }

        text = str(
            query or ""
        ).casefold().replace(
            "ё",
            "е",
        )

        topic = (
            conclusion.get(
                "topic"
            )
            or ""
        ).casefold()

        predicates = {
            str(item).casefold()
            for item in conclusion.get(
                "predicates",
                [],
            )
        }

        # ------------------------------------------------
        # SELF-CONCEPT INTENT
        # ------------------------------------------------

        self_concept_markers = (
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

        if (
            topic == "self_concept"
            and any(
                marker in text
                for marker in self_concept_markers
            )
        ):
            return {
                "relevant": True,
                "score": 1.0,
                "matches": [
                    "topic:self_concept"
                ],
                "conclusion": conclusion[
                    "conclusion"
                ],
                "reason": (
                    "self_concept_intent"
                ),
            }

        # ------------------------------------------------
        # SELF-CONCLUSION / REASONING INTENT
        # ------------------------------------------------

        reasoning_markers = (
            "почему ты так думаешь",
            "почему ты так считаешь",
            "как ты к этому пришел",
            "как ты к этому пришёл",
            "почему ты сделал такой вывод",
            "на чем это основано",
            "на чем основан твой вывод",
            "какие у тебя основания",
            "какие у тебя доказательства",
            "откуда ты это узнал",
            "откуда ты это знаешь",
        )

        if (
            topic == "self_concept"
            and any(
                marker in text
                for marker in reasoning_markers
            )
        ):
            return {
                "relevant": True,
                "score": 1.0,
                "matches": [
                    "topic:self_concept",
                    "intent:reasoning",
                ],
                "conclusion": conclusion[
                    "conclusion"
                ],
                "reason": (
                    "self_conclusion_reasoning_intent"
                ),
            }

        # ------------------------------------------------
        # REVISION / AGREEMENT INTENT
        # ------------------------------------------------

        revision_markers = (
            "ты согласен со своим выводом",
            "ты согласен со своим предыдущим выводом",
            "ты согласен с ним",
            "ты согласен с этим выводом",
            "ты все еще так считаешь",
            "ты всё ещё так считаешь",
            "ты все еще думаешь так",
            "ты всё ещё думаешь так",
            "ты изменил свое мнение",
            "ты изменил своё мнение",
            "ты пересмотрел свой вывод",
            "ты можешь пересмотреть",
            "ты можешь изменить",
            "ты передумал",
            "ты передумала",
        )

        if (
            any(
                marker in text
                for marker in revision_markers
            )
        ):
            return {
                "relevant": True,
                "score": 1.0,
                "matches": [
                    "intent:revision"
                ],
                "conclusion": conclusion[
                    "conclusion"
                ],
                "reason": (
                    "revision_intent"
                ),
            }

        # ------------------------------------------------
        # PREDICATE-LEVEL MATCH
        # ------------------------------------------------

        predicate_markers = {
            "self_conclusion": (
                "вывод",
                "выводы",
                "мнение",
                "считаешь",
                "считаю",
                "убеждение",
                "убеждения",
            ),
            "autonomous_agency": (
                "сам решаешь",
                "самостоятельно решаешь",
                "сам выбираешь",
                "самостоятельно выбираешь",
                "принимаешь решения",
            ),
        }

        predicate_matches = []

        for predicate in predicates:
            markers = predicate_markers.get(
                predicate,
                (),
            )

            if any(
                marker in text
                for marker in markers
            ):
                predicate_matches.append(
                    predicate
                )

        if predicate_matches:
            return {
                "relevant": True,
                "score": 0.85,
                "matches": [
                    "predicate:" + item
                    for item
                    in predicate_matches
                ],
                "conclusion": conclusion[
                    "conclusion"
                ],
                "reason": (
                    "predicate_intent"
                ),
            }

        return {
            "relevant": False,
            "score": 0.0,
            "matches": [],
            "conclusion": conclusion[
                "conclusion"
            ],
            "reason": "no_relevant_intent",
        }

    def get_conclusion(
        self,
    ) -> dict[str, Any] | None:
        if not self.has_conclusion():
            return None

        state = self.snapshot()

        return {
            "conclusion": state[
                "current_conclusion"
            ],
            "topic": state.get(
                "topic"
            ),
            "predicates": list(
                state.get(
                    "predicates",
                    [],
                )
            ),
            "confidence": state[
                "confidence"
            ],
            "basis": list(
                state.get(
                    "basis",
                    [],
                )
            ),
            "provenance": list(
                state.get(
                    "provenance",
                    [],
                )
            ),
            "revision_count": int(
                state.get(
                    "revision_count",
                    0,
                )
            ),
            "last_updated": state.get(
                "last_updated"
            ),
        }

    def revise_conclusion(
        self,
        *,
        conclusion: str,
        confidence: float,
        basis: list[str],
        provenance: list[str] | None = None,
        reason: str,
    ):
        state = self.snapshot()

        current = state.get(
            "current_conclusion"
        )

        if current is None:
            self.set_conclusion(
                conclusion=conclusion,
                confidence=confidence,
                basis=basis,
                provenance=provenance,
            )
            return

        now = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        state.setdefault(
            "revision_history",
            [],
        )

        state.setdefault(
            "revision_count",
            0,
        )

        state["revision_history"].append(
            {
                "revision": (
                    state["revision_count"] + 1
                ),
                "previous_conclusion": current,
                "previous_confidence": (
                    state.get(
                        "confidence",
                        0.0,
                    )
                ),
                "previous_basis": list(
                    state.get(
                        "basis",
                        [],
                    )
                ),
                "previous_provenance": list(
                    state.get(
                        "provenance",
                        [],
                    )
                ),
                "reason": str(
                    reason
                ),
                "replaced_at": now,
            }
        )

        state["revision_count"] += 1
        state["status"] = "FORMED"
        state["current_conclusion"] = (
            str(
                conclusion
            ).strip()
        )
        state["confidence"] = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )
        state["basis"] = list(
            basis
        )
        state["provenance"] = list(
            provenance or []
        )
        state["unresolved_reasons"] = []
        state["last_updated"] = now

        self.self_state.set(
            self.KEY,
            state,
        )

    def invalidate(
        self,
        *,
        reason: str,
    ):
        state = self.snapshot()

        now = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        if state.get(
            "current_conclusion"
        ) is not None:
            state.setdefault(
                "revision_history",
                [],
            )

            state.setdefault(
                "revision_count",
                0,
            )

            state["revision_history"].append(
                {
                    "revision": (
                        state["revision_count"] + 1
                    ),
                    "previous_conclusion": (
                        state[
                            "current_conclusion"
                        ]
                    ),
                    "previous_confidence": (
                        state.get(
                            "confidence",
                            0.0,
                        )
                    ),
                    "previous_basis": list(
                        state.get(
                            "basis",
                            [],
                        )
                    ),
                    "previous_provenance": list(
                        state.get(
                            "provenance",
                            [],
                        )
                    ),
                    "reason": str(
                        reason
                    ),
                    "invalidated_at": now,
                }
            )

            state["revision_count"] += 1

        state["status"] = "UNRESOLVED"
        state["current_conclusion"] = None
        state["confidence"] = 0.0
        state["basis"] = []
        state["provenance"] = []
        state["unresolved_reasons"] = [
            str(reason)
        ]
        state["last_updated"] = now

        self.self_state.set(
            self.KEY,
            state,
        )
