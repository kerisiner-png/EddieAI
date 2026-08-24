from core.model_orchestrator import ModelOrchestrator
from pathlib import Path
from tempfile import TemporaryDirectory

from core.agent_loop import AgentLoop
from core.autonomy_orchestrator import AutonomyOrchestrator
from core.autonomous_runtime import AutonomousRuntime
from core.autonomy_scheduler import AutonomyScheduler

from identity.action_planner import ActionPlanner
from identity.adaptive_plan_controller import (
    AdaptivePlanController,
)
from identity.adaptive_planner import (
    AdaptivePlanner,
)
from identity.filesystem_executor import (
    FilesystemExecutor,
)
from identity.goal_generator import (
    GoalGenerator,
)
from identity.goal_manager import GoalManager
from identity.goal_plan_generator import (
    GoalPlanGenerator,
)
from identity.goal_planner import GoalPlanner
from identity.goal_review import GoalReview
from identity.llm_executor import LLMExecutor
from identity.motivation import MotivationEngine
from identity.personality_lifecycle import (
    PersonalityLifecycle,
)
from identity.reflection_engine import (
    ReflectionEngine,
)
from identity.self_experience import (
    SelfExperienceConsolidator,
)
from identity.self_state import SelfState
from identity.task_controller import (
    TaskController,
)
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner
from identity.web_executor import WebExecutor

from memory.database import Memory
from memory.evidence import EvidenceEngine
from memory.external_knowledge import (
    ExternalKnowledgeRecorder,
)
from memory.research_context import (
    ResearchContext,
)
from memory.self_interpretation import (
    SelfInterpretation,
)
from memory.source_evaluator import (
    SourceEvaluator,
)
from memory.tool_experience import (
    ToolExperienceRecorder,
)


with TemporaryDirectory() as temp:
    root = Path(temp)

    state = SelfState(
        root / "self_state.json"
    )

    memory = Memory(
        root / "memory.db"
    )

    # -----------------------------------------
    # PERSONALITY
    # -----------------------------------------

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

    # -----------------------------------------
    # MOTIVATION / GOAL
    # -----------------------------------------

    motivation = MotivationEngine(
        state,
        lifecycle,
    )

    goal_planner = GoalPlanner(
        state
    )

    goal_manager = GoalManager(
        state,
        goal_planner,
    )

    goal_review = GoalReview(
        goal_manager
    )

    goal_plan_generator = (
        GoalPlanGenerator(
            goal_planner
        )
    )

    goal_generator = GoalGenerator(
        motivation_engine=motivation,
        goal_manager=goal_manager,
        goal_review=goal_review,
        goal_plan_generator=(
            goal_plan_generator
        ),
    )

    # -----------------------------------------
    # ADAPTIVE PLANNING
    # -----------------------------------------

    adaptive_planner = (
        AdaptivePlanner()
    )

    adaptive_plan_controller = (
        AdaptivePlanController(
            goal_planner
        )
    )

    # -----------------------------------------
    # RESEARCH / MEMORY
    # -----------------------------------------

    external_recorder = (
        ExternalKnowledgeRecorder(
            memory
        )
    )

    self_interpreter = (
        SelfInterpretation(
            memory
        )
    )

    research_context = (
        ResearchContext(
            memory
        )
    )

    source_evaluator = (
        SourceEvaluator(
            acceptance_threshold=0.45
        )
    )

    reflection_engine = (
        ReflectionEngine(
            memory,
            EvidenceEngine(memory),
            lifecycle,
        )
    )

    # -----------------------------------------
    # TOOLS
    # -----------------------------------------

    registry = ToolRegistry()

    registry.register(
        name="llm",
        executor=LLMExecutor(ModelOrchestrator()),
        description="Local LLM.",
        enabled=True,
    )

    registry.register(
        name="filesystem",
        executor=FilesystemExecutor(
            r"C:\EddieAI"
        ),
        description=(
            "EddieAI filesystem sandbox."
        ),
        enabled=True,
    )

    registry.register(
        name="web",
        executor=WebExecutor(),
        description=(
            "External web search."
        ),
        enabled=True,
    )

    registry.register(
        name="research",
        executor=object(),
        description=(
            "Composite research executor."
        ),
        enabled=True,
    )

    tool_runner = ToolRunner(
        registry,
        filesystem_root=(
            r"C:\EddieAI"
        ),
        external_recorder=(
            external_recorder
        ),
        self_interpreter=(
            self_interpreter
        ),
        source_evaluator=(
            source_evaluator
        ),
    )

    # -----------------------------------------
    # EXPERIENCE
    # -----------------------------------------

    experience_recorder = (
        ToolExperienceRecorder(
            memory
        )
    )

    experience_consolidator = (
        SelfExperienceConsolidator(
            memory,
            EvidenceEngine(memory),
        )
    )

    # -----------------------------------------
    # TASK EXECUTION
    # -----------------------------------------

    task_controller = TaskController(
        goal_manager,
        goal_planner,
    )

    agent_loop = AgentLoop(
        goal_manager=goal_manager,
        goal_planner=goal_planner,
        action_planner=ActionPlanner(),
        tool_runner=tool_runner,
        task_controller=task_controller,
        experience_recorder=(
            experience_recorder
        ),
        max_actions=1,
        experience_consolidator=(
            experience_consolidator
        ),
        research_context=(
            research_context
        ),
        adaptive_planner=(
            adaptive_planner
        ),
        adaptive_plan_controller=(
            adaptive_plan_controller
        ),
        reflection_engine=(
            reflection_engine
        ),
    )

    # -----------------------------------------
    # ORCHESTRATION
    # -----------------------------------------

    orchestrator = (
        AutonomyOrchestrator(
            goal_manager=goal_manager,
            goal_generator=goal_generator,
            goal_plan_generator=(
                goal_plan_generator
            ),
            agent_loop=agent_loop,
        )
    )

    # -----------------------------------------
    # SCHEDULER / RUNTIME
    # -----------------------------------------

    scheduler = AutonomyScheduler(
        autonomous_cycle=orchestrator,
        interval_seconds=300,
        max_ticks_per_window=3,
        window_seconds=3600,
    )

    runtime = AutonomousRuntime(
        scheduler=scheduler,
        memory=memory,
    )

    runtime.goal_manager = (
        goal_manager
    )

    runtime.goal_planner = (
        goal_planner
    )

    runtime.motivation = (
        motivation
    )

    runtime.goal_generator = (
        goal_generator
    )

    runtime.goal_plan_generator = (
        goal_plan_generator
    )

    runtime.adaptive_planner = (
        adaptive_planner
    )

    runtime.adaptive_plan_controller = (
        adaptive_plan_controller
    )

    runtime.tool_registry = (
        registry
    )

    runtime.tool_runner = (
        tool_runner
    )

    runtime.external_recorder = (
        external_recorder
    )

    runtime.self_interpreter = (
        self_interpreter
    )

    runtime.research_context = (
        research_context
    )

    runtime.source_evaluator = (
        source_evaluator
    )

    runtime.reflection_engine = (
        reflection_engine
    )

    runtime.experience_recorder = (
        experience_recorder
    )

    runtime.experience_consolidator = (
        experience_consolidator
    )

    # -----------------------------------------
    # RUNTIME BEFORE
    # -----------------------------------------

    print("=== RUNTIME BEFORE ===")
    print(
        runtime.snapshot()
    )

    # -----------------------------------------
    # TICK 1
    # -----------------------------------------

    print()
    print("=== TICK 1 ===")

    first = runtime.tick()

    print(first)

    # -----------------------------------------
    # GOALS
    # -----------------------------------------

    print()
    print("=== GOALS ===")

    for goal in goal_manager.all():
        print(goal)

    # -----------------------------------------
    # PLAN
    # -----------------------------------------

    print()
    print("=== PLAN ===")

    active = goal_manager.active()

    if active:
        selected_goal = active[0]

        for task in goal_planner.tasks(
            selected_goal.value
        ):
            print(task)

    # -----------------------------------------
    # KNOWLEDGE COUNTS
    # -----------------------------------------

    print()
    print(
        "=== EXTERNAL KNOWLEDGE COUNT ==="
    )

    row = memory.connection.execute("""
        SELECT COUNT(*) AS count
        FROM knowledge
        WHERE owner = 'EXTERNAL'
    """).fetchone()

    print(row["count"])

    print()
    print(
        "=== SELF INTERPRETATION COUNT ==="
    )

    row = memory.connection.execute("""
        SELECT COUNT(*) AS count
        FROM knowledge
        WHERE owner = 'SELF'
          AND source_type = 'SELF_INTERPRETATION'
    """).fetchone()

    print(row["count"])

    print()
    print(
        "=== SELF EXPERIENCE COUNT ==="
    )

    row = memory.connection.execute("""
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'SELF_EXPERIENCE'
    """).fetchone()

    print(row["count"])

    print()
    print(
        "=== REFLECTION COUNT ==="
    )

    row = memory.connection.execute("""
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'REFLECTION'
    """).fetchone()

    print(row["count"])

    print()
    print(
        "=== EVIDENCE COUNT ==="
    )

    row = memory.connection.execute("""
        SELECT COUNT(*) AS count
        FROM evidence_events
    """).fetchone()

    print(row["count"])

    # -----------------------------------------
    # SOURCE QUALITY
    # -----------------------------------------

    print()
    print(
        "=== SOURCE QUALITY ==="
    )

    result = first.get(
        "result",
        {},
    )

    orchestration = result.get(
        "result",
        {},
    )

    execution = orchestration.get(
        "execution"
    )

    if execution and execution.steps:
        step = execution.steps[0]

        action_result = step.get(
            "result",
            {},
        )

        payload = action_result.get(
            "result",
            {},
        )

        print(
            "RAW:",
            payload.get(
                "raw_results_count",
                0,
            ),
        )

        print(
            "ACCEPTED:",
            payload.get(
                "accepted_count",
                0,
            ),
        )

        print(
            "REJECTED:",
            payload.get(
                "rejected_count",
                0,
            ),
        )

        print()
        print(
            "=== REFLECTION ==="
        )

        print(
            step.get(
                "reflection"
            )
        )

        print()
        print(
            "=== ADAPTIVE ==="
        )

        print(
            step.get(
                "adaptive_result"
            )
        )

    # -----------------------------------------
    # TRAITS
    # -----------------------------------------

    print()
    print(
        "=== TRAITS ==="
    )

    for trait in lifecycle.all_traits():
        print(trait)

    # -----------------------------------------
    # RUNTIME AFTER
    # -----------------------------------------

    print()
    print(
        "=== RUNTIME AFTER ==="
    )

    print(
        runtime.snapshot()
    )

    memory.close()
