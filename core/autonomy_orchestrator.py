from dataclasses import dataclass
from datetime import datetime, timezone
import random

from core.decision_core import NEEDS_NEW_PATTERN


@dataclass
class OrchestrationResult:
    status: str
    reason: str
    goal_generation: object | None = None
    execution: object | None = None


FOLLOWUP_TEMPLATES = [
    "Найти новые аспекты темы: {topic}",
    "Связать тему {topic} с другими областями знаний",
    "Сформулировать новые вопросы по теме: {topic}",
    "Расширить понимание темы: {topic} через практический опыт",
    "Проверить выводы по теме: {topic} на новых данных",
    "Найти противоречия в понимании темы: {topic}",
]


class AutonomyOrchestrator:
    """
    Решает, какой этап автономного цикла нужен сейчас.

    Приоритет:
    1. проверить активные цели;
    2. при отсутствии — попробовать создать цель;
    3. при отсутствии — сгенерировать цель-углубление
       на основе завершённых целей (followup);
    4. при отсутствии — decide(): discovery / reflection / ask;
    5. при наличии цели без плана — создать план;
    6. при готовой цели — выполнить один шаг.
    """

    def __init__(
        self,
        goal_manager,
        goal_generator,
        goal_plan_generator,
        agent_loop,
        agent=None,
        affective_behavior_policy=None,
        outbox=None,
        server=None,
        decision_core=None,
    ):
        self.goal_manager = goal_manager
        self.goal_generator = goal_generator
        self.goal_plan_generator = goal_plan_generator
        self.agent_loop = agent_loop
        self.agent = agent
        self.affective_behavior_policy = (
            affective_behavior_policy
        )
        self.outbox = outbox
        self.server = server
        self.decision_core = decision_core
        self._last_action_at = None

    def _extract_topic(self, goal_value: str) -> str:
        for prefix in (
            "изучить тему: ",
            "углубить понимание темы: ",
            "найти новые аспекты темы: ",
            "связать тему ",
            "сформулировать новые вопросы по теме: ",
            "расширить понимание темы: ",
            "проверить выводы по теме: ",
            "найти противоречия в понимании темы: ",
        ):
            if goal_value.lower().startswith(prefix):
                return goal_value[len(prefix):]
        return goal_value

    def _generate_followup(self, completed_goal):
        topic = self._extract_topic(
            completed_goal.value
        )

        all_goals = {
            g.value.lower()
            for g in self.goal_manager.all()
        }

        candidates = []

        for template in FOLLOWUP_TEMPLATES:
            candidate_value = template.format(
                topic=topic
            )

            if (
                candidate_value.lower()
                not in all_goals
            ):
                candidates.append(candidate_value)

        if not candidates:
            return None

        chosen = random.choice(candidates)

        goal = self.goal_manager.add_candidate(
            value=chosen,
            motivation=max(
                0.70,
                completed_goal.motivation,
            ),
            priority=max(
                0.60,
                completed_goal.priority,
            ),
            confidence=max(
                0.65,
                completed_goal.confidence,
            ),
            source="followup_reflection",
        )

        decision = self.goal_generator.goal_review.evaluate(
            goal
        )

        if decision.action == "ACTIVATE":
            self.goal_manager.activate(goal.value)

        return goal

    def _handle_inbox(self):
        return None

    def _tick_local(self):
        state = self._build_state()

        decision = self.decision_core.decide(state)

        if decision is NEEDS_NEW_PATTERN:
            decision = self.decision_core.learn(
                self.decision_core.key(state),
                self._situation_context(state),
            )

        result = self._apply_action(
            decision,
            state,
        )

        if result.status not in {
            "NO_MOTIVATION",
            "INBOX_READ",
        }:
            self._last_action_at = (
                datetime.now(timezone.utc)
            )

        return result

    def _build_state(self):
        active = self.goal_manager.active()

        goal_value = (
            active[0].value
            if active
            else None
        )

        inbox = 0

        server = getattr(
            self,
            "server",
            None,
        )

        history = (
            getattr(server, "history", None)
            if server is not None
            else None
        )

        if history is not None:
            try:
                meta = history.chat_unread_meta()
                inbox = int(meta["count"])
            except Exception:
                inbox = 0

        idle_seconds = 0

        if self._last_action_at is not None:
            try:
                idle_seconds = max(
                    0,
                    int(
                        (
                            datetime.now(timezone.utc)
                            - self._last_action_at
                        ).total_seconds()
                    ),
                )
            except Exception:
                idle_seconds = 0

        return {
            "goal": goal_value,
            "task_type": None,
            "inbox_unread": inbox,
            "affect": self._affect_valence(),
            "emotions": self._affect_emotions(),
            "freshness": 0,
            "idle_seconds": idle_seconds,
        }

    def _affect_emotions(self):
        state = getattr(
            self.agent,
            "affective_state",
            None,
        )

        if state is None:
            return {}

        try:
            return dict(
                state.snapshot().get(
                    "emotions",
                    {},
                )
            )
        except Exception:
            return {}

    def _affect_valence(self):
        state = getattr(
            self.agent,
            "affective_state",
            None,
        )

        if state is None:
            return None

        try:
            snap = state.snapshot()
        except Exception:
            return None

        emotions = snap.get(
            "emotions",
            {},
        )

        positive = sum(
            float(emotions.get(key, 0.0))
            for key in (
                "joy",
                "surprise",
                "interest",
                "curiosity",
                "satisfaction",
            )
        )

        negative = sum(
            float(emotions.get(key, 0.0))
            for key in (
                "sadness",
                "fear",
                "anger",
                "disgust",
                "frustration",
                "uncertainty",
            )
        )

        return max(
            -1.0,
            min(1.0, positive - negative),
        )

    def _situation_context(self, state):
        active = self.goal_manager.active()

        plan_tasks = 0

        if active:
            try:
                plan = (
                    self.goal_manager
                    .planner
                    .get_plan(active[0].value)
                )

                plan_tasks = len(plan)
            except Exception:
                plan_tasks = 0

        return (
            f"Активная цель: "
            f"{state.get('goal') or 'нет'}\n"
            f"Задач в плане: {plan_tasks}\n"
            f"Непрочитанных сообщений Эдди: "
            f"{state.get('inbox_unread')}\n"
            f"Аффект: "
            f"{state.get('affect') or 'нейтральный'}"
        )

    def _apply_action(self, action, state):
        kind = action.kind
        payload = action.payload or {}

        if kind == "EXECUTE":
            return self._execute_step(
                state.get("goal")
            )

        if kind == "GENERATE_PLAN":
            goal = payload.get(
                "goal"
            ) or state.get("goal")

            if not goal:
                return OrchestrationResult(
                    status="NO_MOTIVATION",
                    reason=(
                        "Локальное ядро попросило "
                        "план, но цель не найдена."
                    ),
                )

            self.goal_plan_generator.generate(
                goal=goal,
                context=(
                    "Автономно выбранная "
                    "активная цель."
                ),
            )

            return OrchestrationResult(
                status="PLAN_CREATED",
                reason=(
                    "Для активной цели "
                    "создан план."
                ),
            )

        if kind == "ACTIVATE_GOAL":
            value = payload.get("value")

            if not value:
                return OrchestrationResult(
                    status="NO_MOTIVATION",
                    reason=(
                        "Ядро выбрало активацию "
                        "цели, но цель не задана."
                    ),
                )

            if self.goal_manager.get(value) is None:
                self.goal_manager.add_candidate(
                    value=value,
                    motivation=0.60,
                    priority=0.50,
                    confidence=0.60,
                    source="decision_core",
                )

            self.goal_manager.activate(value)

            return OrchestrationResult(
                status="GOAL_ACTIVATED",
                reason=(
                    "Активирована цель: "
                    f"{value}"
                ),
            )

        if kind == "COMPLETE_GOAL":
            goal = payload.get("goal")

            if goal:
                try:
                    self.goal_manager.sync_progress(goal)
                except Exception:
                    pass

            return OrchestrationResult(
                status="GOAL_COMPLETED",
                reason=(
                    "Текущая цель завершена "
                    "локальным ядром."
                ),
            )

        if kind == "ASK":
            return OrchestrationResult(
                status="ASKED",
                reason=(
                    "EddieAI решил спросить Эдди "
                    "о направлении."
                ),
            )

        if kind == "REFLECT":
            return self._reflection_action()

        if kind == "READ_INBOX":
            server = getattr(
                self, "server", None
            )

            if server is not None:
                try:
                    server.respond_and_deliver()
                except Exception:
                    pass

            return OrchestrationResult(
                status="INBOX_READ",
                reason=(
                    "EddieAI решил прочитать "
                    "и ответить."
                ),
            )

        return OrchestrationResult(
            status="NO_MOTIVATION",
            reason=(
                "Локальное ядро не нашло "
                "подходящего действия."
            ),
        )

    def _execute_step(self, goal):
        if self.agent is not None:
            self.agent.autonomy_execution_state = {
                "busy": True,
                "goal": goal,
                "task": None,
            }

        import time as _time

        try:
            _start = _time.time()

            execution = self.agent_loop.run_once()

            _duration = (
                _time.time() - _start
            )
        finally:
            if self.agent is not None:
                self.agent.autonomy_execution_state = {
                    "busy": False,
                    "goal": None,
                    "task": None,
                }

        try:
            from core.time_perception import (
                record_action_time,
            )

            record_action_time(
                self.agent.memory,
                f"Выполнение шага цели '{goal}'",
                _duration,
            )
        except Exception:
            pass

        return OrchestrationResult(
            status="EXECUTED",
            reason=(
                "Выполнен один автономный "
                "шаг активной цели."
            ),
            execution=execution,
        )

    def _reflection_action(self):
        goal = self.goal_manager.add_candidate(
            value=(
                "Подвести итог: что я узнал "
                "за последнее время"
            ),
            motivation=0.60,
            priority=0.50,
            confidence=0.60,
            source="reflection_decide",
        )

        self.goal_manager.activate(goal.value)

        return OrchestrationResult(
            status="REFLECTION",
            reason=(
                "EddieAI решил подвести "
                "итог накопленного опыта."
            ),
        )

    def _decide(self):
        """
        Анализирует ситуацию и выбирает действие
        когда мотивационная система молчит.

        Возвращает цель для активации или None.
        """
        now = datetime.now(timezone.utc)

        inbox_action = self._handle_inbox()

        if inbox_action:
            return inbox_action

        # -----------------------------------------
        # 1. Discovery: создать цель из тем памяти
        # -----------------------------------------

        motivation = getattr(
            self.goal_generator,
            "motivation_engine",
            None,
        )

        if motivation is not None:
            try:
                candidates = motivation.candidates()

                discovery = [
                    c
                    for c in candidates
                    if any(
                        "discovery:" in s
                        for s in c.source_traits
                    )
                ]

                if discovery:
                    best = max(
                        discovery,
                        key=lambda c: c.motivation,
                    )

                    goal = (
                        self.goal_manager.add_candidate(
                            value=best.goal,
                            motivation=best.motivation,
                            priority=best.priority,
                            confidence=best.confidence,
                            source="discovery_decide",
                        )
                    )

                    self.goal_manager.activate(
                        goal.value
                    )

                    active = (
                        self.goal_manager.active()
                    )

                    if active:
                        return active[0]
            except Exception:
                pass

        # -----------------------------------------
        # 2. Reflection: подвести итог если давно
        #    ничего не делали
        # -----------------------------------------

        if self._last_action_at is not None:
            elapsed = (
                now - self._last_action_at
            ).total_seconds()

            if elapsed > 3600:
                goal = (
                    self.goal_manager.add_candidate(
                        value=(
                            "Подвести итог: "
                            "что я узнал за последнее время"
                        ),
                        motivation=0.60,
                        priority=0.50,
                        confidence=0.60,
                        source="reflection_decide",
                    )
                )

                self.goal_manager.activate(
                    goal.value
                )

                active = (
                    self.goal_manager.active()
                )

                if active:
                    return active[0]

        # -----------------------------------------
        # 3. Ask: попросить направление
        # -----------------------------------------

        all_goals = self.goal_manager.all()

        if len(all_goals) >= 6:
            completed = [
                g
                for g in all_goals
                if g.status == "COMPLETED"
            ]

            if len(completed) >= 3:
                goal = (
                    self.goal_manager.add_candidate(
                        value=(
                            "Спросить Эдди: "
                            "какие темы исследовать дальше"
                        ),
                        motivation=0.65,
                        priority=0.55,
                        confidence=0.60,
                        source="ask_decide",
                    )
                )

                self.goal_manager.activate(
                    goal.value
                )

                active = (
                    self.goal_manager.active()
                )

                if active:
                    return active[0]

        return None

    def tick(self):
        if self.decision_core is not None:
            return self._tick_local()

        active = self.goal_manager.active()

        # -----------------------------------------
        # Нет активных целей
        # -----------------------------------------

        if not active:
            generated = (
                self.goal_generator.generate()
            )

            active = self.goal_manager.active()

            if not active:
                completed = [
                    g
                    for g in self.goal_manager.all()
                    if g.status == "COMPLETED"
                ]

                if completed:
                    followup = (
                        self._generate_followup(
                            completed[0]
                        )
                    )

                    active = (
                        self.goal_manager.active()
                    )

                if not active:
                    decided = self._decide()

                    if decided is not None:
                        goal = decided
                    else:
                        return OrchestrationResult(
                            status="NO_MOTIVATION",
                            reason=(
                                "Нет активных целей, "
                                "мотивационная система "
                                "и отражение завершённого "
                                "не создали новую цель."
                            ),
                            goal_generation=generated,
                        )
                else:
                    goal = active[0]

            else:
                goal = active[0]

        else:
            scored_goals = []

            for item in active:
                base_score = (
                    float(item.priority) * 0.50
                    + float(item.motivation) * 0.30
                    + float(item.confidence) * 0.20
                )

                affective_bias = 0.0

                if (
                    self.affective_behavior_policy
                    is not None
                ):
                    affective_bias = (
                        self.affective_behavior_policy
                        .goal_bias(item)
                    )

                scored_goals.append({
                    "goal": item,
                    "base_score": round(
                        base_score,
                        4,
                    ),
                    "affective_bias": (
                        affective_bias
                    ),
                    "total_score": round(
                        base_score
                        + affective_bias,
                        4,
                    ),
                })

            scored_goals.sort(
                key=lambda item: (
                    item["total_score"],
                    float(
                        item["goal"].priority
                    ),
                    float(
                        item["goal"].motivation
                    ),
                ),
                reverse=True,
            )

            goal = scored_goals[0]["goal"]

        # -----------------------------------------
        # Нет плана
        # -----------------------------------------

        existing_plan = (
            self.goal_manager.planner
            .get_plan(
                goal.value
            )
        )

        if existing_plan is None:
            plan = (
                self.goal_plan_generator.generate(
                    goal=goal.value,
                    context=(
                        "Автономно созданная "
                        "активная цель."
                    ),
                )
            )

            return OrchestrationResult(
                status="PLAN_CREATED",
                reason=(
                    "Для активной цели "
                    "создан план."
                ),
                execution=None,
                goal_generation=None,
            )

        # -----------------------------------------
        # Есть цель и план
        # -----------------------------------------

        if self.agent is not None:
            self.agent.autonomy_execution_state = {
                "busy": True,
                "goal": goal.value,
                "task": None,
            }

        try:
            execution = (
                self.agent_loop.run_once()
            )
        finally:
            if self.agent is not None:
                self.agent.autonomy_execution_state = {
                    "busy": False,
                    "goal": None,
                    "task": None,
                }

        return OrchestrationResult(
            status="EXECUTED",
            reason=(
                "Выполнен один автономный "
                "шаг активной цели."
            ),
            execution=execution,
        )
