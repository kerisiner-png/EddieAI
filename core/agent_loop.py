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

    ):

        self.goal_manager = goal_manager

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
                        "????????????? ????????? "
                        f"?????????? ??????? "
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

    def run_once(self):

        goal = self.goal_manager.best_candidate()



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



        if goal.status != "ACTIVE":

            activation = self.goal_manager.activate(

                goal.value

            )



            if activation.get(

                "status"

            ) != "ACTIVATED":

                return LoopResult(

                    status="GOAL_NOT_ACTIVATED",

                    goal=goal.value,

                    actions_executed=0,

                    steps=[],

                )



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

            selection = (
                self.action_selector.select(
                    action_options
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



            if isinstance(

                task_result,

                dict,

            ):

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

