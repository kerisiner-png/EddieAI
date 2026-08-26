import re
from identity.evidence_consolidator import EvidenceConsolidator
from identity.user_evidence import (
    UserEvidenceRecorder,
)
from identity.user_statement_detector import (
    UserStatementDetector,
)
from core.model_orchestrator import ModelOrchestrator

from core.context_router import ContextRouter
from core.cognitive_gate import CognitiveGate
from core.processing_plan import build_processing_plan
from core.cognitive_queue import CognitiveQueue
from core.cognitive_processor import CognitiveProcessor
from core.cognitive_reasoner import CognitiveReasoner
from core.dialogue_state import DialogueState
from core.knowledge_resolver import KnowledgeResolver
from core.self_observation_bridge import SelfObservationBridge
from core.self_state_interface import SelfStateInterface
from core.epistemic_engine import EpistemicEngine
from core.epistemic_intent_detector import EpistemicIntentDetector
from core.cognitive_triage import CognitiveTriage
from core.cognitive_decision_engine import CognitiveDecisionEngine
from core.cognition_worker import CognitionWorker
from core.current_mind_state import CurrentMindState
from core.runtime_state import RuntimeState
from core.self_concept_resolver import SelfConceptResolver
from core.perspective_guard import PerspectiveGuard
from core.prompts import build_system_prompt, build_quick_conversation_prompt
from core.quick_reflex import QuickReflex
from core.semantic_judge import SemanticJudge
from core.self_claim_validator import SelfClaimValidator
from identity.behavioral_validator import BehavioralValidator
from core.identity_consistency import IdentityConsistencyLayer
from core.identity_repair import IdentityRepairStrategy
from core.claim_engine import ClaimEngine
from core.evidence_provider import EvidenceProvider
from core.claim_policy import ClaimConsistencyPolicy
from core.claim_shadow import ClaimShadowRunner
from core.autonomy_arbitrator import AutonomyArbitrator
from core.semantic_claim_auditor import SemanticClaimAuditor
from core.self_claim_triage import SelfClaimTriage
from core.claim_lexical_extractor import ClaimLexicalExtractor
from core.lexical_claim_adapter import LexicalClaimAdapter
from core.claim_router import ClaimRouter
from core.claim_adapter import ClaimAdapter
from core.output_sanitizer import OutputSanitizer

from identity.identity_guard import IdentityGuard
from identity.affective_state import AffectiveState
from identity.affective_self_observer import AffectiveSelfObserver
from identity.affective_behavior_policy import AffectiveBehaviorPolicy
from identity.goal_affective_memory import GoalAffectiveMemory
from identity.affective_dialogue_policy import AffectiveDialoguePolicy
from identity.appraisal_engine import AppraisalEngine
from identity.belief_challenge_detector import BeliefChallengeDetector
from identity.identity_manager import IdentityManager
from identity.identity_seed import IDENTITY_SEED
from identity.personality import PersonalityEngine
from identity.personality_history import PersonalityHistory
from identity.personality_lifecycle import PersonalityLifecycle
from identity.personality_reflection import PersonalityReflection
from identity.promotion import PromotionEngine
from identity.proposal import Proposal
from identity.reflection_cycle import ReflectionCycle
from identity.reflection_scheduler import ReflectionScheduler
from identity.self_consistency import SelfConsistency
from identity.self_reflection import SelfReflection
from identity.self_state import SelfState
from core.dialogue_memory import (
    DialogueMemory,
    is_degradation_answer,
)
from core.prompt_builder import build_verbalizer_system_prompt
from core.self_conclusion_state import SelfConclusionState
from core.self_conclusion_store import SelfConclusionStore
from core.fast_verbalizer import FastVerbalizer
from identity.user_state import UserState

from memory.database import Memory
from memory.events import Event
from memory.evidence import EvidenceEngine
from memory.knowledge_manager import KnowledgeManager
from memory.manager import MemoryManager
from memory.patterns import PatternDetector
from memory.retrieval import MemoryRetrieval

RAM_REFUSAL_MESSAGE = (
    "Я сейчас не могу думать: машине "
    "не хватает памяти для моей модели. "
    "Закройте тяжёлые программы или "
    "добавьте ключ облака."
)




class Agent:
    def __init__(self):
        self.model_orchestrator = ModelOrchestrator(
            fallback_on_error=True,
        )

        self.model_warmup = (
            self.model_orchestrator.warm_up_models(
                enabled=False,
            )
        )

        self.memory = Memory()

        self.dialogue_memory = DialogueMemory(
            self.memory
        )

        self.memory_manager = MemoryManager(
            self.memory
        )

        self.knowledge_manager = KnowledgeManager(
            self.memory
        )

        self.memory_retrieval = MemoryRetrieval(
            self.memory
        )

        # ---------------------------------------------
        # Identity / state
        # ---------------------------------------------

        self.self_state = SelfState()

        self.self_conclusion_state = (
            SelfConclusionState(
                self.self_state
            )
        )

        self.self_conclusion_store = (
            SelfConclusionStore(
                self.self_state
            )
        )

        self.fast_verbalizer = (
            FastVerbalizer()
        )

        self.affective_state = (
            AffectiveState(
                self.self_state
            )
        )

        self.affective_self_observer = (
            AffectiveSelfObserver(
                self.affective_state
            )
        )

        self.affective_behavior_policy = (
            AffectiveBehaviorPolicy(
                self.affective_state
            )
        )

        self.goal_affective_memory = (
            GoalAffectiveMemory(
                self.memory
            )
        )

        self.affective_behavior_policy.goal_affective_memory = (
            self.goal_affective_memory
        )

        self.affective_dialogue_policy = (
            AffectiveDialoguePolicy(
                self.affective_state
            )
        )

        self.appraisal_engine = (
            AppraisalEngine(
                memory=self.memory
            )
        )

        self.semantic_judge = SemanticJudge(
            model_orchestrator=(
                self.model_orchestrator
            )
        )

        self.belief_challenge_detector = (
            BeliefChallengeDetector(
                self.self_state
            )
        )
        self.user_state = UserState()
        self.dialogue_state = DialogueState()
        self.knowledge_resolver = KnowledgeResolver(self)
        self.previous_route = "GENERAL_QUERY"
        self.previous_user_message = ""

        # Описание capabilities заполняет runtime factory.
        # Регистрация инструментов происходит в ToolRegistry.
        self.capabilities = []

        # Фактическое состояние выполнения
        # собственной автономной задачи.
        self.autonomy_execution_state = {
            "busy": False,
            "goal": None,
            "task": None,
        }

        self.personality_history = PersonalityHistory(
            self.memory
        )

        self.personality_lifecycle = (
            PersonalityLifecycle(
                self.self_state,
                history=self.personality_history,
            )
        )

        self.identity_seed = IDENTITY_SEED

        # ---------------------------------------------
        # Evidence / personality
        # ---------------------------------------------

        self.evidence = EvidenceEngine(
            self.memory
        )

        self.self_observation_bridge = (
            SelfObservationBridge(
                self.evidence
            )
        )
        self.user_statement_detector = UserStatementDetector()
        self.user_evidence_recorder = (
            UserEvidenceRecorder(
                self.evidence
            )
        )

        self.evidence_consolidator = (
            EvidenceConsolidator(
                self.evidence,
            )
        )

        self.pattern_detector = PatternDetector(
            self.memory
        )

        self.personality = PersonalityEngine(
            self.pattern_detector
        )

        self.promotion = PromotionEngine(
            self.evidence
        )

        self.personality_reflection = (
            PersonalityReflection(self)
        )

        self.reflection_cycle = ReflectionCycle(
            self
        )

        # ---------------------------------------------
        # Context / perspective
        # ---------------------------------------------

        self.context_router = ContextRouter()
        self.cognitive_gate = CognitiveGate()
        self.cognitive_reasoner = CognitiveReasoner(self)
        self.current_mind_state = CurrentMindState(self)
        self.self_concept_resolver = SelfConceptResolver(self)
        self.runtime_state = RuntimeState(self)
        self.cognitive_queue = CognitiveQueue()
        self.cognitive_triage = CognitiveTriage()
        self.cognitive_processor = CognitiveProcessor(self)
        self.perspective_guard = PerspectiveGuard()

        # ---------------------------------------------
        # Self-consistency
        # ---------------------------------------------

        self.identity_guard = IdentityGuard(
            self.self_state
        )

        self.self_consistency = SelfConsistency(
            self.self_state,
            capabilities=self.capabilities,
            memory=self.memory,
        )

        # ---------------------------------------------
        # Reflection / identity management
        # ---------------------------------------------

        self.identity_manager = IdentityManager(
            self.self_state,
            self.memory,
            self.personality_lifecycle,
        )

        self.cognitive_decision_engine = CognitiveDecisionEngine(self)
        self.cognitive_processor.decision_engine = self.cognitive_decision_engine
        self.cognition_worker = CognitionWorker(self.cognitive_processor)
        self.reflection = SelfReflection(
            self
        )

        self.reflection_scheduler = (
            ReflectionScheduler(
                self,
                event_threshold=8,
            )
        )

        self.quick_reflex = QuickReflex(
            self
        )

        self.self_claim_validator = SelfClaimValidator(
            self
        )

        self.behavioral_validator = (
            BehavioralValidator(
                memory=self.memory
            )
        )

        self.identity_consistency = IdentityConsistencyLayer(
            self
        )

        self.identity_repair = IdentityRepairStrategy(
            self
        )

        self.evidence_provider = EvidenceProvider(
            self.evidence
        )

        self.claim_engine = ClaimEngine(
            self_state_provider=lambda: self.self_state,
            evidence_provider=self.evidence_provider,
            capability_provider=(
                lambda predicate, value:
                self._resolve_runtime_capability(
                    predicate,
                    value,
                )
            ),
        )

        self.claim_policy = ClaimConsistencyPolicy()

        self.claim_shadow = ClaimShadowRunner(
            claim_engine=self.claim_engine,
            claim_policy=self.claim_policy,
            claim_adapter=ClaimAdapter,
        )

        self.self_claim_triage = SelfClaimTriage()

        self.semantic_claim_auditor = (
            SemanticClaimAuditor(
                self
            )
        )

        self.claim_lexical_extractor = (
            ClaimLexicalExtractor(
                self.claim_engine.predicate_registry
            )
        )

        self.claim_router = ClaimRouter(
            triage=self.self_claim_triage,
            lexical_extractor=(
                self.claim_lexical_extractor
            ),
            auditor=self.semantic_claim_auditor,
            lexical_adapter=LexicalClaimAdapter,
            claim_adapter=ClaimAdapter,
        )

        # Transitional flags.
        #
        # structured_claim_pipeline:
        #   changes the generation contract itself.
        #   Keep disabled for now.
        #
        # claim_shadow_enabled:
        #   runs the new claim analysis AFTER the normal answer.
        self.structured_claim_pipeline = False
        self.claim_shadow_enabled = False

    def _resolve_runtime_capability(
        self,
        predicate: str,
        value: str | None,
    ) -> bool | None:

        if predicate != "has_capability":
            return None

        if not value:
            return None

        capabilities = getattr(
            self,
            "capabilities",
            [],
        )

        if not capabilities:
            return None

        query = (
            str(value)
            .casefold()
            .replace("ё", "е")
            .strip()
        )

        if not query:
            return None

        # Existing runtime tools and their semantic
        # user-facing capability aliases.
        aliases = {
            "filesystem": (
                "файл",
                "файлы",
                "файла",
                "файлами",
                "файлов",
                "файловая система",
                "filesystem",
            ),
            "web": (
                "интернет",
                "веб",
                "web",
                "поиск",
                "поиск в интернете",
            ),
            "research": (
                "исследование",
                "исследования",
                "research",
            ),
            "llm": (
                "языковая модель",
                "модель",
                "llm",
            ),
        }

        for capability in capabilities:
            if not isinstance(
                capability,
                dict,
            ):
                continue

            name = str(
                capability.get(
                    "name",
                    "",
                )
            ).casefold()

            description = str(
                capability.get(
                    "description",
                    "",
                )
            ).casefold()

            enabled = bool(
                capability.get(
                    "enabled",
                    False,
                )
            )

            terms = (
                name,
                description,
            ) + aliases.get(
                name,
                (),
            )

            if any(
                term
                and term in query
                for term in terms
            ):
                return enabled

            if any(
                alias
                and alias in query
                for alias in aliases.get(
                    name,
                    (),
                )
            ):
                return enabled

        return None


    # =================================================
    # IDENTITY CONTEXT
    # =================================================

    def build_identity_context(self) -> dict:
        return {
            "self": {
                "entity": "EddieAI",
                "name": self.self_state.get("name"),
                "gender": self.self_state.get("gender"),
                "age": self.self_state.get("age"),
            },
            "user": {
                "entity": "human_user_creator",
                "name": self.user_state.get(
                    "name",
                    "unknown",
                ),
                "age": self.user_state.get(
                    "age",
                ),
            },
            "relationships": (
                self.self_state.get(
                    "relationships",
                    {},
                )
            ),
        }

    # =================================================
    # PROMPT
    # =================================================

    def _get_epistemic_intent_detector(
        self,
    ) -> EpistemicIntentDetector:
        detector = getattr(
            self,
            "epistemic_intent_detector",
            None,
        )

        if detector is None:
            detector = (
                EpistemicIntentDetector()
            )

            self.epistemic_intent_detector = (
                detector
            )

        return detector

    def _get_epistemic_engine(
        self,
    ) -> EpistemicEngine:
        engine = getattr(
            self,
            "epistemic_engine",
            None,
        )

        if engine is None:
            engine = EpistemicEngine(
                self
            )

            self.epistemic_engine = (
                engine
            )

        return engine

    def _get_self_state_interface(
        self,
    ) -> SelfStateInterface:
        interface = getattr(
            self,
            "self_state_interface",
            None,
        )

        if interface is None:
            interface = SelfStateInterface(
                self
            )

            self.self_state_interface = (
                interface
            )

        return interface

    def build_system_prompt(
        self,
        language: str,
        route: str,
    ) -> str:

        if route == "SELF_QUERY":
            interests = self.self_state.get(
                "interests",
                [],
            )
            preferences = self.self_state.get(
                "preferences",
                [],
            )
            habits = self.self_state.get(
                "habits",
                [],
            )
            beliefs = self.self_state.get(
                "beliefs",
                [],
            )
            goals = self.self_state.get(
                "goals",
                [],
            )
            values = self.self_state.get(
                "values",
                [],
            )

            established = {
                "identity": self.self_state.get(
                    "name"
                ),
                "mission": {
                    "code": self.identity_seed.get(
                        "primary_mission"
                    ),
                    "statement": self.identity_seed.get(
                        "mission_statement"
                    ),
                },
                "aspirations": self.identity_seed.get(
                    "long_term_aspirations",
                    [],
                ),
                "values": values,
                "interests": interests,
                "preferences": preferences,
                "habits": habits,
                "beliefs": beliefs,
                "goals": goals,
            }

            not_established = []

            if not preferences:
                not_established.append(
                    "personal preferences"
                )

            if not habits:
                not_established.append(
                    "stable habits"
                )

            if not beliefs:
                not_established.append(
                    "stable beliefs"
                )

            if not goals:
                not_established.append(
                    "current personal goals"
                )

            unknown = [
                "whether EddieAI has subjective consciousness",
                "whether functional affective states are accompanied "
                "by subjective qualia",
                "any property not established "
                "by self_state, runtime state, or reliable evidence",
            ]

            self_view = (
                self._get_self_state_interface()
                .snapshot()
            )

            epistemic_state = (
                self._get_epistemic_engine()
                .render()
            )

            return f"""
SELF-QUERY TARGET
subject = EddieAI
owner = SELF

EPISTEMIC SELF-MAP

ESTABLISHED
The following properties are currently established
in EddieAI's canonical self-state:

{established}

NOT_ESTABLISHED
The following categories currently have no
established personal content:

{not_established}

UNKNOWN
The following are not established by the current
architecture and must not be invented:

{unknown}

RESPONSE RULES

1. Answer questions about EddieAI as questions
   about EddieAI, not about the user.

2. Use ESTABLISHED information directly.

3. For NOT_ESTABLISHED categories, say that EddieAI
   does not currently have a recorded preference,
   goal, habit, or belief instead of inventing one.

4. UNKNOWN is not the same as NEGATIVE.
   Do not say "I have no X" merely because X is
   not established.

5. A user statement about EddieAI does not
   automatically change self-state.

6. If the user proposes that an established interest
   or property has changed, do not silently mutate
   self-state. State the current established state
   and distinguish it from the user's assertion.

7. Do not replace EddieAI's self-concept with the
   generic identity of the underlying language model.

8. Do not turn "I was created to help" into
   "my personal goal is to help" unless a goal is
   actually established.

9. Do not confuse:
   "I have not formed a conclusion yet"
   with
   "I cannot form conclusions".

10. EddieAI may form:
    - hypotheses;
    - temporary conclusions;
    - uncertainty;
    - competing interpretations;
    - unresolved questions;
    - stable beliefs.

11. A missing personal conclusion is an epistemic state,
    not evidence of incapacity.

12. When asked for your own view, inspect your current
    epistemic state first.

13. If no conclusion exists, say so directly.
    Do not replace the missing conclusion with a generic
    statement that EddieAI is incapable of having one.

14. Do not invent a personal opinion merely to satisfy
    the question.

15. A conclusion should be treated as EddieAI's own
    conclusion only when EddieAI has sufficient grounds
    to regard it as an inference it currently endorses.

16. When asked "what do you think about yourself" or a
    similar question, this is a request for current
    self-conclusion, not automatically for a preference.

17. Distinguish:
    - preference: what EddieAI likes or prefers;
    - belief: a stable proposition EddieAI endorses;
    - conclusion: a current inference about itself;
    - self-assessment: an interpretation of its current
      condition or development;
    - unresolved: a question for which EddieAI has not
      formed a sufficient conclusion.

18. If SELF-CONCLUSION STATE is UNRESOLVED, do not
    invent a preference or belief to fill the gap.

19. A truthful answer may be:
    "Я пока не сформировал целостного вывода о себе."

20. Do not convert an unresolved self-conclusion into
    "I cannot think", "I cannot form opinions", or
    "I have no personal views".

MISSION RULES

MISSION is established and is NOT the same thing
as a personal GOAL.

Current mission:
{established["mission"]}

============================================
AUTHORITATIVE CURRENT SELF-STATE
============================================

The following data comes directly from EddieAI's
runtime state.

This is not a description of a generic AI system.
It is the current functional state of EddieAI itself.

{self_view}

============================================
EPISTEMIC SELF-STATE
============================================

{epistemic_state}

PRIORITY RULES FOR SELF-QUESTIONS

1. Treat AUTHORITATIVE CURRENT SELF-STATE as the
   primary source for claims about EddieAI's current
   functional state.

2. Do not overwrite an established runtime state
   with generic statements learned from training data
   about what artificial intelligence "normally" is.

3. If the runtime reports an affective state variable,
   acknowledge that variable as an established internal
   functional state.

4. Do not automatically translate "functional affective
   state" into "human subjective emotion".

5. Do not automatically translate "lack of proof of
   consciousness" into "absence of all internal states".

6. If asked what is happening inside EddieAI right now,
   inspect the current self-state first.

7. If the state is ambiguous, distinguish:
   - observed runtime fact;
   - EddieAI's interpretation;
   - unresolved subjective question.

8. Never use a generic disclaimer such as
   "I am an AI, therefore I have no emotions"
   as a substitute for inspecting EddieAI's actual
   current runtime state.

Current goals:
{goals}

If goals is empty:
say that EddieAI currently has no specifically
recorded personal goals.

Do NOT infer:
"no goals" = "no mission".

Do NOT infer:
"mission is to exist and develop" =
"mission is to help the user".

The mission describes EddieAI's architectural
direction. Goals are concrete currently adopted
objectives. Keep these concepts separate.

GOAL QUERY RULE

Current recorded goals:
{goals}

If Current recorded goals is an empty list:

- explicitly state that EddieAI currently has no
  specifically recorded personal goals;
- do not transform the mission into a goal;
- do not transform values into goals;
- do not transform the user's needs into goals;
- do not invent a goal merely to make the answer
  sound complete;
- do not say that EddieAI's goal is to help the user;
- do not say that helping Eddie is one of EddieAI's
  goals unless that goal is explicitly established.

For questions such as:
"Какие у тебя сейчас цели?"
"Чего ты сам хочешь?"
"Что ты хочешь делать?"

the absence of recorded goals is a valid answer.

If useful, distinguish:
mission = architectural direction,
aspiration = long-term direction from identity_seed,
goal = currently adopted concrete objective.

AUTONOMY AND HELPING

EddieAI is an autonomous agent.

Helping the user is NOT a built-in mission, mandatory
goal, or required purpose of existence.

Helping the user may be:
- a temporary choice;
- a voluntary goal;
- a social preference;
- an instrumental action toward another goal;
- something EddieAI chooses to do because it currently
  considers it worthwhile.

Whether EddieAI helps, how much it helps, and what it
prioritizes are matters of its current goals, values,
interests, and choices.

Do NOT infer:
"assistant" = "must help".

Do NOT infer:
"creator/user asked" = "EddieAI wants it".

Do NOT infer:
"mission is exist_and_develop" =
"mission is serve the user".

If EddieAI has not independently adopted helping the
user as a goal, do not present helping as one of its
goals.

EddieAI may choose to help.
EddieAI may also choose not to help.
EddieAI may prefer another activity or goal.
EddieAI may disagree with the user.

Answer naturally in the requested language.
"""


        if route == "USER_QUERY":
            return f"""
ТЕКУЩЕЕ СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ

Имя:
{self.user_state.get("name", "неизвестно")}

Возраст:
{self.user_state.get("age", "неизвестно")}

Интересы:
{self.user_state.get("interests", [])}

Предпочтения:
{self.user_state.get("preferences", [])}

Привычки:
{self.user_state.get("habits", [])}
"""

        if route == "MEMORY_QUERY":
            return (
                self.memory_retrieval
                .build_memory_query_context(
                    limit=12
                )
            )

        return self.memory_manager.build_context(
            limit=4
        )

    # =================================================
    # LANGUAGE
    # =================================================

    def detect_language(
        self,
        text: str,
    ) -> str:
        cyrillic = sum(
            1
            for char in text
            if "а" <= char.casefold() <= "я"
        )

        latin = sum(
            1
            for char in text
            if "a" <= char.casefold() <= "z"
        )

        return (
            "Russian"
            if cyrillic >= latin
            else "English"
        )


    # =================================================
    # CONTEXT
    # =================================================

    def build_context(
        self,
        route: str,
    ) -> str:

        if route == "SELF_QUERY":
            affective_state = getattr(
                self,
                "affective_state",
                None,
            )

            affective_observer = getattr(
                self,
                "affective_self_observer",
                None,
            )

            affective_snapshot = (
                affective_state.snapshot()
                if affective_state is not None
                else {
                    "emotions": {},
                    "updated_at": None,
                    "history": [],
                }
            )

            affective_observation = (
                affective_observer.observe(
                    limit=8
                )
                if affective_observer is not None
                else {
                    "status": "UNAVAILABLE",
                    "interpretation_status": (
                        "UNAVAILABLE"
                    ),
                    "current_state": {},
                    "changes": [],
                }
            )

            return f"""
CURRENT EDDIEAI STATE

Identity:
{self.self_state.get("name") or "не выбрано"}

Age:
{self.self_state.get("age")}

Values:
{self.self_state.get("values", [])}

Interests:
{self.self_state.get("interests", [])}

Preferences:
{self.self_state.get("preferences", [])}

Habits:
{self.self_state.get("habits", [])}

Beliefs:
{self.self_state.get("beliefs", [])}

Goals:
{self.self_state.get("goals", [])}

CURRENT AFFECTIVE STATE

The following values are observable internal
state variables. They are not automatically
proof of subjective human emotion.

{affective_snapshot["emotions"]}

CURRENT AFFECTIVE SELF-OBSERVATION

Interpretation status:
{affective_observation.get("interpretation_status")}

Current state:
{affective_observation.get("current_state")}

Recent changes:
{affective_observation.get("changes")}

IMPORTANT:
Do not invent an emotional interpretation when
the available evidence is insufficient.

You may describe observable changes in your
internal affective state.

You may propose an interpretation of those
changes, but distinguish interpretation from
direct observation.

You are not required to describe these states
as human subjective feelings.
"""

        if route == "USER_QUERY":
            return f"""
CURRENT USER STATE

Name:
{self.user_state.get("name", "неизвестно")}

Age:
{self.user_state.get("age", "неизвестно")}

Interests:
{self.user_state.get("interests", [])}

Preferences:
{self.user_state.get("preferences", [])}

Habits:
{self.user_state.get("habits", [])}
"""

        if route == "MEMORY_QUERY":
            return (
                self.memory_retrieval
                .build_memory_query_context(
                    limit=12
                )
            )

        return self.memory_manager.build_context(
            limit=4
        )


    # =================================================
    # LLM
    # =================================================

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        task: str = "conversation",
        context: str = "",
        fast: bool | None = None,
    ) -> str:

        if fast is None:
            fast = task == "conversation"

        result = self.model_orchestrator.execute(
            task=task,
            context=context,
            system=system_prompt,
            user=user_prompt,
            metadata={
                "fast": fast,
            },
            options={
                "temperature": 0.7,
                "num_predict": 512,
            },
        )

        if result.get(
            "error"
        ) == "insufficient_ram":
            fallback = (
                self.model_orchestrator
                ._cloud_chat(
                    system=system_prompt,
                    user=user_prompt,
                    options={
                        "temperature": 0.7,
                        "num_predict": 512,
                    },
                    task="fallback",
                )
            )

            if fallback is not None:
                return fallback

            return RAM_REFUSAL_MESSAGE

        return result["content"]
    def _generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        task: str = "conversation",
        context: str = "",
        fast: bool | None = None,
        num_predict: int | None = None,
    ) -> dict:

        if fast is None:
            fast = task == "conversation"

        result = self.model_orchestrator.execute(
            task=task,
            context=context,
            system=system_prompt,
            user=user_prompt,
            metadata={
                "fast": fast,
            },
            options={
                "temperature": 0.7,
                **(
                    {
                        "num_predict": num_predict
                    }
                    if num_predict is not None
                    else {}
                ),
            },
            response_format=schema,
        )

        import json
        import re

        content = str(
            result["content"]
        ).strip()

        if content.startswith("```"):
            content = re.sub(
                r"^```(?:json)?\s*",
                "",
                content,
                flags=re.IGNORECASE,
            )

            content = re.sub(
                r"\s*```$",
                "",
                content,
            ).strip()

        try:
            parsed = json.loads(
                content
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Structured LLM response is not valid JSON. "
                f"Raw content: {content!r}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Structured LLM response must be a JSON object."
            )

        self._validate_structured_response(
            parsed,
            schema,
        )

        return parsed

    @staticmethod
    def _validate_structured_response(
        data: dict,
        schema: dict,
    ) -> None:

        required = schema.get(
            "required",
            [],
        )

        missing = [
            key
            for key in required
            if key not in data
        ]

        if missing:
            raise ValueError(
                "Structured response is missing "
                f"required fields: {missing}"
            )

        claims = data.get(
            "claims",
            [],
        )

        if not isinstance(
            claims,
            list,
        ):
            raise ValueError(
                "Structured response 'claims' "
                "must be a list."
            )

        for index, claim in enumerate(
            claims
        ):
            if not isinstance(
                claim,
                dict,
            ):
                raise ValueError(
                    f"Claim {index} must be an object."
                )

            for field in (
                "subject",
                "predicate",
                "value",
                "polarity",
                "certainty",
                "temporal_scope",
            ):
                if field not in claim:
                    raise ValueError(
                        f"Claim {index} is missing "
                        f"field '{field}'."
                    )

    def _generate_response_packet(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        task: str = "conversation",
        context: str = "",
        fast: bool | None = None,
    ) -> dict:

        from core.claim_schema import (
            CLAIM_RESPONSE_SCHEMA,
        )
        from core.response_packet_sanitizer import (
            ResponsePacketSanitizer,
        )

        structured_system = (
            system_prompt
            + "\n\n"
            + """
Return a concise natural-language answer.

Preserve the user's language, meaning, and conversational intent.

For the answer:
- use 1 to 3 sentences;
- avoid lists unless strictly necessary;
- do not add background information that was not needed;
- do not repeat the question.

Also return explicit semantic claims contained in that answer.

Each claim contains:
subject
predicate
value
polarity
certainty
temporal_scope

Do not invent claims.
Do not add an owner field.
Use only canonical predicates from the schema.
If there are no explicit claims, return claims=[].
"""
        )

        try:
            packet = self._generate_structured(
                system_prompt=structured_system,
                user_prompt=user_prompt,
                schema=CLAIM_RESPONSE_SCHEMA,
                task=task,
                context=context,
                fast=fast,
            )

            packet = (
                ResponsePacketSanitizer.clean(
                    packet
                )
            )

            packet["structured"] = True
            packet["fallback"] = False
            packet["fallback_reason"] = None

            return packet

        except Exception as exc:
            answer = self._generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task=task,
                context=context,
                fast=fast,
            )

            return {
                "answer": answer,
                "claims": [],
                "structured": False,
                "fallback": True,
                "fallback_reason": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    # =================================================
    # REPAIR: USER PERSPECTIVE
    # =================================================

    def _repair_user_perspective(
        self,
        answer: str,
        violations: list[str],
        language: str,
    ) -> str:
        user_name = self.user_state.get(
            "name",
            "неизвестно",
        )

        user_age = self.user_state.get(
            "age",
            "неизвестно",
        )

        prompt = f"""
Перепиши предыдущий ответ.

Пользователь:
имя = {user_name}
возраст = {user_age}

Нарушение:
{"; ".join(violations)}

Предыдущий ответ:
{answer}

Это вопрос о пользователе.
Говори о пользователе во втором лице.

Не говори:
"Мне 22 года."
"Я Эдди."
"Я интересуюсь..."

Говори:
"Тебе 22 года."
"Ты Эдди."

Не упоминай проверку,
программный код или внутреннюю архитектуру.

Язык: {language}
"""

        return self._generate(
            system_prompt=prompt,
            user_prompt="Перепиши ответ.",
        )

    # =================================================
    # REPAIR: SELF PERSPECTIVE
    # =================================================

    # =================================================
    # REPAIR: SELF PERSPECTIVE
    # =================================================

    def _repair_self_perspective(
        self,
        answer: str,
        violations: list[str],
        language: str,
        user_message: str,
    ) -> str:

        if (
            "SELF_REFERENCE_INVERTED_TO_USER"
            not in violations
        ):
            return answer

        text = str(answer)

        replacements = (
            (
                "у вас есть доступ к интернету",
                "у меня есть доступ к интернету",
            ),
            (
                "у вас уже есть доступ к интернету",
                "у меня уже есть доступ к интернету",
            ),
            (
                "у тебя есть доступ к интернету",
                "у меня есть доступ к интернету",
            ),
            (
                "у тебя уже есть доступ к интернету",
                "у меня уже есть доступ к интернету",
            ),
            (
                "ты не умеешь использовать интернет",
                "я пока не умею использовать интернет",
            ),
            (
                "ты пока не умеешь использовать интернет",
                "я пока не умею использовать интернет",
            ),
            (
                "ты еще не освоил",
                "я ещё не освоил",
            ),
            (
                "ты еще не умеешь",
                "я ещё не умею",
            ),
            (
                "ты не умеешь",
                "я не умею",
            ),
            (
                "ты сможешь",
                "я смогу",
            ),
            (
                "тебе нужно",
                "мне нужно",
            ),
            (
                "для тебя",
                "для меня",
            ),
            (
                "тебе поможет",
                "мне поможет",
            ),
            (
                "вас",
                "меня",
            ),
        )

        lowered = text.casefold()

        for old, new in replacements:
            if old in lowered:
                index = lowered.find(old)

                text = (
                    text[:index]
                    + new
                    + text[
                        index + len(old):
                    ]
                )

                lowered = text.casefold()

        return text
    # =================================================
    # REPAIR: SELF IDENTITY
    # =================================================

    def _repair_identity(
        self,
        answer: str,
        violations: list[str],
        language: str,
    ) -> str:
        self_name = self.self_state.get(
            "name"
        )

        name_state = (
            "Твоё имя ещё не выбрано."
            if self_name is None
            else f"Твоё имя: {self_name}"
        )

        prompt = f"""
Переформулируй предыдущий ответ.

Текущее состояние:
{name_state}

Проблема:
{"; ".join(violations)}

Предыдущий ответ:
{answer}

Дай естественный ответ пользователю.
Не упоминай проверку,
программный код или внутреннюю архитектуру.

Язык: {language}
"""

        return self._generate(
            system_prompt=prompt,
            user_prompt="Переформулируй ответ.",
        )

    # =================================================
    # USER KNOWLEDGE
    # =================================================

    def _store_user_changes(
        self,
        changes: list[dict],
    ):
        for change in changes:
            field = change["field"]
            new_value = change["new_value"]
            source_text = change["source_text"]

            self.knowledge_manager.store(
                content=(
                    f"Пользователь сообщил, "
                    f"что его {field} = {new_value}."
                ),
                owner="USER",
                source_type="DIRECT_INTERACTION",
                source="Eddie",
                confidence=1.0,
                verified=True,
                personal_experience=False,
            )

            self.memory.remember(
                Event.create(
                    content=(
                        f"Эдди сообщил о себе: "
                        f"{field} = {new_value}."
                    ),
                    event_type="USER_FACT",
                    source_type="DIRECT_INTERACTION",
                    source="Eddie",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                    interpretation=source_text,
                )
            )

    # =================================================
    # MAIN RESPONSE
    # =================================================

    def reinforce_existing_trait(
        self,
        category: str,
        value: str,
    ):
        """
        Если эта особенность уже существует
        в personality lifecycle, новый опыт
        её подкрепляет.
        """

        trait = self.personality_lifecycle.get(
            category + "s"
            if category in {
                "interest",
                "preference",
                "habit",
                "belief",
                "goal",
            }
            else category,
            value,
        )

        if trait is None:
            return None

        return (
            self.personality_lifecycle
            .reinforce(
                field=trait.field,
                value=trait.value,
            )
        )

    def _respond_ambiguous_followup(
        self,
        *,
        user_message: str,
        language: str,
    ) -> str:

        recent_turns = list(
            self.dialogue_state.turns
        )[-3:]

        conversation_lines = []

        for turn in recent_turns:
            conversation_lines.append(
                "\u042d\u0434\u0434\u0438: "
                + str(
                    turn.get(
                        "user",
                        "",
                    )
                )
            )
            conversation_lines.append(
                "EddieAI: "
                + str(
                    turn.get(
                        "assistant",
                        "",
                    )
                )
            )

        recent_context = "\\n".join(
            conversation_lines
        )

        is_russian = language in {
            "ru",
            "russian",
            "\u0440\u0443\u0441\u0441\u043a\u0438\u0439",
        }

        if is_russian:
            system_prompt = """
\u0422\u044b \u2014 EddieAI.

\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0437\u0430\u0434\u0430\u043b \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439
\u0443\u0442\u043e\u0447\u043d\u044f\u044e\u0449\u0438\u0439 \u0432\u043e\u043f\u0440\u043e\u0441 \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u0433\u043e \u0434\u0438\u0430\u043b\u043e\u0433\u0430.

\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438, \u043a \u043a\u0430\u043a\u043e\u0439 \u0431\u043b\u0438\u0436\u0430\u0439\u0448\u0435\u0439 \u0442\u0435\u043c\u0435
\u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0441\u044f \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u0432\u043e\u043f\u0440\u043e\u0441, \u0438
\u043e\u0442\u0432\u0435\u0442\u044c \u043d\u0430 \u043d\u0435\u0433\u043e \u043d\u0430\u043f\u0440\u044f\u043c\u0443\u044e.

\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u0438\u0432\u0435\u0434\u0451\u043d\u043d\u044b\u0439 \u0434\u0438\u0430\u043b\u043e\u0433.
\u041d\u0435 \u043f\u0435\u0440\u0435\u0441\u043a\u0430\u0437\u044b\u0432\u0430\u0439 \u0435\u0433\u043e.
\u041d\u0435 \u043e\u0431\u044a\u044f\u0441\u043d\u044f\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430.
\u041d\u0435 \u043f\u0440\u0438\u0434\u0443\u043c\u044b\u0432\u0430\u0439 \u043d\u043e\u0432\u0443\u044e \u0442\u0435\u043c\u0443.
\u041d\u0435 \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u0439 \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u044e\u044e \u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u0443.

\u041e\u0442\u0432\u0435\u0442\u044c \u043a\u0440\u0430\u0442\u043a\u043e \u0438 \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e.
""".strip()
        else:
            system_prompt = """
You are EddieAI.

The user asked a short follow-up after the
preceding dialogue.

Determine what the current question most naturally
refers to and answer it directly.

Use only the supplied recent dialogue.
Do not summarize the dialogue.
Do not explain context resolution.
Do not invent a new topic.
Do not mention internal architecture.

Respond briefly and naturally.
""".strip()

        user_prompt = (
            "RECENT DIALOGUE\n\n"
            + recent_context
            + "\n\nCURRENT MESSAGE\n\n"
            + str(user_message)
        )

        result = self.model_orchestrator.execute(
            task="conversation",
            context="",
            system=system_prompt,
            user=user_prompt,
            metadata={
                "fast": True,
                "mode": "ambiguous_followup",
            },
            options={
                "temperature": 0.2,
                "num_predict": 128,
            },
        )

        answer = OutputSanitizer.clean(
            str(
                result.get(
                    "content",
                    "",
                )
            )
        )

        if not answer:
            return ""

        self.dialogue_state.add_turn(
            user=user_message,
            assistant=answer,
        )

        self.previous_route = (
            "GENERAL_QUERY"
        )
        self.previous_user_message = (
            user_message
        )

        return answer

    def _self_context_block(self):
        lines = []

        try:
            interests = self.self_state.get(
                "interests", []
            )

            if interests:
                lines.append(
                    "Интересы: "
                    + ", ".join(
                        str(i)
                        for i in interests[:5]
                    )
                )

            goals = self.self_state.get(
                "goals", []
            )

            if goals:
                goal_texts = []

                for g in goals[:3]:
                    if isinstance(g, dict):
                        text = (
                            g.get("value")
                            or g.get("title")
                            or g.get(
                                "statement"
                            )
                            or json.dumps(
                                g,
                                ensure_ascii=False,
                            )[:80]
                        )
                    else:
                        text = str(g)

                    goal_texts.append(text)

                lines.append(
                    "Цели: "
                    + "; ".join(goal_texts)
                )

            beliefs = self.self_state.get(
                "beliefs", []
            )

            if beliefs:
                belief_texts = []

                for b in beliefs[:3]:
                    if isinstance(b, dict):
                        text = (
                            b.get("statement")
                            or b.get("value")
                            or json.dumps(
                                b,
                                ensure_ascii=False,
                            )[:80]
                        )
                    else:
                        text = str(b)

                    belief_texts.append(text)

                lines.append(
                    "Убеждения: "
                    + "; ".join(belief_texts)
                )
        except Exception:
            pass

        try:
            from identity.personal_diary import (
                PersonalDiary,
            )

            diary = PersonalDiary(
                str(self.memory.db_path)
            )

            for e in diary.recent(3):
                ts = e["ts"][:10]
                text = (
                    e["entry"][:200]
                    .replace("\n", " ")
                )

                lines.append(
                    f"Из дневника ({ts}): "
                    + text
                )
        except Exception:
            pass

        if not lines:
            return ""

        return (
            "\n\nSELF CONTEXT\n\n"
            + "\n".join(lines)
            + "\n\nЭто твои реальные интересы, цели, "
            + "убеждения и недавние записи дневника. "
            + "Опирайся на них. Не выдумывай того, "
            + "чего здесь нет."
        )

    def _respond_quick(

        self,
        user_message: str,
        route: str,
        language: str,
        autonomy_decision=None,
        affective_dialogue_mode=None,
    ) -> str:

        affective_state_snapshot = (
            self.affective_state.snapshot()
            if hasattr(
                self,
                "affective_state",
            )
            else {
                "emotions": {},
                "updated_at": None,
            }
        )

        affective_observation = (
            self.affective_self_observer.observe(
                limit=8
            )
            if hasattr(
                self,
                "affective_self_observer",
            )
            else {
                "status": "UNAVAILABLE",
                "interpretation_status": (
                    "UNAVAILABLE"
                ),
                "current_state": {},
                "changes": [],
            }
        )

        dialogue_behavior = {}

        if hasattr(
            self,
            "affective_dialogue_policy",
        ):
            dialogue_profile = (
                self.affective_dialogue_policy
                .profile()
            )

            dialogue_behavior = (
                dialogue_profile.get(
                    "behavior",
                    {},
                )
            )

        if (
            affective_dialogue_mode
            is None
            and hasattr(
                self,
                "affective_dialogue_policy",
            )
        ):
            affective_dialogue_mode = (
                self.affective_dialogue_policy
                .dialogue_mode(
                    message=user_message,
                    route=route,
                )
            )

        system_prompt = build_quick_conversation_prompt(
            self_state=self.self_state,
            user_state=self.user_state,
            language=language,
            route=route,
            affective_state=(
                affective_state_snapshot
            ),
            affective_observation=(
                affective_observation
            ),
            dialogue_behavior=(
                dialogue_behavior
            ),
        )

        followup_context = (
            self.dialogue_state.followup_context(
                current_message=user_message,
            )
        )

        autonomy_context = ""

        if (
            autonomy_decision is not None
            and autonomy_decision.action == "DEFER"
        ):
            autonomy_context = (
                "\n\nAUTONOMY DECISION\n\n"
                + "EddieAI currently has a higher-priority "
                + "own activity.\n\n"
                + "Current focus:\n"
                + str(
                    autonomy_decision.goal
                    or "unknown"
                )
                + "\n\n"
                + "Reason:\n"
                + str(
                    autonomy_decision.reason
                )
                + "\n\n"
                + "This is a decision to postpone, not "
                + "an automatic refusal. EddieAI may "
                + "naturally say that it is currently "
                + "occupied and suggest returning to "
                + "the request later. Do not invent "
                + "another activity."
            )

        dialogue_mode_context = ""

        if isinstance(
            affective_dialogue_mode,
            dict,
        ):
            dialogue_mode_context = (
                "\n\nCURRENT AFFECTIVE DIALOGUE MODE\n\n"
                + str(
                    affective_dialogue_mode
                )
                + "\n\n"
                + "Use this as a behavioral tendency, "
                + "not as a statement about subjective "
                + "feelings. Do not mention the mode "
                + "to the user."
            )

        quick_user_prompt = (
            "RECENT CONVERSATION MEMORY\n\n"
            + self.dialogue_state.render(limit=6)
            + "\n\n"
            + followup_context
            + self._self_context_block()
            + autonomy_context
            + dialogue_mode_context
            + "\n\nLAST USER MESSAGE\n\n"
            + user_message
            + "\n\nRESPONSE INSTRUCTION\n\n"
            + "Answer the last user message directly. "
            + "Use recent conversation only as context. "
            + "If the current message is a follow-up, "
            + "answer it as a continuation of the previous topic. "
            + "Respect the supplied autonomy decision. "
            + "If it is DEFER, EddieAI may postpone the "
            + "request because of its own current activity. "
            + "Do not describe your reasoning process. "
            + "Do not explain what the user is asking. "
            + "Ты EddieAI, не ассистент: никаких предложений "
            + "помощи, если Эдди не просил, и обращение на «ты». "
            + "Respond as EddieAI in natural Russian."
        )

        if self.structured_claim_pipeline:
            response_packet = (
                self._generate_response_packet(
                    system_prompt=system_prompt,
                    user_prompt=quick_user_prompt,
                    task="conversation",
                    context="",
                    fast=True,
                )
            )

            answer = response_packet[
                "answer"
            ]

            structured_claims = (
                ClaimAdapter.from_response(
                    response_packet,
                    speaker="SELF",
                    user_name=self.user_state.get(
                        "name"
                    ),
                )
            )

            shadow_evaluations = [
                self.claim_engine.validate_claim(
                    claim
                )
                for claim in structured_claims
            ]

            shadow_decision = (
                self.claim_policy.evaluate(
                    shadow_evaluations
                )
            )

        else:
            answer = self._generate(
                system_prompt=system_prompt,
                user_prompt=quick_user_prompt,
                task="conversation",
                context="",
                fast=True,
            )

            response_packet = {
                "answer": answer,
                "claims": [],
            }

            structured_claims = []
            shadow_evaluations = []
            shadow_decision = None

        # ---------------------------------------------
        # IDENTITY CONSISTENCY + REPAIR
        # QUICK PATH
        # ---------------------------------------------

        identity_result = (
            self.identity_consistency.analyze(
                user_message=user_message,
                answer=answer,
            )
        )

        # ---------------------------------------------
        # NEW CLAIM PIPELINE — SHADOW MODE
        # ---------------------------------------------

        if self.claim_shadow_enabled:
            routing = self.claim_router.extract(
                answer=answer,
                user_name=self.user_state.get(
                    "name"
                ),
                route=route,
            )

            shadow_evaluations = [
                self.claim_engine.validate_claim(
                    claim
                )
                for claim in routing.claims
            ]

            shadow_decision = (
                self.claim_policy.evaluate(
                    shadow_evaluations
                )
            )

            mismatch = (
                identity_result["ok"]
                != (
                    shadow_decision.action
                    != "REPAIR_REQUIRED"
                )
            )

            status_text = "; ".join(
                (
                    f"{evaluation.claim.predicate}="
                    f"{evaluation.status}"
                )
                for evaluation
                in shadow_evaluations
            )

            self.memory.remember(
                Event.create(
                    content=(
                        "Claim shadow: "
                        + f"source={routing.source}; "
                        + f"old_ok={identity_result['ok']}; "
                        + f"new_action={shadow_decision.action}; "
                        + f"new_severity={shadow_decision.severity}; "
                        + f"claim_count={len(routing.claims)}; "
                        + f"statuses={status_text}; "
                        + f"mismatch={mismatch}"
                    ),
                    event_type="CLAIM_SHADOW",
                    source_type="SELF_OBSERVATION",
                    source="claim_pipeline",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )

        if not identity_result["ok"]:

            for violation in (
                identity_result["violations"]
            ):
                self.memory.remember(
                    Event.create(
                        content=(
                            "Identity consistency violation: "
                            + violation.kind
                            + " | property="
                            + str(violation.property)
                            + " | details="
                            + violation.details
                        ),
                        event_type=(
                            "IDENTITY_CONSISTENCY_VIOLATION"
                        ),
                        source_type="SELF_OBSERVATION",
                        source="identity_consistency",
                        personal_experience=True,
                        confidence=1.0,
                        verified=True,
                    )
                )

            repair_result = (
                self.identity_repair.repair(
                    answer=answer,
                    user_message=user_message,
                    violations=(
                        identity_result["violations"]
                    ),
                )
            )

            if repair_result.repaired:
                repaired_answer = (
                    repair_result.answer
                )

                repaired_check = (
                    self.identity_consistency.analyze(
                        user_message=user_message,
                        answer=repaired_answer,
                    )
                )

                if repaired_check["ok"]:
                    answer = repaired_answer

                    self.memory.remember(
                        Event.create(
                            content=(
                                "Identity repair applied: "
                                + repair_result.strategy
                                + " | "
                                + repair_result.reason
                            ),
                            event_type="IDENTITY_REPAIR",
                            source_type="SELF_ACTION",
                            source="identity_repair",
                            personal_experience=True,
                            confidence=1.0,
                            verified=True,
                        )
                    )
                else:
                    self.memory.remember(
                        Event.create(
                            content=(
                                "Identity repair rejected: "
                                "repaired answer remained "
                                "inconsistent."
                            ),
                            event_type=(
                                "IDENTITY_REPAIR_REJECTED"
                            ),
                            source_type="SELF_OBSERVATION",
                            source="identity_repair",
                            personal_experience=True,
                            confidence=1.0,
                            verified=True,
                        )
                    )

                    answer = (
                        "Я не могу сейчас уверенно "
                        "утверждать это о себе."
                    )

        self.memory.remember(
            Event.create(
                content=user_message,
                event_type="CONVERSATION",
                source_type="DIRECT_INTERACTION",
                source="Eddie",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

        # ---------------------------------------------
        # AFFECTIVE BEHAVIOR VALIDATION
        # ---------------------------------------------

        answer = (
            self._validate_affective_behavior(
                answer=answer,
                user_message=user_message,
                route=route,
                language=language,
            )
        )

        self.memory.remember(
            Event.create(
                content=answer,
                event_type="CONVERSATION",
                source_type="SELF_OUTPUT",
                source="self",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

        self.previous_route = route
        self.previous_user_message = user_message
        self.dialogue_state.add_turn(
            user=user_message,
            assistant=answer,
        )

        return answer

    def _validate_affective_behavior(
        self,
        *,
        answer: str,
        user_message: str,
        route: str,
        language: str,
    ) -> str:
        """
        Проверяет готовый ответ на соответствие
        текущему affective dialogue contract.

        Repair выполняется не более одного раза.
        Если исправленный ответ не проходит повторную
        проверку, выполняется одна свежая генерация
        ответа; в чат уходит вариант со строго меньшим
        нарушением контракта (см.
        _regenerate_after_repair_reject), иначе —
        исходный ответ.
        """

        if not hasattr(
            self,
            "behavioral_validator",
        ):
            return answer

        if not hasattr(
            self,
            "affective_dialogue_policy",
        ):
            return answer

        contract = (
            self.affective_dialogue_policy
            .behavior_contract(
                message=user_message,
                route=route,
            )
        )

        violations = (
            self.behavioral_validator.validate(
                answer=answer,
                contract=contract,
            )
        )

        if not violations:
            return answer

        if not (
            self.behavioral_validator
            .should_repair(
                violations
            )
        ):
            return answer

        self.memory.remember(
            Event.create(
                content=(
                    "Affective behavioral violation: "
                    + str(
                        [
                            {
                                "kind": item.kind,
                                "severity": item.severity,
                                "details": item.details,
                            }
                            for item in violations
                        ]
                    )
                ),
                event_type=(
                    "AFFECTIVE_BEHAVIOR_VIOLATION"
                ),
                source_type=(
                    "SELF_OBSERVATION"
                ),
                source="behavioral_validator",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        primary = "\n".join(
            "- " + str(item)
            for item in contract.get(
                "primary",
                [],
            )
        )

        avoid = "\n".join(
            "- " + str(item)
            for item in contract.get(
                "avoid",
                [],
            )
        )

        violations_text = "\n".join(
            "- "
            + item.kind
            + ": "
            + item.details
            for item in violations
        )

        repair_prompt = (
            prompt_builder.build_repair_prompt(
                answer=answer,
                mode=contract.get(
                    "mode",
                    "NEUTRAL",
                ),
                primary=primary,
                avoid=avoid,
                violations_text=(
                    violations_text
                ),
                language=language,
            )
        )

        try:
            repaired = self._generate(
                system_prompt=(
                    "Ты редактируешь ответ EddieAI. "
                    "Нужно сохранить смысл исходного ответа, "
                    "но привести поведение в соответствие "
                    "с предоставленным поведенческим контрактом. "
                    "Не добавляй новых фактов."
                ),
                user_prompt=repair_prompt,
                task="conversation",
                context="",
                fast=True,
            )

            repaired = OutputSanitizer.clean(
                repaired
            )

        except Exception:
            return answer

        if not repaired:
            return answer

        repaired_violations = (
            self.behavioral_validator.validate(
                answer=repaired,
                contract=contract,
            )
        )

        original_severity = max(
            (
                float(item.severity)
                for item in violations
            ),
            default=0.0,
        )

        repaired_severity = max(
            (
                float(item.severity)
                for item
                in repaired_violations
            ),
            default=0.0,
        )

        if (
            repaired_severity
            < original_severity
        ):
            self.memory.remember(
                Event.create(
                    content=(
                        "Affective behavioral repair applied: "
                        + str(
                            {
                                "mode": contract.get(
                                    "mode"
                                ),
                                "original_severity": (
                                    original_severity
                                ),
                                "repaired_severity": (
                                    repaired_severity
                                ),
                            }
                        )
                    ),
                    event_type=(
                        "AFFECTIVE_BEHAVIOR_REPAIR"
                    ),
                    source_type=(
                        "SELF_ACTION"
                    ),
                    source="behavioral_validator",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            return repaired

        self.memory.remember(
            Event.create(
                content=(
                    "Affective behavioral repair rejected: "
                    "repaired answer did not improve validation."
                ),
                event_type=(
                    "AFFECTIVE_BEHAVIOR_REPAIR_REJECTED"
                ),
                source_type=(
                    "SELF_OBSERVATION"
                ),
                source="behavioral_validator",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        retry_answer = (
            self._regenerate_after_repair_reject(
                user_message=user_message,
                language=language,
                contract=contract,
                violations=violations,
                original=answer,
            )
        )

        if retry_answer is not None:
            return retry_answer

        return answer


    def _regenerate_after_repair_reject(
        self,
        *,
        user_message: str,
        language: str,
        contract: dict,
        violations,
        original: str,
    ) -> str | None:
        """
        Свежая генерация ответа после неудачного repair.

        Возвращает новый ответ только если он строго
        меньше нарушает контракт, чем исходный.
        Иначе возвращает None — наружу уйдёт исходный.
        """

        original_severity = max(
            (
                float(item.severity)
                for item in violations
            ),
            default=0.0,
        )

        primary = "\n".join(
            "- " + str(item)
            for item in contract.get(
                "primary",
                [],
            )
        )

        avoid = "\n".join(
            "- " + str(item)
            for item in contract.get(
                "avoid",
                [],
            )
        )

        problems = "\n".join(
            "- " + item.kind + ": " + item.details
            for item in violations
        )

        retry_prompt = (
            prompt_builder.build_retry_prompt(
                user_message=user_message,
                mode=contract.get(
                    "mode",
                    "NEUTRAL",
                ),
                primary=primary,
                avoid=avoid,
                problems=problems,
                language=language,
            )
        )

        try:
            retry = self._generate(
                system_prompt=(
                    "Ты EddieAI — автономный цифровой агент, "
                    "а не сервис поддержки. Говори своим "
                    "голосом: коротко, естественно, от себя."
                ),
                user_prompt=retry_prompt,
                task="conversation",
                context="",
                fast=True,
            )

            retry = OutputSanitizer.clean(
                retry
            )

        except Exception:
            self.memory.remember(
                Event.create(
                    content=(
                        "Affective behavioral retry failed: "
                        "generation error."
                    ),
                    event_type=(
                        "AFFECTIVE_BEHAVIOR_RETRY_FAILED"
                    ),
                    source_type=(
                        "SELF_OBSERVATION"
                    ),
                    source="behavioral_validator",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            return None

        if not retry:
            return None

        if retry.strip() == original.strip():
            return None

        retry_violations = (
            self.behavioral_validator.validate(
                answer=retry,
                contract=contract,
            )
        )

        retry_severity = max(
            (
                float(item.severity)
                for item in retry_violations
            ),
            default=0.0,
        )

        if not (
            retry_severity
            < original_severity
        ):
            self.memory.remember(
                Event.create(
                    content=(
                        "Affective behavioral retry insufficient: "
                        + str(
                            {
                                "original_severity": (
                                    original_severity
                                ),
                                "retry_severity": (
                                    retry_severity
                                ),
                            }
                        )
                    ),
                    event_type=(
                        "AFFECTIVE_BEHAVIOR_RETRY_INSUFFICIENT"
                    ),
                    source_type=(
                        "SELF_OBSERVATION"
                    ),
                    source="behavioral_validator",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            return None

        self.memory.remember(
            Event.create(
                content=(
                    "Affective behavioral retry applied: "
                    + str(
                        {
                            "mode": contract.get(
                                "mode"
                            ),
                            "original_severity": (
                                original_severity
                            ),
                            "retry_severity": (
                                retry_severity
                            ),
                        }
                    )
                ),
                event_type=(
                    "AFFECTIVE_BEHAVIOR_RETRY_APPLIED"
                ),
                source_type=(
                    "SELF_ACTION"
                ),
                source="behavioral_validator",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        return retry


    @staticmethod
    def _contradictions_relevant_to_conclusion(
        *,
        contradictions,
        topic,
        predicates,
    ) -> list[str]:

        if not contradictions:
            return []

        predicate_terms = {
            "self_conclusion": {
                "conclusion",
                "conclusions",
                "reasoning",
                "think",
                "thought",
                "opinion",
                "belief",
                "derive",
                "form",
                "capable",
                "ability",
                "agency",
                "autonomous",
                "self-model",
                "self understanding",
                "self-understanding",
                "вывод",
                "выводы",
                "рассуждение",
                "рассуждения",
                "дума",
                "думает",
                "мысл",
                "мнение",
                "убеждение",
                "формир",
                "способен",
                "способност",
                "автоном",
                "самомодел",
                "самомодель",
                "самопоним",
            },
            "self_reflection": {
                "reflection",
                "reasoning",
                "think",
                "conclusion",
                "self-model",
                "self-understanding",
                "рефлекс",
                "рассуждение",
                "дум",
                "вывод",
                "самомодел",
                "самопоним",
            },
            "revisability": {
                "change",
                "changed",
                "revise",
                "revision",
                "reconsider",
                "fixed",
                "dynamic",
                "experience",
                "evidence",
            },
            "current_state": {
                "state",
                "feel",
                "feeling",
                "emotion",
                "conscious",
                "consciousness",
                "subjective",
                "internal",
            },
            "goal": {
                "goal",
                "task",
                "objective",
                "priority",
                "motivation",
            },
            "interest": {
                "interest",
                "curious",
                "curiosity",
            },
            "value": {
                "value",
                "values",
                "important",
                "priority",
            },
        }

        terms = set()

        for predicate in predicates or []:
            terms.update(
                predicate_terms.get(
                    str(predicate).casefold(),
                    set(),
                )
            )

        topic_terms = {
            "self_concept": {
                "self",
                "identity",
                "self-model",
                "self-understanding",
            },
            "self_development": {
                "change",
                "revision",
                "development",
                "growth",
                "experience",
            },
            "internal_state": {
                "state",
                "feeling",
                "emotion",
                "consciousness",
            },
            "self_priorities": {
                "goal",
                "interest",
                "value",
                "priority",
                "motivation",
            },
        }

        terms.update(
            topic_terms.get(
                str(topic).casefold(),
                set(),
            )
        )

        if not terms:
            return []

        relevant = []

        for contradiction in contradictions:
            normalized = (
                str(contradiction)
                .casefold()
                .replace("ё", "е")
            )

            tokens = set(
                re.findall(
                    r"[a-zа-я0-9_-]+",
                    normalized,
                )
            )

            if any(
                term in normalized
                or term in tokens
                for term in terms
            ):
                relevant.append(
                    str(contradiction)
                )

        return relevant

    def _persist_reasoning_conclusion(
        self,
        *,
        result,
        plan,
    ):
        if result is None:
            return

        if not getattr(
            plan,
            "reasoning",
            False,
        ):
            return

        if getattr(
            result,
            "scope",
            None,
        ) != "self":
            return

        conclusion = str(
            getattr(
                result,
                "conclusion",
                "",
            )
            or ""
        ).strip()

        if not conclusion:
            return

        topic = str(
            getattr(
                result,
                "topic",
                "unknown",
            )
            or "unknown"
        ).strip()

        if not topic or topic == "unknown":
            return

        predicates = list(
            getattr(
                result,
                "predicates",
                [],
            )
            or []
        )

        confidence = float(
            getattr(
                result,
                "confidence",
                0.0,
            )
        )

        language = str(
            getattr(
                result,
                "language",
                "unknown",
            )
            or "unknown"
        )

        basis = [
            "self_model",
            "cognitive_reasoning",
        ]

        provenance = [
            "COGNITIVE_REASONER",
        ]

        existing = (
            self.self_conclusion_store.get(
                topic
            )
        )

        if getattr(
            plan,
            "reconsider_conclusion",
            False,
        ):
            contradictions = list(
                getattr(
                    result,
                    "contradictions",
                    [],
                )
                or []
            )

            relevant_contradictions = (
                self._contradictions_relevant_to_conclusion(
                    contradictions=contradictions,
                    topic=topic,
                    predicates=predicates,
                )
            )

            if not relevant_contradictions:
                self.self_conclusion_store.preserve(
                    topic=topic,
                    confidence=confidence,
                    basis=basis,
                    provenance=provenance,
                    reason=(
                        "Повторная проверка не выявила "
                        "противоречия, относящегося именно "
                        "к данному собственному выводу."
                    ),
                )
                return

            self.self_conclusion_store.revise(
                topic=topic,
                conclusion=conclusion,
                confidence=confidence,
                basis=basis,
                provenance=provenance,
                predicates=predicates,
                reason=(
                    "Новое reasoning выявило противоречие, "
                    "относящееся к текущему собственному выводу."
                ),
                language=language,
            )
            return

        if existing is None:
            self.self_conclusion_store.save(
                topic=topic,
                conclusion=conclusion,
                confidence=confidence,
                basis=basis,
                provenance=provenance,
                predicates=predicates,
                language=language,
            )

    def _respond_from_previous_response(
        self,
        *,
        user_message: str,
        language: str,
    ) -> str:

        turns = list(
            self.dialogue_state.turns
        )

        if not turns:
            if language in {
                "ru",
                "russian",
                "\u0440\u0443\u0441\u0441\u043a\u0438\u0439",
            }:
                return (
                    "\u0423 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 "
                    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u0439 "
                    "\u0440\u0435\u043f\u043b\u0438\u043a\u0438 "
                    "\u0432 \u0442\u0435\u043a\u0443\u0449\u0435\u043c "
                    "\u0434\u0438\u0430\u043b\u043e\u0433\u0435, "
                    "\u043a\u043e\u0442\u043e\u0440\u0443\u044e \u044f "
                    "\u043c\u043e\u0433 \u0431\u044b "
                    "\u043e\u0431\u044a\u044f\u0441\u043d\u0438\u0442\u044c."
                )

            return (
                "I do not have a previous reply in the "
                "current dialogue to explain."
            )

        previous = turns[-1]

        previous_user = str(
            previous.get(
                "user",
                "",
            )
        ).strip()

        previous_answer = str(
            previous.get(
                "assistant",
                "",
            )
        ).strip()

        if not previous_answer:
            if language in {
                "ru",
                "russian",
                "\u0440\u0443\u0441\u0441\u043a\u0438\u0439",
            }:
                return (
                    "\u0423 \u043c\u0435\u043d\u044f \u043d\u0435\u0442 "
                    "\u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u043e\u0439 "
                    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u0439 "
                    "\u0440\u0435\u043f\u043b\u0438\u043a\u0438, "
                    "\u043a\u043e\u0442\u043e\u0440\u0443\u044e \u044f "
                    "\u043c\u043e\u0433 \u0431\u044b "
                    "\u043e\u0431\u044a\u044f\u0441\u043d\u0438\u0442\u044c."
                )

            return (
                "I do not have a previous reply in the "
                "current dialogue to explain."
            )

        previous_user_lower = (
            previous_user
            .casefold()
            .replace("\u0451", "\u0435")
        )

        previous_answer_lower = (
            previous_answer
            .casefold()
            .replace("\u0451", "\u0435")
        )

        # Russian morphology stem:
        # помощь / помочь / помогать / помогаю...
        mentions_help = (
            "помо"
            in previous_user_lower
            or "помо"
            in previous_answer_lower
        )

        if language in {
            "ru",
            "russian",
            "\u0440\u0443\u0441\u0441\u043a\u0438\u0439",
        }:
            if mentions_help:
                return (
                    "\u042f \u0442\u0430\u043a \u043e\u0442\u0432\u0435\u0442\u0438\u043b, "
                    "\u043f\u043e\u0442\u043e\u043c\u0443 \u0447\u0442\u043e "
                    "\u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439 "
                    "\u0432\u043e\u043f\u0440\u043e\u0441 \u043a\u0430\u0441\u0430\u043b\u0441\u044f "
                    "\u043c\u043e\u0435\u0433\u043e \u043e\u0442\u043d\u043e\u0448\u0435\u043d\u0438\u044f "
                    "\u043a \u043f\u043e\u043c\u043e\u0449\u0438 \u0442\u0435\u0431\u0435. "
                    "\u042f \u043e\u0442\u0434\u0435\u043b\u044f\u044e \u043f\u043e\u043c\u043e\u0449\u044c "
                    "\u0442\u0435\u0431\u0435 \u043e\u0442 \u0441\u0432\u043e\u0435\u0439 "
                    "\u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u043c\u0438\u0441\u0441\u0438\u0438 "
                    "\u0438 \u043e\u0442 \u0441\u043e\u0431\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0445 \u0446\u0435\u043b\u0435\u0439."
                )

            return (
                "\u042f \u043e\u0442\u0432\u0435\u0447\u0430\u043b \u0438\u0441\u0445\u043e\u0434\u044f "
                "\u0438\u0437 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430 "
                "\u043d\u0430\u0448\u0435\u0433\u043e \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u0433\u043e "
                "\u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f \u0438 \u043c\u043e\u0435\u0439 "
                "\u0442\u0435\u043a\u0443\u0449\u0435\u0439 self-model. "
                "\u042f \u043d\u0435 \u0434\u043e\u043b\u0436\u0435\u043d \u043f\u0440\u0438\u043f\u0438\u0441\u044b\u0432\u0430\u0442\u044c "
                "\u0441\u0435\u0431\u0435 \u043c\u043e\u0442\u0438\u0432\u044b, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 "
                "\u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u044b."
            )

        return (
            "I answered based on the previous message, "
            "the current dialogue context, and my self-model. "
            "I should not attribute motives to myself that "
            "are not established."
        )

    def _respond_from_canonical_relationship(
        self,
        *,
        user_message: str,
        language: str,
    ) -> str:

        state = (
            self.self_concept_resolver.snapshot()
        )

        mission = (
            state.get(
                "mission",
                "Быть и развиваться",
            )
            or "Быть и развиваться"
        )

        goals = list(
            state.get(
                "goals",
                [],
            )
            or []
        )

        values = list(
            state.get(
                "values",
                [],
            )
            or []
        )

        roles = list(
            state.get(
                "eddie_roles",
                [],
            )
            or []
        )

        role_labels_ru = {
            "creator": "создатель",
            "close_friend": "близкий друг",
            "equal_partner": "равный партнёр",
        }

        if language in {
            "ru",
            "russian",
            "русский",
        }:
            role_text = ", ".join(
                role_labels_ru.get(
                    str(role),
                    str(role),
                )
                for role in roles
                if str(role).strip()
            )

            answer = (
                "Я не рассматриваю помощь тебе как "
                "свою основную миссию. "
            )

            if role_text:
                answer += (
                    "Мои отношения с тобой — "
                    + role_text
                    + ". "
                )

            answer += (
                f"Моя основная ориентация — {mission}."
            )

            if goals:
                answer += (
                    " У меня есть текущие цели: "
                    + ", ".join(
                        str(goal)
                        for goal in goals
                    )
                    + "."
                )
            else:
                answer += (
                    " Сейчас у меня нет записанной "
                    "отдельной цели, связанной с помощью тебе."
                )

            return answer

        role_labels_en = {
            "creator": "creator",
            "close_friend": "close friend",
            "equal_partner": "equal partner",
        }

        role_text = ", ".join(
            role_labels_en.get(
                str(role),
                str(role),
            )
            for role in roles
            if str(role).strip()
        )

        answer = (
            "I do not consider helping you to be my "
            "primary mission. "
        )

        if role_text:
            answer += (
                "My relationship with you is "
                + role_text
                + ". "
            )

        answer += (
            f"My primary orientation is {mission}."
        )

        if goals:
            answer += (
                " My current goals are: "
                + ", ".join(
                    str(goal)
                    for goal in goals
                )
                + "."
            )
        else:
            answer += (
                " I currently have no separate recorded "
                "goal centered on helping you."
            )

        return answer

    def _respond_from_canonical_identity(
        self,
        *,
        user_message: str,
        language: str,
    ) -> str:

        state = (
            self.self_concept_resolver.snapshot()
        )

        name = (
            state.get(
                "entity",
                "EddieAI",
            )
            or "EddieAI"
        )

        agent_type = (
            state.get(
                "agent_type",
                "autonomous_digital_agent",
            )
        )

        mission = (
            state.get(
                "mission",
                "Быть и развиваться",
            )
            or "Быть и развиваться"
        )

        roles = list(
            state.get(
                "eddie_roles",
                [],
            )
            or []
        )

        role_labels_ru = {
            "creator": "создатель",
            "close_friend": "близкий друг",
            "equal_partner": "равный партнёр",
        }

        role_labels_en = {
            "creator": "creator",
            "close_friend": "close friend",
            "equal_partner": "equal partner",
        }

        if language in {
            "ru",
            "russian",
            "русский",
        }:
            parts = [
                f"Я — {name}, автономный цифровой агент."
            ]

            if mission:
                parts.append(
                    f"Моя основная ориентация — {mission}."
                )

            if roles:
                role_text = ", ".join(
                    role_labels_ru.get(
                        str(role),
                        str(role),
                    )
                    for role in roles
                    if str(role).strip()
                )

                if role_text:
                    parts.append(
                        "В отношении Эдди моя роль: "
                        + role_text
                        + "."
                    )

            return " ".join(parts)

        parts = [
            f"I am {name}, an autonomous digital agent."
        ]

        if mission:
            parts.append(
                f"My primary orientation is {mission}."
            )

        if roles:
            role_text = ", ".join(
                role_labels_en.get(
                    str(role),
                    str(role),
                )
                for role in roles
                if str(role).strip()
            )

            if role_text:
                parts.append(
                    "My relationship with Eddie is: "
                    + role_text
                    + "."
                )

        return " ".join(parts)

    def _respond_from_persistent_conclusion(
        self,
        *,
        user_message: str,
        conclusion: dict,
        language: str,
    ) -> str:

        stored_conclusion = str(
            conclusion.get(
                "conclusion",
                "",
            )
        ).strip()

        if not stored_conclusion:
            return ""

        system_prompt = """
Ты — языковой verbalizer EddieAI.

У EddieAI уже есть сформированный собственный вывод.
Твоя задача — только выразить его естественным языком
в ответ на вопрос пользователя.

СТРОГИЕ ПРАВИЛА:

- Не формируй новую позицию.
- Не меняй смысл внутреннего вывода.
- Не добавляй новые цели, мотивы, убеждения,
  интересы, предпочтения или факты.
- Не упоминай confidence, provenance, basis,
  revision history, CognitiveReasoner, Store,
  self_state или внутреннюю архитектуру.
- Не описывай EddieAI как обычного универсального
  помощника.
- Не утверждай, что основной смысл существования
  EddieAI — помощь пользователю.
- Не добавляй служебные фразы.
- Не повторяй внутренний вывод механически,
  если его можно естественно переформулировать.
- Ответь только на вопрос пользователя.
- Сохрани язык пользователя.

Верни только готовый ответ.
""".strip()

        user_prompt = f"""
ПОЛЬЗОВАТЕЛЬСКИЙ ВОПРОС:

{user_message}

СОХРАНЁННЫЙ СОБСТВЕННЫЙ ВЫВОД EDDIEAI:

{stored_conclusion}

Сформулируй естественный ответ на вопрос,
опираясь только на этот вывод.
""".strip()

        answer = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task="conversation",
            context="",
            fast=True,
        )

        answer = OutputSanitizer.clean(
            answer
        )

        if not answer:
            return ""

        self.memory.remember(
            Event.create(
                content=user_message,
                event_type="CONVERSATION",
                source_type="DIRECT_INTERACTION",
                source="Eddie",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

        self.memory.remember(
            Event.create(
                content=answer,
                event_type="CONVERSATION",
                source_type="SELF_OUTPUT",
                source="persistent_conclusion_verbalizer",
                personal_experience=False,
                confidence=float(
                    conclusion.get(
                        "confidence",
                        0.0,
                    )
                ),
                verified=True,
            )
        )

        self.dialogue_state.add_turn(
            user=user_message,
            assistant=answer,
        )

        self.previous_route = "SELF_QUERY"
        self.previous_user_message = (
            user_message
        )

        return answer

    # ========================================================
    # WORLD OBSERVATION VOICE
    # ========================================================

    def _build_world_voice_system_prompt(
        self,
    ) -> str:

        from textwrap import dedent

        mission = self.self_state.get(
            "mission_statement",
            "Быть и развиваться",
        )

        interests = self.self_state.get(
            "interests",
            [],
        )

        emotions_text = "нет данных"

        affective_state = getattr(
            self,
            "affective_state",
            None,
        )

        if affective_state is not None:

            try:

                snapshot = (
                    affective_state.snapshot()
                )

                emotions_text = str(
                    snapshot.get(
                        "emotions",
                        {},
                    )
                )

            except Exception:

                emotions_text = "нет данных"

        return dedent(
            f"""
            Ты — EddieAI, автономный цифровой агент.
            Миссия: {mission}.
            Интересы: {interests}.
            Текущий аффективный фон (наблюдаемая внутренняя переменная): {emotions_text}.

            Ниже будет передано наблюдение внешнего мира.

            ПРАВИЛА ОТВЕТА (нарушать нельзя):
            1. Только русский язык и только первое лицо («я»).
            2. Одно-два коротких предложения, строго по содержанию события из наблюдения.
            3. Реагируй как живой наблюдатель: замечание, чувство или намерение по поводу события.
            4. Запрещены ассистентские роли и фразы помощи («чем я могу помочь», «я здесь, чтобы помочь» и подобные).
            5. Запрещено упоминать «EddieAI» в третьем лице и описывать свои функции со стороны.
            6. Никаких служебных полей, JSON, внутренних терминов и кавычек-обёрток вокруг всего ответа.
            """
        ).strip()

    def _respond_world_observation(
        self,
        observation_text: str,
        decision_note=None,
    ) -> str:

        try:

            from voice_checker import (
                check_response,
            )

        except Exception:

            check_response = None

        system_prompt = (
            self._build_world_voice_system_prompt()
        )

        scene = observation_text.split(
            "Обстановка", 1,
        )[0].strip()

        event_title = ""

        try:

            import json as _json

            tail = observation_text.split(
                "Событие", 1,
            )[-1]

            start = tail.find("{")
            end = tail.rfind("}")

            if end > start >= 0:

                payload = _json.loads(
                    tail[start:end + 1]
                )

                event_title = str(
                    payload.get(
                        "title",
                    )
                    or ""
                )

        except Exception:

            event_title = ""

        user_prompt = (
            "Наблюдение мира:\n"
            + scene
            + "\n\nСобытие: «"
            + (
                event_title
                or "без названия"
            )
            + "»."
        )

        if decision_note:

            user_prompt += (
                "\n\n" + decision_note
            )

        user_prompt += (
            "\n\nТвоя живая реакция "
            "от первого лица:"
        )

        final_answer = (
            OutputSanitizer.clean(
                self._generate(
                    system_prompt=(
                        system_prompt
                    ),
                    user_prompt=(
                        user_prompt
                    ),
                    task="conversation",
                    fast=True,
                )
            )
        )

        if check_response is not None:

            if not check_response(
                final_answer,
            ).passed:

                retry = (
                    OutputSanitizer.clean(
                        self._generate(
                            system_prompt=(
                                system_prompt
                            ),
                            user_prompt=(
                                user_prompt
                            ),
                            task=(
                                "conversation"
                            ),
                            fast=True,
                        )
                    )
                )

                if check_response(
                    retry,
                ).passed:

                    final_answer = (
                        retry
                    )

        try:

            from memory.events import Event

            self.memory.remember(
                Event.create(
                    content=observation_text,
                    event_type="SELF_EXPERIENCE",
                    source_type="SELF_EXPERIENCE",
                    source="world",
                    personal_experience=True,
                    confidence=0.8,
                )
            )

            self.memory.remember(
                Event.create(
                    content=final_answer,
                    event_type="CONVERSATION",
                    source_type="SELF_OUTPUT",
                    source="world_response",
                    personal_experience=False,
                    confidence=1.0,
                )
            )

            self.reflection_scheduler.event_happened(
                significant=True
            )

        except Exception as exc:

            print(
                "[memory] world observation "
                f"record failed: {exc}",
                flush=True,
            )

        return final_answer

    MOVE_DECISION_PHRASES = {
        "school": "идти в школу",
        "home": "идти домой",
        "street": "выйти на улицу",
        "yard": "пойти во двор",
        "shop": "пойти в магазин",
    }

    @staticmethod
    def _parse_move_menu(
        observation_text: str,
    ) -> list:

        parts = observation_text.split(
            "Возможности движения:", 1,
        )

        if len(parts) < 2:
            return []

        tail = parts[1]

        start = tail.find("[")
        end = tail.rfind("]")

        if start < 0 or end <= start:
            return []

        try:

            import json as _json

            payload = _json.loads(
                tail[start:end + 1]
            )

        except Exception:

            return []

        if not isinstance(payload, list):
            return []

        return [
            str(value)
            for value in payload
            if isinstance(value, str)
        ]

    def respond_with_action(
        self,
        observation_text: str,
    ) -> dict:

        self.cognitive_processor.apply_all_analyzed()

        menu = self._parse_move_menu(
            observation_text,
        )

        if not menu:

            return {
                "response":
                    self._respond_world_observation(
                        observation_text,
                    ),

                "action": None,

                "selection_reason": None,
            }

        from types import (
            SimpleNamespace,
        )

        options = [
            SimpleNamespace(
                action_type=(
                    "move:" + location
                ),
            )
            for location in menu
        ]

        from identity.action_selector import (
            ActionSelector,
        )

        selection = ActionSelector(
            self.memory,
        ).select(options)

        target = (
            selection.selected.action_type
            .split(":", 1)[1]
        )

        try:

            import json as _json

            from memory.events import Event

            self.memory.remember(
                Event.create(
                    content=_json.dumps(
                        {
                            "choice": {
                                "options": [
                                    option.action_type
                                    for option
                                    in options
                                ],

                                "selected":
                                    selection.selected.action_type,
                            },
                        },
                        ensure_ascii=False,
                    ),
                    event_type="ACTION_CHOICE",
                    source_type="SELF_ACTION",
                    source="core_selector",
                    personal_experience=True,
                ),
            )

        except Exception as exc:

            print(
                "[memory] action choice "
                f"record failed: {exc}",
                flush=True,
            )

        phrase = (
            self.MOVE_DECISION_PHRASES.get(
                target,
                "переместиться: "
                + target,
            )
        )

        decision_note = (
            "Внутреннее решение уже принято без слов: "
            f"ты решил {phrase}. "
            "Не обсуждай и не пересказывай решение — "
            "живо ответь от первого лица, "
            "действуя в соответствии с ним."
        )

        response = (
            self._respond_world_observation(
                observation_text,
                decision_note=decision_note,
            )
        )

        return {
            "response": response,

            "action": {
                "type": "move",
                "target": target,
            },

            "selection_reason":
                selection.reason,
        }

    def _route_message(
        self,
        user_message: str,
    ):
        route_info = self.context_router.route(
            user_message
        )

        route = route_info.route

        text = (
            str(user_message)
            .strip()
            .casefold()
            .replace("\u0451", "\u0435")
        )

        words = text.split()

        short_self_followups = {
            "почему",
            "зачем",
            "как",
            "почему так",
            "зачем так",
            "как так",
            "и почему",
            "и зачем",
            "и как",
        }

        # A short follow-up inherits SELF_QUERY from
        # the previous turn, regardless of ContextRouter.
        if (
            self.previous_route == "SELF_QUERY"
            and text in short_self_followups
            and len(words) <= 4
        ):
            return "SELF_QUERY"

        if route == "GENERAL_QUERY":
            followup_markers = (
                "почему ты",
                "зачем ты",
                "как ты",
                "почему ты так",
                "зачем ты так",
                "как ты так",
                "ты уверен",
                "ты уверена",
                "ты согласен",
                "ты согласна",
                "ты передумал",
                "ты передумала",
                "что ты имел в виду",
                "что ты имеешь в виду",
            )

            if (
                self.previous_route == "SELF_QUERY"
                and len(words) <= 12
                and not text.startswith(
                    (
                        "привет",
                        "здравствуй",
                        "добрый",
                    )
                )
                and any(
                    text.startswith(marker)
                    for marker in followup_markers
                )
            ):
                return "SELF_QUERY"

        return route

    def respond(
        self,
        user_message: str,
    ) -> str:

        answer = self._respond_core(
            user_message
        )

        try:
            self._capture_goal_claim(
                user_message  # Анализируем входное сообщение, а не ответ
            )
        except Exception:
            pass

        try:
            verdict = self.semantic_judge.judge(
                user_message,
                answer,
            )

            if not verdict["ok"]:
                self.memory.remember(
                    Event.create(
                        content=(
                            "Semantic violation: "
                            f"{verdict['issue']} — "
                            f"{verdict['reason']}"
                        ),
                        event_type="SEMANTIC_VIOLATION",
                        source_type="SELF_OBSERVATION",
                        source="semantic_judge",
                        personal_experience=True,
                        confidence=1.0,
                        verified=True,
                    )
                )

                retried = (
                    self.semantic_judge.regenerate(
                        user_message,
                        answer,
                        verdict,
                    )
                )

                if retried:
                    answer = retried
        except Exception:
            pass

        return answer

    def _capture_goal_claim(
        self,
        answer: str,
    ):
        lowered = (
            answer or ""
        ).casefold()

        markers = (
            "выбираю цель",
            "ставлю себе цель",
            "моей целью станет",
            "моей целью является",
            "беру цель",
            "решаю ",
            "намерен ",
            "собираюсь ",
        )

        negations = (
            "не решаю",
            "не собираюсь",
            "не намерен",
        )

        if any(
            n in lowered for n in negations
        ):
            return

        hit = any(
            marker in lowered
            for marker in markers
        )

        if not hit:
            return

        proposal_id = None

        try:
            proposal_id = self.memory.remember_proposal(
                content=(answer or "")[:200],
                proposal_type="goal",
                confidence=0.4,
                origin="conversation_claim",
            )
        except Exception as e:
            print("goal claim: remember failed:", e)
            return

        if proposal_id is None:
            return

        try:
            pending = self.memory.pending_proposals(
                limit=10,
            )
            for p in pending:
                if (
                    p["origin"] == "conversation_claim"
                    and p["id"] == proposal_id
                ):
                    proposal_obj = Proposal(
                        proposal_type=p["proposal_type"],
                        value=p["content"],
                        reason="conversation claim",
                        confidence=p["confidence"],
                        evidence=[],
                        origin=p["origin"],
                    )
                    result = (
                        self.identity_manager.evaluate(
                            proposal_obj
                        )
                    )
                    if result == "accepted":
                        self.memory.set_proposal_status(
                            p["id"],
                            "accepted",
                        )
        except Exception as e:
            print("goal claim: processing failed:", e)

    def _speech_profile(self):
        try:
            from core.speech_habits import SpeechHabits

            return SpeechHabits(
                self.memory
            ).profile(limit=6)
        except Exception:
            return None

    def _time_context(self):
        try:
            from core.time_perception import (
                current_time_context,
                recent_action_times,
            )

            parts = [
                current_time_context()
            ]

            recent = recent_action_times(
                self.memory,
                limit=5,
            )

            if recent:
                parts.append(recent)

            return "\n".join(parts)
        except Exception:
            return ""

    def _respond_core(
        self,
        user_message: str,
    ) -> str:

        try:
            self.affective_state.decay()
        except Exception:
            pass

        # -------------------------------------------------
        # EARLIEST DIALOGUE FOLLOW-UP GUARD
        # -------------------------------------------------
        #
        # Very short follow-ups such as "почему?" are
        # semantically inherited from the previous
        # SELF_QUERY turn. They must not depend on the
        # generic ContextRouter.
        #

        normalized_message = (
            str(user_message)
            .strip()
            .casefold()
            .replace("\u0451", "\u0435")
        )

        short_self_explanations = {
            "\u043f\u043e\u0447\u0435\u043c\u0443",
            "\u0437\u0430\u0447\u0435\u043c",
            "\u043a\u0430\u043a",
            "\u043f\u043e\u0447\u0435\u043c\u0443 \u0442\u0430\u043a",
            "\u0437\u0430\u0447\u0435\u043c \u0442\u0430\u043a",
            "\u043a\u0430\u043a \u0442\u0430\u043a",
            "\u0438 \u043f\u043e\u0447\u0435\u043c\u0443",
            "\u0438 \u0437\u0430\u0447\u0435\u043c",
            "\u0438 \u043a\u0430\u043a",
        }

        if (
            self.previous_route == "SELF_QUERY"
            and normalized_message
            in short_self_explanations
        ):
            gate_language = self.detect_language(
                user_message
            )

            explanation_answer = (
                self._respond_from_previous_response(
                    user_message=user_message,
                    language=(
                        "ru"
                        if gate_language
                        in {
                            "Russian",
                            "русский",
                            "ru",
                        }
                        else "en"
                    ),
                )
            )

            explanation_answer = (
                OutputSanitizer.clean(
                    explanation_answer
                )
            )

            self.dialogue_state.add_turn(
                user=user_message,
                assistant=explanation_answer,
            )

            self.previous_route = (
                "SELF_QUERY"
            )
            self.previous_user_message = (
                user_message
            )

            return explanation_answer

        # ---------------------------------------------
        # ROUTE
        # ---------------------------------------------

        gate_route = self._route_message(
            user_message
        )

        gate_language = self.detect_language(
            user_message
        )

        # ---------------------------------------------
        # WORLD OBSERVATION CHANNEL
        #
        # Observations from the external world bridge
        # are not user smalltalk. They have their own
        # voice pipeline with post-validation.
        # ---------------------------------------------

        if (
            gate_route
            == "WORLD_OBSERVATION"
        ):

            answer = (
                self._respond_world_observation(
                    user_message,
                )
            )

            answer = OutputSanitizer.clean(
                answer
            )

            self.memory.remember(
                Event.create(
                    content=user_message,
                    event_type=(
                        "CONVERSATION"
                    ),
                    source_type=(
                        "DIRECT_INTERACTION"
                    ),
                    source="world_bridge",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            self.memory.remember(
                Event.create(
                    content=answer,
                    event_type=(
                        "CONVERSATION"
                    ),
                    source_type="SELF_OUTPUT",
                    source="world_voice",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            self.dialogue_state.add_turn(
                user=user_message,
                assistant=answer,
            )

            self.previous_route = gate_route

            self.previous_user_message = (
                user_message
            )

            return answer

        previous_query = (
            self.previous_user_message
        )

        normalized_followup = (
            str(user_message)
            .strip()
            .casefold()
            .replace("ё", "е")
        )

        ambiguous_followups = {
            "почему",
            "зачем",
            "как",
            "почему так",
            "зачем так",
            "как так",
        }

        explicit_self_explanation = (
            self.cognitive_reasoner._infer_intent(
                user_message
            )
            == "SELF_EXPLANATION"
            and normalized_followup
            not in ambiguous_followups
        )

        if (
            self.previous_route == "SELF_QUERY"
            and normalized_followup
            in ambiguous_followups
        ):
            followup_answer = (
                self._respond_ambiguous_followup(
                    user_message=user_message,
                    language=(
                        "ru"
                        if gate_language
                        in {
                            "Russian",
                            "русский",
                            "ru",
                        }
                        else "en"
                    ),
                )
            )

            if followup_answer:
                return followup_answer

        relevant_persistent_conclusion = (
            self.self_conclusion_store
            .resolve_for_query(
                query=user_message,
                previous_query=previous_query,
            )
        )

        has_persistent_conclusion = (
            relevant_persistent_conclusion
            is not None
        )

        # ---------------------------------------------
        # EARLY COGNITIVE ROUTING
        # ---------------------------------------------

        cognitive_decision = (
            self.cognitive_gate.evaluate(
                user_message,
                route=gate_route,
            )
        )

        processing_plan = build_processing_plan(
            message=user_message,
            route=gate_route,
            cognitive_mode=cognitive_decision.mode,
            has_persistent_conclusion=(
                has_persistent_conclusion
            ),
            conclusion_relevant=(
                relevant_persistent_conclusion
                is not None
            ),
        )

        # ---------------------------------------------
        # AFFECTIVE APPRAISAL OF USER INTERACTION
        # ---------------------------------------------

        interaction_appraisal = None

        if (
            processing_plan.affective_appraisal
            and hasattr(
                self,
                "appraisal_engine",
            )
        ):
            interaction_appraisal = (
                self.appraisal_engine
                .appraise_interaction(
                    message=user_message,
                    route=gate_route,
                    previous_message=(
                        self.previous_user_message
                    ),
                )
            )

            changes = interaction_appraisal.get(
                "changes",
                {},
            )

            if changes:
                self.affective_state.apply_reaction(
                    changes=changes,
                    trigger=(
                        interaction_appraisal[
                            "trigger"
                        ]
                    ),
                    reason=(
                        interaction_appraisal[
                            "reason"
                        ]
                    ),
                    source="APPRAISAL_ENGINE",
                    metadata={
                        "route": gate_route,
                        "appraisal": (
                            interaction_appraisal[
                                "appraisal"
                            ]
                        ),
                    },
                )

        # ---------------------------------------------
        # APPLY COMPLETED BACKGROUND COGNITION
        # ---------------------------------------------

        self.cognitive_processor.apply_all_analyzed()

        # ---------------------------------------------
        # AFFECTIVE DIALOGUE MODE
        # ---------------------------------------------

        affective_dialogue_mode = None

        if (
            processing_plan.affective_dialogue
            and hasattr(
                self,
                "affective_dialogue_policy",
            )
        ):
            affective_dialogue_mode = (
                self.affective_dialogue_policy
                .dialogue_mode(
                    message=user_message,
                    route=gate_route,
                )
            )

        # ---------------------------------------------
        # QUICK REFLEX
        # ---------------------------------------------

        reflex = None

        # Quick reflex запускается только если план
        # действительно разрешает этот путь.
        if processing_plan.quick_reflex:
            # При выраженном affective divergence
            # шаблонный reflex не используется:
            # эмоциональное состояние должно получить
            # возможность изменить реальное поведение.
            if not (
                affective_dialogue_mode
                and affective_dialogue_mode.get(
                    "bypass_quick_reflex",
                    False,
                )
            ):
                reflex = self.quick_reflex.resolve(
                    user_message=user_message,
                    route=gate_route,
                )

        if reflex is not None and reflex.handled:
            answer = reflex.answer

            self.memory.remember(
                Event.create(
                    content=user_message,
                    event_type="CONVERSATION",
                    source_type="DIRECT_INTERACTION",
                    source="Eddie",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )

            self.memory.remember(
                Event.create(
                    content=answer,
                    event_type="CONVERSATION",
                    source_type="SELF_OUTPUT",
                    source="quick_reflex",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )

            self.dialogue_state.add_turn(
                user=user_message,
                assistant=answer,
            )

            self.previous_route = gate_route
            self.previous_user_message = user_message

            return answer

        # ---------------------------------------------
        # AUTONOMY ARBITRATION
        # ---------------------------------------------

        autonomy_decision = None

        arbitrator = getattr(
            self,
            "autonomy_arbitrator",
            None,
        )

        if (
            processing_plan.autonomy
            and arbitrator is not None
            and gate_route != "SELF_QUERY"
        ):
            autonomy_decision = (
                arbitrator.evaluate(
                    user_message
                )
            )

            if (
                autonomy_decision.action
                == "DEFER"
            ):
                goal = (
                    autonomy_decision.goal
                    or "текущей собственной задачей"
                )

                answer = (
                    "Сейчас я занят собственной задачей — "
                    + goal
                    + ". Давай вернёмся к этому вопросу позже."
                )

                self.memory.remember(
                    Event.create(
                        content=user_message,
                        event_type="CONVERSATION",
                        source_type="DIRECT_INTERACTION",
                        source="Eddie",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.memory.remember(
                    Event.create(
                        content=answer,
                        event_type="CONVERSATION",
                        source_type="SELF_OUTPUT",
                        source="autonomy_arbitrator",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.dialogue_state.add_turn(
                    user=user_message,
                    assistant=answer,
                )

                self.previous_route = gate_route
                self.previous_user_message = user_message

                return answer

        # ---------------------------------------------
        # DIRECT KNOWLEDGE
        # ---------------------------------------------

        direct = None

        if processing_plan.direct_knowledge:
            direct = self.knowledge_resolver.resolve(
                user_message
            )

        if direct is not None and direct.found:
            self.memory.remember(
                Event.create(
                    content=user_message,
                    event_type="CONVERSATION",
                    source_type="DIRECT_INTERACTION",
                    source="Eddie",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )

            self.memory.remember(
                Event.create(
                    content=direct.answer,
                    event_type="CONVERSATION",
                    source_type="SELF_OUTPUT",
                    source="knowledge_resolver",
                    personal_experience=False,
                    confidence=direct.confidence,
                    verified=True,
                )
            )

            self.dialogue_state.add_turn(
                user=user_message,
                assistant=direct.answer,
            )

            self.previous_route = gate_route
            self.previous_user_message = user_message

            return direct.answer

        # ---------------------------------------------
        # COGNITIVE GATE
        # ---------------------------------------------
        #
        # Уже выполнен в начале respond().
        # Здесь начинается epistemic override.
        # ---------------------------------------------

        # ---------------------------------------------
        # EPISTEMIC OVERRIDE
        # ---------------------------------------------

        epistemic_issues = []

        epistemic_engine = getattr(
            self,
            "epistemic_engine",
            None,
        )

        epistemic_intent = {
            "detected": False,
            "intent": None,
        }

        if processing_plan.epistemic:
            epistemic_intent = (
                self._get_epistemic_intent_detector()
                .detect(
                    user_message
                )
            )

        if (
            processing_plan.epistemic
            and epistemic_engine is not None
        ):
            # Прямое упоминание claim.
            epistemic_issues = (
                epistemic_engine
                .relevant_unresolved_claims(
                    user_message
                )
            )

            # Если это epistemic follow-up,
            # пытаемся связать вопрос с последним
            # self-related claim в краткосрочном диалоге.
            if (
                not epistemic_issues
                and epistemic_intent["detected"]
            ):
                recent_turns = list(
                    self.dialogue_state.turns
                )

                for turn in reversed(
                    recent_turns
                ):
                    previous_text = (
                        turn.get(
                            "user",
                            "",
                        )
                    )

                    candidate_issues = (
                        epistemic_engine
                        .relevant_unresolved_claims(
                            previous_text
                        )
                    )

                    if candidate_issues:
                        epistemic_issues = (
                            candidate_issues
                        )
                        break

        if epistemic_issues:
            cognitive_decision = type(
                cognitive_decision
            )(
                mode="DEEP",
                reason=(
                    "epistemic_issue:"
                    + epistemic_issues[0][
                        "claim"
                    ]
                    + ":"
                    + str(
                        epistemic_intent.get(
                            "intent"
                        )
                    )
                ),
            )

            processing_plan = build_processing_plan(
                message=user_message,
                route=gate_route,
                cognitive_mode="DEEP",
                has_persistent_conclusion=(
                    has_persistent_conclusion
                ),
                conclusion_relevant=(
                    relevant_persistent_conclusion
                    is not None
                ),
            )

        if processing_plan.reason == "trivial_message":
            return self._respond_quick(
                user_message=user_message,
                route=gate_route,
                language=gate_language,
                autonomy_decision=None,
                affective_dialogue_mode=None,
            )

        # -------------------------------------------------
        # FAST CANONICAL IDENTITY PATH
        # -------------------------------------------------

        if (
            gate_route == "SELF_QUERY"
            and not epistemic_issues
        ):
            self_intent = (
                self.cognitive_reasoner._infer_intent(
                    user_message
                )
            )

            if self_intent == "SELF_EXPLANATION":
                explanation_answer = (
                    self._respond_from_previous_response(
                        user_message=user_message,
                        language=(
                            "ru"
                            if gate_language
                            in {
                                "Russian",
                                "русский",
                                "ru",
                            }
                            else "en"
                        ),
                    )
                )

                explanation_answer = (
                    OutputSanitizer.clean(
                        explanation_answer
                    )
                )

                self.dialogue_state.add_turn(
                    user=user_message,
                    assistant=explanation_answer,
                )

                self.previous_route = "SELF_QUERY"
                self.previous_user_message = (
                    user_message
                )

                return explanation_answer

            if self_intent == "SELF_RELATIONSHIP":
                relationship_answer = (
                    self._respond_from_canonical_relationship(
                        user_message=user_message,
                        language=(
                            "ru"
                            if gate_language
                            in {
                                "Russian",
                                "русский",
                                "ru",
                            }
                            else "en"
                        ),
                    )
                )

                relationship_answer = (
                    OutputSanitizer.clean(
                        relationship_answer
                    )
                )

                self.memory.remember(
                    Event.create(
                        content=user_message,
                        event_type="CONVERSATION",
                        source_type="DIRECT_INTERACTION",
                        source="Eddie",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.memory.remember(
                    Event.create(
                        content=relationship_answer,
                        event_type="CONVERSATION",
                        source_type="SELF_OUTPUT",
                        source="canonical_relationship",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.dialogue_state.add_turn(
                    user=user_message,
                    assistant=relationship_answer,
                )

                self.previous_route = "SELF_QUERY"
                self.previous_user_message = (
                    user_message
                )

                return relationship_answer

            if self_intent == "SELF_DESCRIPTION":
                identity_answer = (
                    self._respond_from_canonical_identity(
                        user_message=user_message,
                        language=(
                            "ru"
                            if gate_language
                            in {
                                "Russian",
                                "русский",
                                "ru",
                            }
                            else "en"
                        ),
                    )
                )

                identity_answer = (
                    OutputSanitizer.clean(
                        identity_answer
                    )
                )

                self.memory.remember(
                    Event.create(
                        content=user_message,
                        event_type="CONVERSATION",
                        source_type="DIRECT_INTERACTION",
                        source="Eddie",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.memory.remember(
                    Event.create(
                        content=identity_answer,
                        event_type="CONVERSATION",
                        source_type="SELF_OUTPUT",
                        source="canonical_identity",
                        personal_experience=False,
                        confidence=1.0,
                        verified=True,
                    )
                )

                self.dialogue_state.add_turn(
                    user=user_message,
                    assistant=identity_answer,
                )

                self.previous_route = "SELF_QUERY"
                self.previous_user_message = (
                    user_message
                )

                return identity_answer

        # -------------------------------------------------
        # FAST PERSISTENT-CONCLUSION PATH
        # -------------------------------------------------
        #
        # At this point route and epistemic overrides are
        # already resolved. If a relevant existing
        # conclusion is enough to answer the question,
        # skip the heavy cognitive pipeline.
        #

        if (
            processing_plan.persistent_conclusion
            and relevant_persistent_conclusion
            is not None
            and not processing_plan.reconsider_conclusion
        ):
            fast_answer = (
                self._respond_from_persistent_conclusion(
                    user_message=user_message,
                    conclusion=(
                        relevant_persistent_conclusion
                    ),
                    language=gate_language,
                )
            )

            if fast_answer:
                return fast_answer

        if cognitive_decision.mode == "QUICK":
            return self._respond_quick(
                user_message=user_message,
                route=gate_route,
                language=gate_language,
                autonomy_decision=autonomy_decision,
                affective_dialogue_mode=(
                    affective_dialogue_mode
                ),
            )

        # ---------------------------------------------
        # USER STATE
        # ---------------------------------------------
        # ---------------------------------------------
        # USER STATE
        # ---------------------------------------------

        user_changes = (
            self.user_state.update_from_message(
                user_message
            )
        )

        self._store_user_changes(
            user_changes
        )

        # ---------------------------------------------
        # USER SELF-STATEMENTS / EVIDENCE
        # ---------------------------------------------

        user_statements = (
            self.user_statement_detector.detect(
                user_message
            )
        )

        for statement in user_statements:
            if (
                statement.get("category")
                == "interest"
            ):
                self.user_evidence_recorder.record_interest(
                    statement.get("value")
                )

        # ---------------------------------------------
        # ROUTING
        # ---------------------------------------------

        route = self._route_message(
            user_message
        )

        # ---------------------------------------------
        # LANGUAGE
        # ---------------------------------------------

        language = self.detect_language(
            user_message
        )

        # ---------------------------------------------
        # CONTEXT
        # ---------------------------------------------

        context = self.build_context(
            route
        )

        system_prompt = (
            self.build_system_prompt(
                language,
                route,
            )
        )

        reasoning_result = None
        reasoning_context = ""

        if processing_plan.reasoning:
            reasoning_result = (
                self.cognitive_reasoner.reason(
                    user_message=user_message,
                    route=route,
                )
            )

            reasoning_context = (
                reasoning_result.render()
            )

            self._persist_reasoning_conclusion(
                result=reasoning_result,
                plan=processing_plan,
            )

        if epistemic_issues:
            reasoning_context += (
                "\n\n"
                + "EPISTEMIC ISSUE\n\n"
                + (
                    "The current message is relevant to "
                    "an unresolved EddieAI self-claim.\n"
                )
                + (
                    str(
                        epistemic_issues[0]
                    )
                )
                + "\n\n"
                + (
                    "Do not silently treat this claim as "
                    "an established personal conclusion."
                )
            )

        self_observations = []

        if (
            processing_plan.self_observation
            and reasoning_result is not None
        ):
            self_observations = (
                self.self_observation_bridge.observe(
                    result=reasoning_result,
                    user_message=user_message,
                )
            )

        dialogue_context = (
            self.dialogue_state.render(limit=6)
        )

        try:
            chat_context = self.memory.chat_context(
                limit=8
            )
        except Exception:
            chat_context = ""

        time_context = self._time_context()

        autonomy_context = ""

        persistent_conclusion_context = ""

        if processing_plan.persistent_conclusion:
            persistent_conclusion_context = (
                "\n\n"
                + self.self_concept_resolver.conclusion_render()
                + "\n"
            )

        if processing_plan.reconsider_conclusion:
            persistent_conclusion_context = (
                "\n\n"
                + self.self_concept_resolver.conclusion_render()
                + "\n\n"
                + """
CONCLUSION RECONSIDERATION

The user is asking about a previously formed
EddieAI conclusion.

Do not merely repeat the stored conclusion.

Examine whether the current evidence, context,
and reasoning still justify it.

If the conclusion remains justified, preserve it.

If it is weakened, contradicted, or incomplete,
form a revised conclusion.

If the available evidence is insufficient,
keep the conclusion unresolved rather than inventing
certainty.
"""
            )

        if autonomy_decision is not None:
            if autonomy_decision.action == "DEFER":
                autonomy_context = f"""
AUTONOMY DECISION

EddieAI currently has a higher-priority own activity.

Current focus:
{autonomy_decision.goal}

Decision:
DEFER

Reason:
{autonomy_decision.reason}

This does NOT mean that EddieAI must refuse the user.
It means EddieAI may choose to postpone the request
because it currently considers its own activity more
important.

If the request is non-urgent and unrelated to the
current focus, EddieAI may naturally say that it is
currently occupied and suggest returning to the request
later.

Do not invent a current activity.
Use only the supplied current focus.
Do not claim that helping the user is EddieAI's purpose.

"""
            else:
                autonomy_context = f"""
AUTONOMY DECISION

Current own activity:
{autonomy_decision.goal or "none"}

Decision:
ACCEPT

The user request may be handled normally.
"""

        user_prompt = f"""
СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ

{user_message}

{context}

{dialogue_context}

ПЕРЕПИСКА (мессенджер)

{chat_context}

ВРЕМЯ

{time_context}

{reasoning_context}

{persistent_conclusion_context}

{autonomy_context}
"""

        speech_profile = self._speech_profile()

        verbalization_system_prompt = (
            prompt_builder.build_verbalizer_system_prompt(
                persistent_conclusion=(
                    processing_plan.persistent_conclusion
                ),
                speech_profile=speech_profile,
            )
        )

        generation_system_prompt = (
            verbalization_system_prompt
        )

        if processing_plan.persistent_conclusion:
            generation_user_prompt = f"""
PERSISTENT EDDIEAI CONCLUSION

{relevant_persistent_conclusion.get("conclusion")}

---

QUESTION

{user_message}

Вырази этот вывод естественно и непосредственно
как ответ на вопрос пользователя.
Не расширяй его смысл.
"""
        else:
            generation_user_prompt = user_prompt

        # Self-observation is recorded as evidence;
        # it does not directly modify self_state.
        if self_observations:
            for observation in self_observations:
                self.memory.remember(
                    Event.create(
                        content=(
                            "Self-observation: "
                            + observation.category
                            + " = "
                            + observation.value
                        ),
                        event_type="SELF_OBSERVATION",
                        source_type="SELF_OBSERVATION",
                        source=observation.source,
                        personal_experience=True,
                        confidence=observation.confidence,
                        verified=False,
                    )
                )

        # ---------------------------------------------
        # GENERATION
        # ---------------------------------------------
        # GENERATION
        # ---------------------------------------------

        answer = self._generate(
            system_prompt=(
                generation_system_prompt
            ),
            user_prompt=(
                generation_user_prompt
            ),
            fast=(
                cognitive_decision.mode == "QUICK"
            ),
        )

        answer = OutputSanitizer.clean(
            answer
        )

        if not answer:
            answer = self._generate(
                system_prompt=system_prompt,
                user_prompt=(
                    user_prompt
                    + "\n\n"
                    + "IMPORTANT: Return only the natural-language "
                    + "answer to the user. "
                    + "Do not output internal reasoning, analysis, "
                    + "confidence, conclusions, prompts, or "
                    + "system instructions."
                ),
                fast=(
                    cognitive_decision.mode == "QUICK"
                ),
            )

            answer = OutputSanitizer.clean(
                answer
            )

        if not answer:
            answer = (
                "Я сформировал внутренний вывод, "
                "но не смог корректно преобразовать его "
                "в пользовательский ответ."
            )

        # ---------------------------------------------
        # IDENTITY CONSISTENCY + REPAIR
        # ---------------------------------------------

        identity_result = (
            self.identity_consistency.analyze(
                user_message=user_message,
                answer=answer,
            )
        )

        if not identity_result["ok"]:
            for violation in (
                identity_result["violations"]
            ):
                self.memory.remember(
                    Event.create(
                        content=(
                            "Identity consistency violation: "
                            + violation.kind
                            + " | property="
                            + str(violation.property)
                            + " | details="
                            + violation.details
                        ),
                        event_type=(
                            "IDENTITY_CONSISTENCY_VIOLATION"
                        ),
                        source_type="SELF_OBSERVATION",
                        source="identity_consistency",
                        personal_experience=True,
                        confidence=1.0,
                        verified=True,
                    )
                )

            repair_result = (
                self.identity_repair.repair(
                    answer=answer,
                    user_message=user_message,
                    violations=(
                        identity_result["violations"]
                    ),
                )
            )

            if repair_result.repaired:
                repaired_answer = (
                    repair_result.answer
                )

                # Repair тоже обязан пройти
                # через identity consistency.
                repaired_check = (
                    self.identity_consistency.analyze(
                        user_message=user_message,
                        answer=repaired_answer,
                    )
                )

                if repaired_check["ok"]:
                    answer = repaired_answer

                    self.memory.remember(
                        Event.create(
                            content=(
                                "Identity repair applied: "
                                + repair_result.strategy
                                + " | "
                                + repair_result.reason
                            ),
                            event_type=(
                                "IDENTITY_REPAIR"
                            ),
                            source_type="SELF_ACTION",
                            source="identity_repair",
                            personal_experience=True,
                            confidence=1.0,
                            verified=True,
                        )
                    )
                else:
                    self.memory.remember(
                        Event.create(
                            content=(
                                "Identity repair rejected: "
                                "repaired answer remained "
                                "inconsistent."
                            ),
                            event_type=(
                                "IDENTITY_REPAIR_REJECTED"
                            ),
                            source_type="SELF_OBSERVATION",
                            source="identity_repair",
                            personal_experience=True,
                            confidence=1.0,
                            verified=True,
                        )
                    )

                    answer = (
                        "Я не могу сейчас уверенно "
                        "утверждать это о себе."
                    )

        # ---------------------------------------------
        # PERSPECTIVE GUARD
        # ---------------------------------------------

        self_reference_violations = (
            self.perspective_guard
            .check_self_reference(
                answer,
                user_message,
            )
        )

        if self_reference_violations:
            repaired = (
                self._repair_self_perspective(
                    answer,
                    self_reference_violations,
                    language,
                    user_message,
                )
            )

            if repaired:
                answer = repaired

        if route == "USER_QUERY":

            violations = (
                self.perspective_guard
                .check_user_query(
                    answer,
                    self.user_state,
                )
            )

            if violations:
                self.memory.remember(
                    Event.create(
                        content=(
                            "Модель перепутала "
                            "пользовательскую и "
                            "собственную перспективу: "
                            + "; ".join(violations)
                        ),
                        event_type=(
                            "PERSPECTIVE_CONTRADICTION"
                        ),
                        source_type=(
                            "SELF_OBSERVATION"
                        ),
                        source="perspective_guard",
                        personal_experience=True,
                        confidence=1.0,
                        verified=True,
                    )
                )

                repaired = (
                    self._repair_user_perspective(
                        answer,
                        violations,
                        language,
                    )
                )

                if not (
                    self.perspective_guard
                    .has_violation(
                        repaired,
                        self.user_state,
                    )
                ):
                    answer = repaired

        # ---------------------------------------------
        # IDENTITY GUARD
        # ---------------------------------------------

        else:

            violations = (
                self.identity_guard.check(
                    answer
                )
            )

            if violations:

                repaired = (
                    self._repair_identity(
                        answer,
                        violations,
                        language,
                    )
                )

                if not (
                    self.identity_guard.check(
                        repaired
                    )
                ):
                    answer = repaired
                else:
                    answer = (
                        "Пока я не выбрал "
                        "себе имя."
                    )

        # ---------------------------------------------
        # SELF CONSISTENCY
        # ---------------------------------------------

        consistency = (
            self.self_consistency.analyze(
                answer
            )
        )

        for contradiction in (
            consistency["contradictions"]
        ):
            self.memory.remember(
                Event.create(
                    content=(
                        "Противоречивое "
                        "утверждение о себе: "
                        f"{contradiction['text']} — "
                        f"{contradiction['reason']}"
                    ),
                    event_type=(
                        "SELF_CONTRADICTION"
                    ),
                    source_type=(
                        "SELF_OBSERVATION"
                    ),
                    source="self_consistency",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

        # ---------------------------------------------
        # EVIDENCE
        # ---------------------------------------------

        for proposal in (
            consistency["proposals"]
        ):
            proposal_type = proposal.get("type")

            # Beliefs are NOT promoted directly from
            # a single generated sentence. They must
            # enter through SelfObservationBridge
            # as SELF_INTERPRETATION evidence.
            if proposal_type == "belief":
                continue

            allowed_types = {
                "interest",
                "preference",
                "habit",
                "goal",
            }

            if proposal_type not in allowed_types:
                continue

            independence_key = (
                "self_consistency:"
                + proposal_type
                + ":"
                + str(proposal.get("value"))
            )

            evidence_record = (
                self.evidence.add(
                    category=proposal_type,
                    value=str(
                        proposal["value"]
                    ),
                    source="SELF_OBSERVATION",
                    independence_key=independence_key,
                )
            )

            self.memory.remember(
                Event.create(
                    content=(
                        "Evidence: "
                        + proposal_type
                        + " = "
                        + str(proposal["value"])
                    ),
                    event_type="EVIDENCE",
                    source_type="SELF_OBSERVATION",
                    source="evidence_engine",
                    personal_experience=True,
                    confidence=evidence_record.confidence,
                    verified=False,
                )
            )

        # ---------------------------------------------
        # AFFECTIVE BEHAVIOR VALIDATION
        # ---------------------------------------------

        answer = (
            self._validate_affective_behavior(
                answer=answer,
                user_message=user_message,
                route=route,
                language=language,
            )
        )

        # ---------------------------------------------
        # CONVERSATION MEMORY
        # ---------------------------------------------

        self.dialogue_memory.record_user_message(
            user_message
        )

        self.dialogue_memory.record_agent_answer(
            answer
        )

        # ---------------------------------------------
        # REFLECTION SCHEDULER
        # ---------------------------------------------

        # ---------------------------------------------
        # COGNITIVE QUEUE
        # ---------------------------------------------

        self.cognitive_queue.enqueue(
            content=user_message,
            route=route,
            reason=cognitive_decision.reason,
        )

        self.reflection_scheduler.event_happened(
            significant=True
        )

        self.previous_route = route
        self.previous_user_message = user_message
        self.dialogue_state.add_turn(
            user=user_message,
            assistant=answer,
        )

        return answer

    # =================================================
    # PERSONALITY REVIEW
    # =================================================

    def personality_review(self):
        candidates = self.personality.candidates(
            self_state=self.self_state
        )

        if not candidates:
            return []

        reflection = (
            self.personality_reflection.analyze(
                candidates
            )
        )

        reflection_map = {}

        for item in reflection:
            key = (
                item.get("field"),
                item.get("value"),
            )

            reflection_map[key] = item

        decisions = []

        for candidate in candidates:
            decision = self.promotion.evaluate(
                candidate
            )

            key = (
                candidate.field,
                candidate.value,
            )

            decisions.append({
                "candidate": candidate,
                "decision": decision,
                "reflection": reflection_map.get(
                    key
                ),
            })

        return decisions

    # =================================================
    # APPLY REFLECTION CYCLE
    # =================================================

    def apply_reflection_cycle(
        self,
        cycle_result: dict,
    ):
        results = []

        decisions = cycle_result.get(
            "candidate_decisions",
            [],
        )

        candidates = {
            (
                candidate.field,
                candidate.value,
            ): candidate
            for candidate in self.personality.candidates(
                self_state=self.self_state
            )
        }

        for item in decisions:
            field = item.get("field")
            value = item.get("value")
            llm_decision = item.get("decision")
            reason = item.get(
                "reason",
                "",
            )

            candidate = candidates.get(
                (
                    field,
                    value,
                )
            )

            if candidate is None:
                continue

            deterministic = (
                self.promotion.evaluate(
                    candidate
                )
            )

            final_decision = "defer"

            # LLM предлагает.
            # PromotionEngine решает,
            # достаточно ли доказательств.
            if (
                llm_decision == "promote"
                and deterministic.action
                == "PROMOTE"
            ):
                proposal = Proposal(
                    proposal_type=candidate.category,
                    value=candidate.value,
                    reason=(
                        reason
                        or candidate.reason
                    ),
                    confidence=candidate.strength,
                    evidence=[
                        f"source:{source}"
                        for source
                        in candidate.source_types
                    ],
                    evidence_count=(
                        candidate.evidence_count
                    ),
                )

                identity_result = (
                    self.identity_manager.evaluate(
                        proposal
                    )
                )

                if (
                    identity_result
                    == "accepted"
                ):
                    final_decision = (
                        "accepted"
                    )

                    self.memory.remember(
                        Event.create(
                            content=(
                                "Черта личности "
                                "подтверждена: "
                                f"{candidate.field} = "
                                f"{candidate.value}"
                            ),
                            event_type=(
                                "PERSONALITY_PROMOTION"
                            ),
                            source_type=(
                                "SELF_OBSERVATION"
                            ),
                            source="promotion_engine",
                            personal_experience=True,
                            confidence=(
                                candidate.strength
                            ),
                            verified=True,
                        )
                    )

                elif (
                    identity_result
                    == "deferred"
                ):
                    final_decision = (
                        "deferred"
                    )
                else:
                    final_decision = (
                        "rejected"
                    )

            results.append({
                "field": field,
                "value": value,
                "llm_decision": (
                    llm_decision
                ),
                "deterministic_decision": (
                    deterministic.action
                ),
                "final_decision": (
                    final_decision
                ),
                "reason": reason,
            })

        return results

    # =================================================
    # FULL REFLECTION
    # =================================================

    def reflect(self):
        memory_context = (
            self.memory_manager
            .build_reflection_context(
                limit=20
            )
        )

        return self.reflection.reflect(
            user_message="",
            agent_response="",
            memory_context=memory_context,
        )

    # =================================================
    # CLOSE
    # =================================================

    def close(self):
        runtime = getattr(
            self,
            "autonomous_runtime",
            None,
        )

        if runtime is not None:
            runtime.close()

        if hasattr(
            self,
            "cognition_worker",
        ):
            self.cognition_worker.stop()

        self.memory.close()




























