from pathlib import Path
from tempfile import TemporaryDirectory

from identity.behavior_pattern_detector import (
    BehaviorPatternDetector,
)
from identity.evidence_consolidator import (
    EvidenceConsolidator,
)
from identity.personality_lifecycle import (
    PersonalityLifecycle,
)
from identity.self_state import SelfState

from memory.database import Memory
from memory.evidence import EvidenceEngine
from memory.events import Event


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

        detector = BehaviorPatternDetector(
            memory,
            evidence,
        )

        consolidator = (
            EvidenceConsolidator(
                evidence,
                lifecycle,
            )
        )

        print("=== CYCLE 1 ===")

        memory.remember(
            Event.create(
                content=(
                    "Я самостоятельно выполнил "
                    "действие 'Провести исследование: "
                    "изучить тему: космос' "
                    "через инструмент research. "
                    "Статус: OK."
                ),
                event_type="SELF_EXPERIENCE",
                source_type="TOOL",
                source="research",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        print(
            "OBSERVATIONS:",
            detector.observe(),
        )

        print(
            "CONSOLIDATION:",
            consolidator.consolidate(),
        )

        print()
        print("=== CYCLE 2 ===")

        memory.remember(
            Event.create(
                content=(
                    "Я самостоятельно выполнил "
                    "действие 'Провести исследование: "
                    "изучить тему: космос' "
                    "через инструмент research. "
                    "Статус: OK."
                ),
                event_type="SELF_EXPERIENCE",
                source_type="TOOL",
                source="research",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        print(
            "OBSERVATIONS:",
            detector.observe(),
        )

        print(
            "CONSOLIDATION:",
            consolidator.consolidate(),
        )

        print()
        print("=== CYCLE 3 ===")

        memory.remember(
            Event.create(
                content=(
                    "Я самостоятельно выполнил "
                    "действие 'Провести исследование: "
                    "изучить тему: космос' "
                    "через инструмент research. "
                    "Статус: OK."
                ),
                event_type="SELF_EXPERIENCE",
                source_type="TOOL",
                source="research",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        observations = detector.observe()

        print(
            "OBSERVATIONS:",
            observations,
        )

        print(
            "CONSOLIDATION:",
            consolidator.consolidate(),
        )

        print()
        print("=== EVIDENCE ===")

        print(
            evidence.get(
                "interest",
                "космос",
            )
        )

        print()
        print("=== TRAITS ===")

        for trait in lifecycle.all_traits():
            print(trait)

    finally:
        if memory is not None:
            memory.close()
