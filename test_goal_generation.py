from pathlib import Path
from tempfile import TemporaryDirectory

from identity.goal_generator import GoalGenerator
from identity.goal_manager import GoalManager
from identity.goal_review import GoalReview
from identity.motivation import MotivationEngine
from identity.personality_lifecycle import PersonalityLifecycle
from identity.self_state import SelfState


with TemporaryDirectory() as temp:
    state = SelfState(
        Path(temp) / "self_state.json"
    )

    lifecycle = PersonalityLifecycle(
        state
    )

    lifecycle.promote(
        field="interest",
        value="космос",
        strength=0.95,
        confidence=0.95,
        evidence_count=10,
    )

    motivation = MotivationEngine(
        state,
        lifecycle,
    )

    goal_manager = GoalManager(
        state
    )

    goal_review = GoalReview(
        goal_manager
    )

    generator = GoalGenerator(
        motivation,
        goal_manager,
        goal_review,
    )

    print("=== MOTIVATION ===")

    for candidate in motivation.candidates():
        print(candidate)

    print()
    print("=== GOAL GENERATION ===")

    for result in generator.generate():
        print(result)

    print()
    print("=== ACTIVE GOALS ===")

    for goal in goal_manager.active():
        print(goal)
