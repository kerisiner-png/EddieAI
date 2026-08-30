from core.agent_loop import AgentLoop
from core.autonomy_arbitrator import AutonomyArbitrator
from core.autonomy_orchestrator import AutonomyOrchestrator
from core.autonomy_scheduler import AutonomyScheduler
from core.autonomous_runtime import AutonomousRuntime
from core.curiosity import CuriosityDirector
from core.decision_core import DecisionCore
from core.eddie_server import EddieServer
from core.life_cycle import LifeCycle
from core.model_orchestrator import ModelOrchestrator
from core.outbox import Outbox
from core.speech_habits import SpeechHabits
from core.world_probe import WorldProbe

from identity.action_planner import ActionPlanner
from identity.action_preference_detector import ActionPreferenceDetector
from identity.habit_pattern_detector import HabitPatternDetector
from identity.belief_pattern_detector import BeliefPatternDetector
from identity.adaptive_plan_controller import (
    AdaptivePlanController,
)
from identity.adaptive_planner import (
    AdaptivePlanner,
)
from identity.behavior_pattern_detector import (
    BehaviorPatternDetector,
)
from identity.evidence_consolidator import (
    EvidenceConsolidator,
)
from identity.filesystem_executor import (
    FilesystemExecutor,
)
from identity.goal_generator import GoalGenerator
from identity.goal_manager import GoalManager
from identity.goal_plan_generator import (
    GoalPlanGenerator,
)
from identity.goal_planner import GoalPlanner
from identity.goal_review import GoalReview
from identity.llm_executor import LLMExecutor
from identity.llm_access import CloudFirstLlm
from identity.motivation import MotivationEngine
from identity.reflection_engine import (
    ReflectionEngine,
)
from identity.self_experience import (
    SelfExperienceConsolidator,
)
from identity.task_controller import (
    TaskController,
)
from identity.tool_registry import ToolRegistry
from identity.tool_runner import ToolRunner
from identity.web_executor import (
    WebExecutor,
)

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


class AutonomyRuntimeFactory:
    def __init__(
        self,
        agent,
        filesystem_root=r"C:\EddieAI",
        scheduler_max_ticks_per_window=3,
        scheduler_interval_seconds=300,
        enable_decision_core=False,
        resource_watchdog=None,
    ):
        self.agent = agent
        self.filesystem_root = filesystem_root
        self.scheduler_max_ticks_per_window = (
            scheduler_max_ticks_per_window
        )
        self.scheduler_interval_seconds = (
            scheduler_interval_seconds
        )
        self.enable_decision_core = (
            enable_decision_core
        )
        self.resource_watchdog = resource_watchdog

    def build(self):
        # -----------------------------------------
        # GOALS / PLANNING
        # -----------------------------------------

        goal_planner = GoalPlanner(
            self.agent.self_state
        )

        goal_manager = GoalManager(
            self.agent.self_state,
            goal_planner,
        )

        goal_review = GoalReview(
            goal_manager
        )

        motivation = MotivationEngine(
            self.agent.self_state,
            self.agent.personality_lifecycle,
            memory=self.agent.memory,
        )

        goal_plan_generator = GoalPlanGenerator(
            goal_planner,
            model_orchestrator=(
                self.agent.model_orchestrator
            ),
        )

        goal_generator = GoalGenerator(
            motivation_engine=motivation,
            goal_manager=goal_manager,
            goal_review=goal_review,
            goal_plan_generator=(
                goal_plan_generator
            ),
        )

        adaptive_planner = AdaptivePlanner(
            model_orchestrator=(
                self.agent.model_orchestrator
            ),
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
                self.agent.memory
            )
        )

        self_interpreter = (
            SelfInterpretation(
                self.agent.memory,
                model_orchestrator=(
                    self.agent
                    .model_orchestrator
                ),
            )
        )

        research_context = ResearchContext(
            self.agent.memory
        )

        source_evaluator = SourceEvaluator(
            acceptance_threshold=0.45
        )

        # -----------------------------------------
        # TOOLS
        # -----------------------------------------

        # -----------------------------------------
        # MODEL ORCHESTRATION
        # -----------------------------------------

        model_orchestrator = (
            self.agent.model_orchestrator
        )

        registry = ToolRegistry()

        registry.register(
            name="llm",
            executor=LLMExecutor(
                model_orchestrator
            ),
            description=(
                "Внутренний локальный LLM executor."
            ),
            enabled=True,
        )

        registry.register(
            name="filesystem",
            executor=FilesystemExecutor(
                self.filesystem_root
            ),
            description=(
                "Filesystem sandbox "
                "для проекта EddieAI."
            ),
            enabled=True,
        )

        registry.register(
            name="web",
            executor=WebExecutor(),
            description=(
                "Внешний web search executor."
            ),
            enabled=True,
        )

        # RESEARCH маршрутизируется отдельно.
        # Фактический composite execution
        # выполняется внутри ToolRunner.
        registry.register(
            name="research",
            executor=object(),
            description=(
                "Составной research executor."
            ),
            enabled=True,
        )

        # Встраивание self-model и описания
        # зарегистрированных capabilities.
        self.agent.capabilities = registry.describe()
        self.agent.self_consistency.capabilities = (
            self.agent.capabilities
        )

        tool_runner = ToolRunner(
            registry,
            filesystem_root=(
                self.filesystem_root
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
                self.agent.memory
            )
        )

        experience_consolidator = (
            SelfExperienceConsolidator(
                self.agent.memory,
                self.agent.evidence,
            )
        )

        action_preference_detector = (
            ActionPreferenceDetector(
                self.agent.memory,
                self.agent.evidence,
            )
        )

        habit_pattern_detector = (
            HabitPatternDetector(
                self.agent.memory,
                self.agent.evidence,
            )
        )

        belief_pattern_detector = (
            BeliefPatternDetector(
                self.agent.memory,
                self.agent.evidence,
            )
        )

        # -----------------------------------------
        # OUTBOX
        # -----------------------------------------

        outbox = Outbox(self.filesystem_root)

        eddie_server = EddieServer(
            agent=self.agent,
            history_store=(
                self.agent.memory
            ),
        )

        # -----------------------------------------
        # TASK EXECUTION
        # -----------------------------------------

        task_controller = TaskController(
            goal_manager,
            goal_planner,
        )

        reflection_engine = ReflectionEngine(
            self.agent.memory,
            self.agent.evidence,
            self.agent.personality_lifecycle,
            model_orchestrator=(
                self.agent.model_orchestrator
            ),
        )

        evidence_consolidator = (
            EvidenceConsolidator(
                self.agent.evidence,
            )
        )

        behavior_pattern_detector = (
            BehaviorPatternDetector(
                self.agent.memory,
                self.agent.evidence,
            )
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
            action_preference_detector=(
                action_preference_detector
            ),
            habit_pattern_detector=(
                habit_pattern_detector
            ),
            belief_pattern_detector=(
                belief_pattern_detector
            ),
            evidence=(
                self.agent.evidence
            ),
            identity_manager=(
                self.agent.identity_manager
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
            reflection_engine=reflection_engine,
            goal_review=goal_review,
            appraisal_engine=(
                self.agent.appraisal_engine
            ),
            affective_state=(
                self.agent.affective_state
            ),
            belief_challenge_detector=(
                self.agent.belief_challenge_detector
            ),
            affective_behavior_policy=(
                self.agent.affective_behavior_policy
            ),
            outbox=outbox,
        )

        runtime_agent_loop = agent_loop

        # -----------------------------------------
        # ORCHESTRATION
        # -----------------------------------------

        if self.enable_decision_core:
            decision_core = DecisionCore(
                memory=self.agent.memory,
                goal_manager=goal_manager,
                model_orchestrator=(
                    self.agent.model_orchestrator
                ),
                task_controller=task_controller,
                agent_loop=agent_loop,
                outbox=outbox,
                server=eddie_server,
                evidence=self.agent.evidence,
            )
        else:
            decision_core = None

        orchestrator = AutonomyOrchestrator(
            goal_manager=goal_manager,
            goal_generator=goal_generator,
            goal_plan_generator=(
                goal_plan_generator
            ),
            agent_loop=agent_loop,
            agent=self.agent,
            affective_behavior_policy=(
                self.agent.affective_behavior_policy
            ),
            outbox=outbox,
            server=eddie_server,
            decision_core=decision_core,
        )

        # -----------------------------------------
        # SCHEDULING
        # -----------------------------------------

        scheduler = AutonomyScheduler(
            autonomous_cycle=orchestrator,
            interval_seconds=(
                self.scheduler_interval_seconds
            ),
            max_ticks_per_window=(
                self.scheduler_max_ticks_per_window
            ),
            window_seconds=3600,
        )

        # -----------------------------------------
        # RUNTIME
        # -----------------------------------------

        runtime = AutonomousRuntime(
            scheduler=scheduler,
            memory=self.agent.memory,
            orchestrator=orchestrator,
            life_cycle=LifeCycle(
                self.agent.self_state
            ),
            resource_watchdog=(
                self.resource_watchdog
            ),
        )

        self.agent.life_cycle = runtime.life_cycle

        self.agent.autonomous_runtime = runtime

        runtime.eddie_server = eddie_server
        self.agent.eddie_server = eddie_server

        runtime.behavior_pattern_detector = (
            behavior_pattern_detector
        )

        runtime.evidence_consolidator = (
            evidence_consolidator
        )

        runtime.goal_manager = goal_manager
        self.agent.goal_manager = goal_manager

        self.agent.autonomy_arbitrator = (
            AutonomyArbitrator(
                goal_manager,
                agent=self.agent,
            )
        )

        runtime.autonomy_arbitrator = (
            self.agent.autonomy_arbitrator
        )

        runtime.agent_loop = agent_loop

        runtime.goal_planner = goal_planner
        runtime.motivation = motivation
        runtime.goal_generator = goal_generator
        runtime.goal_plan_generator = (
            goal_plan_generator
        )
        runtime.adaptive_planner = (
            adaptive_planner
        )
        runtime.adaptive_plan_controller = (
            adaptive_plan_controller
        )
        runtime.tool_registry = registry
        runtime.tool_runner = tool_runner

        director = CuriosityDirector(
            self.agent.self_state,
            goal_manager,
            llm=CloudFirstLlm(
                model_orchestrator=(
                    self.agent.model_orchestrator
                )
            ),
        )
        tool_runner.curiosity = director
        orchestrator.curiosity = director
        runtime.curiosity = director
        runtime.world_probe = WorldProbe()

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
        runtime.experience_recorder = (
            experience_recorder
        )
        runtime.experience_consolidator = (
            experience_consolidator
        )
        runtime.outbox = outbox

        runtime.decision_core = decision_core

        runtime.speech_habits = SpeechHabits(
            self.agent.memory
        )

        runtime.reflection_engine = reflection_engine

        self.agent.cognition_worker.start()
        return runtime






