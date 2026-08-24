import json
import time


class CognitiveProcessor:
    """
    Двухфазная когнитивная обработка.

    Фаза 1:
        analyse_next()
        можно выполнять в background worker.

    Фаза 2:
        apply_analyzed()
        выполняется в главном потоке,
        потому что может менять SQLite-backed state.

    process_next() сохраняется как удобный
    синхронный режим для тестов.
    """

    def __init__(
        self,
        agent,
    ):
        self.agent = agent
        self.queue = agent.cognitive_queue
        self.triage = agent.cognitive_triage
        self.model_orchestrator = (
            agent.model_orchestrator
        )
        self.decision_engine = None

    # =========================================================
    # BACKGROUND PHASE
    # =========================================================

    def analyse_next(self):
        item = self.queue.next()

        if item is None:
            return {
                "status": "EMPTY",
                "item": None,
            }

        try:
            if item.route == "REFLECTION":
                try:
                    snapshot = json.loads(
                        item.content
                    )
                except json.JSONDecodeError:
                    failed = self.queue.fail(
                        item.id
                    )
                    return {
                        "status": "INVALID_REFLECTION_SNAPSHOT",
                        "item": failed,
                    }

                if not isinstance(snapshot, dict):
                    failed = self.queue.fail(
                        item.id
                    )
                    return {
                        "status": "INVALID_REFLECTION_SNAPSHOT",
                        "item": failed,
                    }

                cycle_result = (
                    self.agent.reflection_cycle.run_snapshot(
                        snapshot
                    )
                )

                stored = json.dumps(
                    cycle_result,
                    ensure_ascii=False,
                )

                analyzed = self.queue.save_analysis(
                    item.id,
                    stored,
                )

                return {
                    "status": "ANALYZED_REFLECTION",
                    "item": analyzed,
                    "analysis": cycle_result,
                    "model": "reflection_cycle",
                }

            event_type = self._infer_event_type(
                item
            )

            triage = self.triage.evaluate(
                content=item.content,
                event_type=event_type,
                route=item.route,
                reason=item.reason,
            )

            triage_data = {
                "route": triage.route,
                "reason": triage.reason,
                "expected_seconds": (
                    triage.expected_seconds
                ),
                "expected_value": (
                    triage.expected_value
                ),
                "cost_value_ratio": (
                    triage.cost_value_ratio
                ),
            }

            # -------------------------------------------------
            # DETERMINISTIC
            # -------------------------------------------------

            if triage.route == "DETERMINISTIC":
                analysis = (
                    self._deterministic_analysis(
                        item,
                        event_type,
                    )
                )

                stored = json.dumps(
                    analysis,
                    ensure_ascii=False,
                )

                analyzed = self.queue.save_analysis(
                    item.id,
                    stored,
                )

                return {
                    "status": "ANALYZED_DETERMINISTIC",
                    "item": analyzed,
                    "analysis": analysis,
                    "model": None,
                    "triage": triage_data,
                }

            # -------------------------------------------------
            # QWEN
            # -------------------------------------------------

            started = time.perf_counter()

            result = (
                self.model_orchestrator.execute(
                    task=(
                        "Структурированно проанализируй "
                        "отложенный опыт EddieAI. "
                        "Определи важность события и "
                        "следующее действие."
                    ),
                    context=(
                        f"event_type={event_type}\n"
                        f"route={item.route}\n"
                        f"reason={item.reason}\n"
                        f"attempt={item.attempts}"
                    ),
                    system=(
                        "Ты внутренний когнитивный модуль EddieAI.\n"
                        "Не изменяй self_state напрямую.\n"
                        "Не выдумывай факты.\n"
                        "Пользовательское утверждение не является "
                        "собственным опытом EddieAI.\n\n"
                        "Верни ТОЛЬКО JSON без markdown.\n\n"
                        "Формат:\n"
                        "{\n"
                        '  "importance": 0.0,\n'
                        '  "type": "GENERAL",\n'
                        '  "observation": "string",\n'
                        '  "interpretation": "string",\n'
                        '  "action": "MORE_EVIDENCE",\n'
                        '  "self_update": false\n'
                        "}\n\n"
                        "Допустимые action:\n"
                        "IGNORE\n"
                        "RETAIN\n"
                        "MORE_EVIDENCE\n"
                        "UPDATE_SELF\n"
                        "CREATE_GOAL"
                    ),
                    user=(
                        "Отложенный опыт:\n\n"
                        f"{item.content}\n\n"
                        "Верни только JSON."
                    ),
                    metadata={
                        "high_reasoning": True,
                    },
                    options={
                        "num_predict": 192,
                        "temperature": 0.1,
                    },
                )
            )

            duration = (
                time.perf_counter()
                - started
            )

            self.triage.record_duration(
                "qwen",
                duration,
            )

            raw = (
                result.get("content") or ""
            ).strip()

            if not raw:
                failed = self.queue.fail(
                    item.id
                )

                return {
                    "status": "EMPTY_RESULT",
                    "item": failed,
                    "model": result.get("model"),
                    "duration": duration,
                    "triage": triage_data,
                }

            try:
                analysis = json.loads(raw)

            except json.JSONDecodeError:
                failed = self.queue.fail(
                    item.id
                )

                return {
                    "status": "INVALID_JSON",
                    "item": failed,
                    "model": result.get("model"),
                    "duration": duration,
                    "raw": raw,
                    "triage": triage_data,
                }

            required = {
                "importance",
                "type",
                "observation",
                "interpretation",
                "action",
                "self_update",
            }

            if not required.issubset(
                analysis.keys()
            ):
                failed = self.queue.fail(
                    item.id
                )

                return {
                    "status": "INVALID_SCHEMA",
                    "item": failed,
                    "model": result.get("model"),
                    "duration": duration,
                    "analysis": analysis,
                    "triage": triage_data,
                }

            try:
                importance = float(
                    analysis["importance"]
                )

            except (
                TypeError,
                ValueError,
            ):
                failed = self.queue.fail(
                    item.id
                )

                return {
                    "status": "INVALID_IMPORTANCE",
                    "item": failed,
                    "model": result.get("model"),
                    "duration": duration,
                    "analysis": analysis,
                    "triage": triage_data,
                }

            analysis["importance"] = max(
                0.0,
                min(1.0, importance),
            )

            analysis["self_update"] = bool(
                analysis["self_update"]
            )

            stored = json.dumps(
                analysis,
                ensure_ascii=False,
            )

            analyzed = self.queue.save_analysis(
                item.id,
                stored,
            )

            return {
                "status": "ANALYZED_QWEN",
                "item": analyzed,
                "analysis": analysis,
                "model": result.get("model"),
                "duration": duration,
                "triage": triage_data,
                "task_profile": result.get(
                    "task_profile"
                ),
            }

        except Exception as exc:
            failed = self.queue.fail(
                item.id
            )

            return {
                "status": "FAILED",
                "item": failed,
                "error": str(exc),
            }

    # =========================================================
    # MAIN THREAD PHASE
    # =========================================================

    def apply_analyzed(
        self,
        item_id: str,
    ):
        if self.decision_engine is None:
            return {
                "status": "DECISION_ENGINE_UNAVAILABLE",
                "item_id": item_id,
            }

        item = self.queue.get(
            item_id
        )

        if item is None:
            return {
                "status": "ITEM_NOT_FOUND",
                "item_id": item_id,
            }

        if (
            item.route == "REFLECTION"
            and item.status == "ANALYZED"
        ):
            try:
                cycle_result = json.loads(
                    item.analysis or "{}"
                )
            except json.JSONDecodeError:
                failed = self.queue.fail(
                    item.id
                )
                return {
                    "status": "INVALID_REFLECTION_ANALYSIS",
                    "item": failed,
                }

            applied = (
                self.agent.reflection_scheduler
                .apply_completed_reflection(
                    cycle_result
                )
            )

            completed = self.queue.complete(
                item.id,
                analysis=json.dumps(
                    {
                        "cycle": cycle_result,
                        "application": applied,
                    },
                    ensure_ascii=False,
                ),
            )

            return {
                "status": "REFLECTION_APPLIED",
                "item": completed,
                "decision": applied,
                "analysis": cycle_result,
            }

        if item.status != "ANALYZED":
            return {
                "status": "NOT_ANALYZED",
                "item_id": item_id,
                "current_status": item.status,
            }

        try:
            analysis = json.loads(
                item.analysis or "{}"
            )

        except json.JSONDecodeError:
            failed = self.queue.fail(
                item.id
            )

            return {
                "status": "INVALID_STORED_ANALYSIS",
                "item": failed,
            }

        decision = (
            self.decision_engine.decide(
                item=item,
                analysis=analysis,
            )
        )

        analysis_with_decision = {
            **analysis,
            "decision_result": decision,
        }

        stored = json.dumps(
            analysis_with_decision,
            ensure_ascii=False,
        )

        completed = self.queue.complete(
            item.id,
            analysis=stored,
        )

        return {
            "status": "APPLIED",
            "item": completed,
            "decision": decision,
            "analysis": analysis,
        }

    def apply_all_analyzed(self):
        results = []

        for item in list(
            self.queue.analyzed()
        ):
            results.append(
                self.apply_analyzed(
                    item.id
                )
            )

        return results

    # =========================================================
    # SYNCHRONOUS COMPATIBILITY
    # =========================================================

    def process_next(self):
        result = self.analyse_next()

        if result["status"] == "EMPTY":
            return result

        if result["status"] in {
            "EMPTY_RESULT",
            "INVALID_JSON",
            "INVALID_SCHEMA",
            "INVALID_IMPORTANCE",
            "FAILED",
        }:
            return result

        item = result["item"]

        applied = self.apply_analyzed(
            item.id
        )

        result["decision"] = (
            applied.get("decision")
        )

        result["status"] = (
            "PROCESSED"
            if applied.get("status")
            == "APPLIED"
            else applied.get(
                "status",
                result["status"],
            )
        )

        return result

    # =========================================================
    # HELPERS
    # =========================================================

    def _infer_event_type(
        self,
        item,
    ) -> str:

        content = item.content.lower()

        if (
            "мне нравится" in content
            or "мне интересно" in content
            or "я люблю" in content
            or "я предпочитаю" in content
        ):
            return "USER_INTEREST"

        if (
            "противореч" in content
            or "конфликт" in content
        ):
            return "SELF_CONTRADICTION"

        return "GENERAL"

    def _deterministic_analysis(
        self,
        item,
        event_type: str,
    ) -> dict:

        if event_type == "USER_INTEREST":
            return {
                "importance": 0.50,
                "type": "USER_INTEREST",
                "observation": (
                    "Пользователь выразил "
                    "интерес к теме."
                ),
                "interpretation": (
                    "Интерес потенциально значим, "
                    "но одного наблюдения недостаточно "
                    "для вывода об устойчивом паттерне."
                ),
                "action": "MORE_EVIDENCE",
                "self_update": False,
            }

        if event_type == "SELF_CONTRADICTION":
            return {
                "importance": 0.75,
                "type": "SELF_CONTRADICTION",
                "observation": item.content,
                "interpretation": (
                    "Обнаружен потенциальный "
                    "конфликт, требующий "
                    "дальнейшего анализа."
                ),
                "action": "RETAIN",
                "self_update": False,
            }

        return {
            "importance": 0.30,
            "type": event_type,
            "observation": item.content,
            "interpretation": (
                "Событие сохранено для "
                "дальнейшего наблюдения."
            ),
            "action": "RETAIN",
            "self_update": False,
        }
