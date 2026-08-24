import json

from identity.proposal import Proposal
from memory.events import Event


class CognitiveDecisionEngine:
    """
    Преобразует результат CognitiveProcessor
    в допустимое действие системы.

    LLM не получает права напрямую менять self_state.
    """

    VALID_ACTIONS = {
        "IGNORE",
        "RETAIN",
        "MORE_EVIDENCE",
        "UPDATE_SELF",
        "CREATE_GOAL",
    }

    IDENTITY_FIELDS = {
        "INTEREST": "interest",
        "USER_INTEREST": "interest",
        "PREFERENCE": "preference",
        "HABIT": "habit",
        "BELIEF": "belief",
        "GOAL": "goal",
    }

    def __init__(
        self,
        agent,
    ):
        self.agent = agent
        self.memory = agent.memory
        self.identity_manager = (
            agent.identity_manager
        )
        self.evidence = agent.evidence

    def decide(
        self,
        *,
        item,
        analysis: dict,
    ) -> dict:

        action = str(
            analysis.get(
                "action",
                "RETAIN",
            )
        ).upper()

        if action not in self.VALID_ACTIONS:
            action = "RETAIN"

        importance = self._importance(
            analysis
        )

        decision = {
            "action": action,
            "importance": importance,
            "applied": False,
            "reason": "",
        }

        # ---------------------------------------------
        # IGNORE
        # ---------------------------------------------

        if action == "IGNORE":
            decision["applied"] = True
            decision["reason"] = (
                "Событие не требует дальнейшего "
                "когнитивного действия."
            )

            return self._record(
                item,
                analysis,
                decision,
            )

        # ---------------------------------------------
        # RETAIN
        # ---------------------------------------------

        if action == "RETAIN":
            decision["applied"] = True
            decision["reason"] = (
                "Событие сохраняется как опыт "
                "без изменения личности."
            )

            return self._record(
                item,
                analysis,
                decision,
            )

        # ---------------------------------------------
        # MORE EVIDENCE
        # ---------------------------------------------

        if action == "MORE_EVIDENCE":
            decision["applied"] = True
            decision["reason"] = (
                "Недостаточно оснований для изменения "
                "self-model. Требуется дополнительное "
                "подтверждение."
            )

            return self._record(
                item,
                analysis,
                decision,
            )

        # ---------------------------------------------
        # UPDATE SELF
        # ---------------------------------------------

        if action == "UPDATE_SELF":
            result = self._update_self(
                item,
                analysis,
                importance,
            )

            decision.update(result)

            return self._record(
                item,
                analysis,
                decision,
            )

        # ---------------------------------------------
        # CREATE GOAL
        # ---------------------------------------------

        if action == "CREATE_GOAL":
            result = self._create_goal(
                item,
                analysis,
                importance,
            )

            decision.update(result)

            return self._record(
                item,
                analysis,
                decision,
            )

        return self._record(
            item,
            analysis,
            decision,
        )

    def _update_self(
        self,
        item,
        analysis: dict,
        importance: float,
    ) -> dict:

        if not analysis.get(
            "self_update",
            False,
        ):
            return {
                "applied": False,
                "reason": (
                    "Анализ не разрешает "
                    "изменение self-model."
                ),
            }

        if importance < 0.75:
            return {
                "applied": False,
                "reason": (
                    "Уверенность ниже порога "
                    "IdentityManager."
                ),
            }

        if self._is_user_owned(
            item,
            analysis,
        ):
            return {
                "applied": False,
                "reason": (
                    "Пользовательское утверждение "
                    "не может напрямую изменить "
                    "self-model EddieAI."
                ),
            }

        proposal_type = (
            self.IDENTITY_FIELDS.get(
                str(
                    analysis.get(
                        "type",
                        "",
                    )
                ).upper()
            )
        )

        value = analysis.get(
            "value"
        )

        if proposal_type is None:
            return {
                "applied": False,
                "reason": (
                    "Тип изменения не разрешён "
                    "IdentityManager."
                ),
            }

        if not isinstance(
            value,
            str,
        ) or not value.strip():
            return {
                "applied": False,
                "reason": (
                    "Для UPDATE_SELF отсутствует "
                    "конкретное значение."
                ),
            }

        proposal = Proposal(
            proposal_type=proposal_type,
            value=value.strip(),
            reason=(
                analysis.get(
                    "interpretation",
                    "",
                )
            ),
            confidence=importance,
            evidence=[
                f"cognitive:{item.id}",
            ],
            evidence_count=1,
        )

        result = (
            self.identity_manager.evaluate(
                proposal
            )
        )

        return {
            "applied": result == "accepted",
            "identity_result": result,
            "reason": (
                "IdentityManager: "
                + result
            ),
        }

    def _create_goal(
        self,
        item,
        analysis: dict,
        importance: float,
    ) -> dict:

        if self._is_user_owned(
            item,
            analysis,
        ):
            return {
                "applied": False,
                "reason": (
                    "Пользовательская реплика "
                    "не может напрямую создать "
                    "собственную цель EddieAI."
                ),
            }

        if importance < 0.70:
            return {
                "applied": False,
                "reason": (
                    "Значимость цели недостаточна."
                ),
            }

        value = analysis.get(
            "value"
        )

        if not isinstance(
            value,
            str,
        ) or not value.strip():
            return {
                "applied": False,
                "reason": (
                    "Для CREATE_GOAL отсутствует "
                    "текст цели."
                ),
            }

        goal_value = value.strip()

        existing = (
            self.agent.goal_manager.get(
                goal_value
            )
            if hasattr(
                self.agent,
                "goal_manager",
            )
            else None
        )

        if existing is not None:
            return {
                "applied": False,
                "reason": (
                    "Такая цель уже существует."
                ),
                "goal_status": existing.status,
            }

        if not hasattr(
            self.agent,
            "goal_manager",
        ):
            return {
                "applied": False,
                "reason": (
                    "GoalManager пока не подключён "
                    "к Agent."
                ),
            }

        goal = (
            self.agent.goal_manager.add_candidate(
                value=goal_value,
                motivation=importance,
                priority=importance,
                confidence=importance,
                source="self",
            )
        )

        return {
            "applied": True,
            "reason": (
                "Создан кандидат собственной цели."
            ),
            "goal": goal.to_dict(),
        }

    def _is_user_owned(
        self,
        item,
        analysis,
    ) -> bool:

        event_type = str(
            analysis.get(
                "type",
                "",
            )
        ).upper()

        if event_type.startswith(
            "USER_"
        ):
            return True

        if item.route == "USER_QUERY":
            return True

        return False

    def _importance(
        self,
        analysis: dict,
    ) -> float:

        try:
            value = float(
                analysis.get(
                    "importance",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            value = 0.0

        return max(
            0.0,
            min(1.0, value),
        )

    def _record(
        self,
        item,
        analysis,
        decision,
    ) -> dict:

        self.memory.remember(
            Event.create(
                content=json.dumps(
                    {
                        "item_id": item.id,
                        "analysis": analysis,
                        "decision": decision,
                    },
                    ensure_ascii=False,
                ),
                event_type=(
                    "COGNITIVE_DECISION"
                ),
                source_type=(
                    "SELF_OBSERVATION"
                ),
                source="cognitive_decision_engine",
                personal_experience=True,
                confidence=(
                    decision["importance"]
                ),
                verified=True,
            )
        )

        return {
            "status": "DECIDED",
            "item_id": item.id,
            "analysis": analysis,
            "decision": decision,
        }
