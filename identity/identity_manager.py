from typing import Any

from identity.proposal import Proposal


class IdentityManager:
    """
    Controls changes to long-term identity.

    The language model can propose changes.
    This class decides whether they are admissible.
    """

    MIN_CONFIDENCE = 0.75

    def __init__(
        self,
        self_state,
        memory,
        personality_lifecycle=None,
    ):
        self.self_state = self_state
        self.memory = memory
        self.personality_lifecycle = (
            personality_lifecycle
        )

    def evaluate(self, proposal: Proposal) -> str:
        if proposal.confidence < self.MIN_CONFIDENCE and proposal.origin != "conversation_claim":
            return "deferred"

        if proposal.proposal_type == "name":
            return self._evaluate_name(proposal)

        if proposal.proposal_type == "interest":
            return self._evaluate_list_field(
                "interests",
                proposal,
            )

        if proposal.proposal_type == "preference":
            return self._evaluate_preference(proposal)

        if proposal.proposal_type == "habit":
            return self._evaluate_list_field(
                "habits",
                proposal,
            )

        if proposal.proposal_type == "belief":
            return self._evaluate_list_field(
                "beliefs",
                proposal,
            )

        if proposal.proposal_type == "goal":
            return self._evaluate_list_field(
                "goals",
                proposal,
            )

        return "deferred"

    def _evaluate_name(self, proposal: Proposal) -> str:
        current_name = self.self_state.get("name")

        if current_name is not None:
            return "deferred"

        if not isinstance(proposal.value, str):
            return "rejected"

        name = proposal.value.strip()

        if not name:
            return "rejected"

        self.self_state.set("name", name)

        self.memory.remember_proposal(
            content=f"Я выбрал себе имя: {name}",
            proposal_type="name",
            confidence=proposal.confidence,
            origin="self_decision",
        )

        return "accepted"

    def _evaluate_preference(
        self,
        proposal: Proposal,
    ) -> str:
        from datetime import datetime, timezone

        from identity.preference_label import (
            preference_label,
        )
        from identity.preference_model import (
            enrich_entry,
        )

        meta = proposal.meta

        if not isinstance(meta, dict):
            return self._evaluate_list_field(
                "preferences",
                proposal,
            )

        method = str(
            meta.get("method", "")
        ).strip()
        context = str(
            meta.get("context", "")
        ).strip()

        if not method:
            return self._evaluate_list_field(
                "preferences",
                proposal,
            )

        current = list(
            self.self_state.get(
                "preferences",
                [],
            )
        )

        for entry in current:
            if isinstance(entry, dict):
                if (
                    str(entry.get("method", "")).strip()
                    == method
                ):
                    enriched = enrich_entry(
                        entry,
                        source="ACTION_CHOICE",
                    )

                    entry.update(enriched)

                    self.self_state.set(
                        "preferences",
                        current,
                    )

                    return "already_present"

            elif (
                isinstance(entry, str)
                and entry.startswith(
                    f"{context}:action_method:"
                )
            ):
                if entry.endswith(
                    f":{method}"
                ):
                    return "already_present"

        label = preference_label(
            {
                "label": meta.get("task"),
                "context": context,
                "method": method,
            }
        )

        entry = enrich_entry(
            {
                "label": label,
                "context": context,
                "method": method,
                "share": meta.get("share", 0.0),
                "total": meta.get("total", 0),
                "source": "ACTION_CHOICE",
                "ts": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
            source="ACTION_CHOICE",
        )

        current.append(entry)
        self.self_state.set(
            "preferences",
            current,
        )

        self.memory.remember_proposal(
            content=f"preferences: {label}",
            proposal_type="preference",
            confidence=proposal.confidence,
            origin="evidence_convergence",
        )

        if self.personality_lifecycle is not None:
            evidence_count = (
                proposal.evidence_count
                if proposal.evidence_count is not None
                else len(proposal.evidence)
            )

            self.personality_lifecycle.promote(
                field="preference",
                value=label,
                strength=proposal.confidence,
                confidence=proposal.confidence,
                evidence_count=evidence_count,
            )

        return "accepted"

    def _evaluate_list_field(
        self,
        field: str,
        proposal: Proposal,
    ) -> str:

        value = proposal.value

        if not isinstance(value, str):
            return "rejected"

        value = value.strip()

        if not value:
            return "rejected"

        current = list(
            self.self_state.get(field, [])
        )

        if value in current:
            return "already_present"

        current.append(value)
        self.self_state.set(field, current)

        self.memory.remember_proposal(
            content=f"{field}: {value}",
            proposal_type=proposal.proposal_type,
            confidence=proposal.confidence,
            origin="evidence_convergence",
        )

        if self.personality_lifecycle is not None:
            evidence_count = (
                proposal.evidence_count
                if proposal.evidence_count is not None
                else len(proposal.evidence)
            )

            self.personality_lifecycle.promote(
                field=proposal.proposal_type,
                value=value,
                strength=proposal.confidence,
                confidence=proposal.confidence,
                evidence_count=evidence_count,
            )

        return "accepted"
