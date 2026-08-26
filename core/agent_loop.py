import json

from identity.action_choice import ActionChoice
from identity.action_selector import ActionSelector
from identity.action_preference_detector import ActionPreferenceDetector
from identity.habit_pattern_detector import HabitPatternDetector
from identity.belief_pattern_detector import BeliefPatternDetector
from memory.events import Event
from identity.proposal import Proposal

from dataclasses import dataclass





@dataclass

class LoopResult:

    status: str

    goal: str | None

    actions_executed: int

    steps: list





class AgentLoop:

    def __init__(

        self,

        goal_manager,

        goal_planner,

        action_planner,

        tool_runner,

        task_controller,

        experience_recorder,

        max_actions: int = 3,

        experience_consolidator=None,

        research_context=None,

        adaptive_planner=None,

        adaptive_plan_controller=None,

        reflection_engine=None,

        action_preference_detector=None,

        habit_pattern_detector=None,

        belief_pattern_detector=None,

        evidence=None,

        identity_manager=None,
        goal_review=None,
        appraisal_engine=None,
        affective_state=None,
        belief_challenge_detector=None,
        affective_behavior_policy=None,
        outbox=None,
    ):

        self.goal_manager = goal_manager
        self.goal_review = goal_review

        self.appraisal_engine = (
            appraisal_engine
        )

        self.affective_state = (
            affective_state
        )

        self.belief_challenge_detector = (
            belief_challenge_detector
        )

        self.affective_behavior_policy = (
            affective_behavior_policy
        )

        self.outbox = outbox

        self.goal_affective_memory = (
            getattr(
                affective_behavior_policy,
                "goal_affective_memory",
                None,
            )
        )

        self.goal_planner = goal_planner

        self.action_planner = action_planner

        self.tool_runner = tool_runner

        self.task_controller = task_controller



        self.experience_recorder = (

            experience_recorder

        )

        self.action_selector = ActionSelector(
            self.experience_recorder.memory
        )



        self.experience_consolidator = (

            experience_consolidator

        )



        self.research_context = (

            research_context

        )



        self.adaptive_planner = (

            adaptive_planner

        )



        self.adaptive_plan_controller = (

            adaptive_plan_controller

        )



        self.reflection_engine = (

            reflection_engine

        )



        self.action_preference_detector = (
            action_preference_detector
        )

        self.habit_pattern_detector = (
            habit_pattern_detector
        )

        self.belief_pattern_detector = (
            belief_pattern_detector
        )

        self.evidence = evidence

        self.identity_manager = (
            identity_manager
        )



        self.max_actions = max(

            1,

            int(max_actions),

        )



    def _process_identity_detectors(
        self,
    ):
        results = []

        detectors = (
            (
                "preference",
                self.action_preference_detector,
            ),
            (
                "habit",
                self.habit_pattern_detector,
            ),
            (
                "belief",
                self.belief_pattern_detector,
            ),
        )

        if self.identity_manager is None:
            return results

        for category, detector in detectors:
            if detector is None:
                continue

            detected = detector.detect()

            for item in detected:
                value = item.get("value")

                if not isinstance(
                    value,
                    str,
                ):
                    continue

                confidence = 0.0
                evidence_count = int(
                    item.get(
                        "created_evidence",
                        0,
                    )
                )
                evidence = []

                if self.evidence is not None:
                    try:
                        record = (
                            self.evidence.get(
                                category,
                                value,
                            )
                        )

                        confidence = (
                            record.confidence
                        )

                        evidence_count = (
                            record.count
                        )

                        evidence = [
                            f"source:{source}"
                            for source
                            in record.source_types
                        ]

                    except ValueError:
                        pass

                if confidence <= 0:
                    confidence = float(
                        item.get(
                            "average_confidence",
                            item.get(
                                "share",
                                0.0,
                            ),
                        )
                    )

                if confidence < 0.75:
                    results.append({
                        "category": category,
                        "value": value,
                        "result": "deferred",
                        "confidence": confidence,
                    })
                    continue

                proposal = Proposal(
                    proposal_type=category,
                    value=value,
                    reason=(
                        "Наблюдение подтверждено "
                        f"повторными свидетельствами "
                        f"{category}: {value}"
                    ),
                    confidence=confidence,
                    evidence=evidence,
                    evidence_count=evidence_count,
                )

                identity_result = (
                    self.identity_manager
                    .evaluate(
                        proposal
                    )
                )

                results.append({
                    "category": category,
                    "value": value,
                    "result": identity_result,
                    "confidence": confidence,
                    "proposal": (
                        proposal.to_dict()
                    ),
                })

        return results

    def _process_follow_up_goals(
        self,
        reflection,
        completed_goal: str,
    ):
        """
        Обрабатывает follow-up candidates,
        появившиеся из reflection завершённой цели.

        Reflection только предлагает.
        GoalReview принимает решение.
        GoalManager изменяет состояние.
        """

        if not isinstance(
            reflection,
            dict,
        ):
            return []

        follow_up_goals = reflection.get(
            "follow_up_goals",
            [],
        )

        if not isinstance(
            follow_up_goals,
            list,
        ):
            return []

        if self.goal_review is None:
            return []

        results = []

        for candidate_data in follow_up_goals:
            if not isinstance(
                candidate_data,
                dict,
            ):
                continue

            goal_value = str(
                candidate_data.get(
                    "goal",
                    "",
                )
            ).strip()

            if not goal_value:
                continue

            if (
                goal_value.casefold()
                == completed_goal.casefold()
            ):
                results.append({
                    "goal": goal_value,
                    "status": "REJECTED",
                    "reason": (
                        "Follow-up совпадает "
                        "с завершённой целью."
                    ),
                })
                continue

            if self.goal_manager.get(
                goal_value
            ) is not None:
                results.append({
                    "goal": goal_value,
                    "status": "EXISTS",
                    "reason": (
                        "Такая цель уже существует."
                    ),
                })
                continue

            motivation = float(
                candidate_data.get(
                    "motivation",
                    0.0,
                )
            )

            priority = float(
                candidate_data.get(
                    "priority",
                    0.0,
                )
            )

            confidence = float(
                candidate_data.get(
                    "confidence",
                    0.0,
                )
            )

            candidate = (
                self.goal_manager.add_candidate(
                    value=goal_value,
                    motivation=motivation,
                    priority=priority,
                    confidence=confidence,
                    source="reflection",
                )
            )

            decision = (
                self.goal_review.evaluate(
                    candidate
                )
            )

            if decision.action != "ACTIVATE":
                results.append({
                    "goal": goal_value,
                    "status": "DEFERRED",
                    "review": decision.reason,
                })
                continue

            activation = (
                self.goal_manager.activate(
                    goal_value
                )
            )

            if activation.get(
                "status"
            ) != "ACTIVATED":
                results.append({
                    "goal": goal_value,
                    "status": "DEFERRED",
                    "review": (
                        activation.get(
                            "reason",
                            "Активация не удалась.",
                        )
                    ),
                })
                continue

            results.append({
                "goal": goal_value,
                "status": "ACTIVATED",
                "review": decision.reason,
            })

        return results


    def run_once(self):

        goal = self.goal_manager.best_candidate()



        if (

            goal is not None

            and goal.status != "ACTIVE"

        ):

            activation = self.goal_manager.activate(

                goal.value

            )


            if activation.get(

                "status"

            ) != "ACTIVATED":

                goal = None



        if goal is None:

            active = self.goal_manager.active()



            if not active:

                return LoopResult(

                    status="NO_GOAL",

                    goal=None,

                    actions_executed=0,

                    steps=[],

                )



            goal = sorted(

                active,

                key=lambda item: (

                    item.priority,

                    item.motivation,

                ),

                reverse=True,

            )[0]



        steps = []

        actions_executed = 0



        for _ in range(self.max_actions):

            task = (

                self.goal_manager.activate_next_task(

                    goal.value

                )

            )



            if task is None:

                self.goal_manager.sync_progress(

                    goal.value

                )



                current_goal = (

                    self.goal_manager.get(

                        goal.value

                    )

                )



                if (

                    current_goal.status

                    == "COMPLETED"

                ):

                    if self.outbox is not None:

                        self.outbox.send(

                            f"Цель завершена: "

                            f"{goal.value}"

                        )

                    return LoopResult(

                        status="GOAL_COMPLETED",

                        goal=goal.value,

                        actions_executed=(

                            actions_executed

                        ),

                        steps=steps,

                    )



                return LoopResult(

                    status="NO_TASK",

                    goal=goal.value,

                    actions_executed=(

                        actions_executed

                    ),

                    steps=steps,

                )



            context = ""



            if self.research_context is not None:

                context = (

                    self.research_context.build(

                        query=goal.value

                    )

                )



            action_options = (

                self.action_planner.alternatives(
                    task,
                    context=context,
                )
            )

            behavioral_biases = {}

            if (
                self.affective_behavior_policy
                is not None
            ):
                behavioral_biases = (
                    self.affective_behavior_policy
                    .biases(
                        options=action_options,
                        task=task,
                    )
                )

            selection = (
                self.action_selector.select(
                    action_options,
                    behavioral_biases=(
                        behavioral_biases
                    ),
                )
            )

            action_plan = (
                selection.selected
            )

            action_choice = ActionChoice(
                task=task.title,
                task_type=action_plan.action_type,
                context_type=(
                    self.action_planner
                    .context_type(task)
                ),
                options=[
                    option.action_type
                    for option
                    in selection.options
                ],
                selected=(
                    action_plan.action_type
                ),
                reason=selection.reason,
            )

            self.experience_recorder.memory.remember(

                Event.create(

                    content=json.dumps(
                        {
                            "type": "ACTION_CHOICE",
                            "choice": (
                                action_choice.to_dict()
                            ),
                        },
                        ensure_ascii=False,
                    ),

                    event_type="ACTION_CHOICE",

                    source_type="SELF_ACTION",

                    source="action_selector",

                    personal_experience=True,

                    confidence=1.0,

                    verified=True,

                )

            )

            identity_results = (
                self._process_identity_detectors()
            )

            preference_results = [
                item
                for item in identity_results
                if item["category"]
                == "preference"
            ]

            identity_results = (
                identity_results
            )

            action = (

                self.tool_runner.executor.create(

                    action_type=(

                        action_plan.action_type

                    ),

                    target=action_plan.target,

                    parameters=(

                        action_plan.parameters

                    ),

                    reason=action_plan.reason,

                    dry_run=False,

                )

            )



            result = self.tool_runner.run(

                action

            )

            # Старые affective reactions постепенно затухают
            # перед оценкой нового события.
            if self.affective_state is not None:
                self.affective_state.decay()

            appraisal_result = None

            if self.appraisal_engine is not None:
                appraisal_result = (
                    self.appraisal_engine.appraise(
                        goal=goal.value,
                        task=task.title,
                        action=action.to_dict(),
                        result=result,
                    )
                )

                if (
                    self.experience_recorder
                    is not None
                    and hasattr(
                        self.experience_recorder,
                        "memory",
                    )
                    and appraisal_result[
                        "changes"
                    ]
                ):
                    self.experience_recorder.memory.remember(
                        Event.create(
                            content=(
                                "Автоматическая "
                                "affective reaction: "
                                + str(
                                    appraisal_result[
                                        "changes"
                                    ]
                                )
                            ),
                            event_type=(
                                "AFFECTIVE_REACTION"
                            ),
                            source_type=(
                                "APPRAISAL_ENGINE"
                            ),
                            source="SELF",
                            personal_experience=True,
                            confidence=1.0,
                            verified=True,
                        )
                    )

                # Affective reaction happens automatically
                # from the event. It is not selected by
                # the personality or by the LLM.
                self.experience_recorder.memory

                if appraisal_result[
                    "changes"
                ]:
                    self.appraisal_engine

                    # Apply through Agent-owned
                    # affective state if available.
                    affective_state = getattr(
                        self,
                        "affective_state",
                        None,
                    )

                    if affective_state is not None:
                        affective_state.apply_reaction(
                            changes=(
                                appraisal_result[
                                    "changes"
                                ]
                            ),
                            trigger=(
                                appraisal_result[
                                    "trigger"
                                ]
                            ),
                            reason=(
                                "Реакция автоматически "
                                "возникла вследствие оценки "
                                "завершённого события."
                            ),
                            source="APPRAISAL_ENGINE",
                            metadata={
                                "goal": goal.value,
                                "task": task.title,
                                "action_type": action.to_dict().get(
                                    "action_type"
                                ),
                                "appraisal": (
                                    appraisal_result[
                                        "appraisal"
                                    ]
                                ),
                            },
                        )

                        if (
                            hasattr(
                                self,
                                "goal_affective_memory",
                            )
                            and
                            self.goal_affective_memory
                            is not None
                        ):
                            self.goal_affective_memory.record(
                                goal=goal.value,
                                changes=(
                                    appraisal_result[
                                        "changes"
                                    ]
                                ),
                                trigger=(
                                    appraisal_result[
                                        "trigger"
                                    ]
                                ),
                            )

            actions_executed += 1



            recorded = (

                self.experience_recorder.record(

                    action,

                    result,

                    owner="SELF",

                    personal_experience=True,

                )

            )



            consolidated = None



            if (

                self.experience_consolidator

                is not None

            ):

                consolidated = (

                    self.experience_consolidator

                    .record(

                        action,

                        result,

                    )

                )



            task_result = (

                self.task_controller.execute_result(

                    goal.value,

                    task.title,

                    result,

                    activate_next=False,

                )

            )



            adaptive_result = None



            if (

                result.get("status") == "OK"

                and self.adaptive_planner

                is not None

                and self.adaptive_plan_controller

                is not None

            ):

                remaining_tasks = [

                    pending.title

                    for pending

                    in self.goal_planner.tasks(

                        goal.value

                    )

                    if pending.status

                    in {

                        "PENDING",

                        "ACTIVE",

                    }

                ]



                adaptive_decision = (

                    self.adaptive_planner.review(

                        goal=goal.value,

                        completed_task=task.title,

                        result=result,

                        remaining_tasks=(

                            remaining_tasks

                        ),

                    )

                )



                adaptive_result = (

                    self.adaptive_plan_controller.apply(

                        goal=goal.value,

                        decision=adaptive_decision,

                    )

                )



            reflection = None



            if (

                result.get("status") == "OK"

                and self.reflection_engine

                is not None

            ):

                reflection = (

                    self.reflection_engine.reflect(

                        goal=goal.value,

                        task=task.title,

                        action=action.to_dict(),

                        result=result,

                    )

                )



            next_task = (

                self.goal_manager

                .activate_next_task(

                    goal.value

                )

            )

            # -------------------------------------------------
            # FOLLOW-UP GOALS
            # -------------------------------------------------
            #
            # Reflection may suggest what EddieAI could pursue
            # next, but only a completed current goal can trigger
            # this transition. Reflection itself has no authority
            # to modify the goal state.
            #

            follow_up_results = []

            current_goal = (
                self.goal_manager.get(
                    goal.value
                )
            )

            if (
                reflection
                and current_goal is not None
                and current_goal.status == "COMPLETED"
            ):
                follow_up_results = (
                    self._process_follow_up_goals(
                        reflection=reflection,
                        completed_goal=goal.value,
                    )
                )

            if isinstance(
                task_result,
                dict,
            ):
                task_result[
                    "next_task"
                ] = next_task
                task_result[
                    "follow_up_goals"
                ] = follow_up_results

                task_result[

                    "next_task"

                ] = next_task



            steps.append({

                "task": task.title,

                "action": action.to_dict(),

                "result": result,

                "context_used": context,

                "experience": (

                    recorded["event"].content

                ),

                "consolidated_experience": (

                    consolidated

                ),

                "task_result": task_result,

                "adaptive_result": (

                    adaptive_result

                ),

                "preference_results": (

                    preference_results

                ),

                "identity_results": (

                    identity_results

                ),

                "reflection": reflection,

            })



            if result.get("status") != "OK":

                return LoopResult(

                    status="ACTION_FAILED",

                    goal=goal.value,

                    actions_executed=(

                        actions_executed

                    ),

                    steps=steps,

                )



            updated_goal = (

                self.goal_manager.sync_progress(

                    goal.value

                )

            )



            if (

                updated_goal.status

                == "COMPLETED"

            ):

                if self.outbox is not None:

                    self.outbox.send(

                        f"Цель завершена: "

                        f"{goal.value}"

                    )

                return LoopResult(

                    status="GOAL_COMPLETED",

                    goal=goal.value,

                    actions_executed=(

                        actions_executed

                    ),

                    steps=steps,

                )



        return LoopResult(

            status="ACTION_LIMIT_REACHED",

            goal=goal.value,

            actions_executed=actions_executed,

            steps=steps,

        )

