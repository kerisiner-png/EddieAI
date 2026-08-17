from pathlib import Path
from tempfile import TemporaryDirectory

from identity.evidence_consolidator import (
    EvidenceConsolidator,
)
from identity.personality_lifecycle import (
    PersonalityLifecycle,
)
from identity.self_state import SelfState

from memory.database import Memory
from memory.evidence import EvidenceEngine


with TemporaryDirectory() as temp:
    memory = None

    try:
        state = SelfState(
            Path(temp) / "state.json"
        )

        memory = Memory(
            Path(temp) / "memory.db"
        )

        evidence = EvidenceEngine(
            memory
        )

        lifecycle = PersonalityLifecycle(
            state
        )

        consolidator = (
            EvidenceConsolidator(
                evidence,
            )
        )

        # -----------------------------------------
        # FIRST: ONE SOURCE
        # -----------------------------------------

        first_record = evidence.add(
            category="interest",
            value="космос",
            source="SELF_ACTION",
        )

        print("=== FIRST EVIDENCE ===")
        print(first_record)

        print()
        print("=== FIRST CONSOLIDATION ===")

        first = (
            consolidator.consolidate()
        )

        print(first)

        # -----------------------------------------
        # SECOND: MORE DIVERSE SOURCES
        # -----------------------------------------

        evidence.add(
            category="interest",
            value="космос",
            source="SELF_OBSERVATION",
        )

        evidence.add(
            category="interest",
            value="космос",
            source="SHARED_EXPERIENCE",
        )

        evidence.add(
            category="interest",
            value="космос",
            source="USER_STATEMENT",
        )

        record = evidence.get(
            "interest",
            "космос",
        )

        print()
        print("=== COMBINED EVIDENCE ===")
        print(record)

        print()
        print("=== SECOND CONSOLIDATION ===")

        second = (
            consolidator.consolidate()
        )

        print(second)

        print()
        print("=== FINAL TRAITS ===")

        traits = lifecycle.all_traits()
        print(traits)

        if traits:
            raise AssertionError(
                "EvidenceConsolidator must not modify lifecycle."
            )

    finally:
        if memory is not None:
            memory.close()
