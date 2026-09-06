from identity.action_executor import ActionExecutor
from identity.action_router import ActionRouter
from identity.tool_policy import ToolExecutionPolicy


class ToolRunner:
    def __init__(
        self,
        registry,
        filesystem_root=r"C:\EddieAI",
        external_recorder=None,
        self_interpreter=None,
        source_evaluator=None,
        model_orchestrator=None,
    ):
        self.registry = registry
        self.executor = ActionExecutor()

        self.router = ActionRouter(
            registry
        )

        self.policy = ToolExecutionPolicy(
            filesystem_root
        )

        self.model_orchestrator = (
            model_orchestrator
        )

        self.external_recorder = (
            external_recorder
        )

        self.self_interpreter = (
            self_interpreter
        )

        self.source_evaluator = (
            source_evaluator
        )

    def run(
        self,
        action,
    ):
        validation = self.executor.validate(
            action
        )

        if not validation["valid"]:
            action.status = "REJECTED"

            return {
                "status": "REJECTED",
                "stage": "validation",
                "action": action.to_dict(),
                "errors": validation["errors"],
            }

        route = self.router.route(
            action
        )

        if not route.allowed:
            action.status = "REJECTED"

            return {
                "status": "REJECTED",
                "stage": "routing",
                "tool": route.tool,
                "reason": route.reason,
                "action": action.to_dict(),
            }

        policy = self.policy.evaluate(
            action
        )

        if not policy["allowed"]:
            action.status = "REJECTED"

            return {
                "status": "REJECTED",
                "stage": "policy",
                "tool": route.tool,
                "reason": policy["reason"],
                "action": action.to_dict(),
            }

        if action.dry_run:
            action.status = "SIMULATED"

            return {
                "status": "SIMULATED",
                "stage": "dry_run",
                "tool": route.tool,
                "action": action.to_dict(),
                "reason": policy["reason"],
            }

        try:
            if action.action_type == "RESEARCH":
                result = self._execute_research(
                    action
                )
            else:
                result = self._execute_real(
                    route.tool,
                    action,
                )

            action.status = (
                "COMPLETED"
                if result.get("status") == "OK"
                else "FAILED"
            )

            return {
                "status": result.get(
                    "status",
                    "FAILED",
                ),
                "stage": "execution",
                "tool": route.tool,
                "action": action.to_dict(),
                "result": result,
            }

        except Exception as exc:
            action.status = "FAILED"

            return {
                "status": "FAILED",
                "stage": "execution",
                "tool": route.tool,
                "action": action.to_dict(),
                "error": str(exc),
            }

    def _execute_research(
        self,
        action,
    ):
        if self.external_recorder is None:
            return {
                "status": "FAILED",
                "error": (
                    "ExternalKnowledgeRecorder "
                    "не подключён."
                ),
            }

        if self.self_interpreter is None:
            return {
                "status": "FAILED",
                "error": (
                    "SelfInterpretation "
                    "не подключён."
                ),
            }

        if self.source_evaluator is None:
            return {
                "status": "FAILED",
                "error": (
                    "SourceEvaluator "
                    "не подключён."
                ),
            }

        query = action.parameters.get(
            "query",
            action.target,
        )

        limit = action.parameters.get(
            "limit",
            5,
        )

        # -----------------------------------------
        # WEB SEARCH
        # -----------------------------------------

        web_result = self._execute_web_search(
            query=query,
            limit=limit,
        )

        if web_result.get("status") != "OK":
            return web_result

        raw_results = web_result.get(
            "results",
            [],
        )

        # -----------------------------------------
        # SOURCE EVALUATION
        # -----------------------------------------

        evaluated = (
            self.source_evaluator.evaluate(
                raw_results,
                query,
            )
        )

        accepted = [
            {
                "url": item.url,
                "title": item.title,
            }
            for item in evaluated
            if item.accepted
        ]

        rejected = [
            {
                "url": item.url,
                "title": item.title,
                "score": item.score,
                "reasons": item.reasons,
            }
            for item in evaluated
            if not item.accepted
        ]

        if not accepted:
            return {
                "status": "OK",
                "no_accepted_sources": True,
                "honest_note": (
                    "Исследование проведено, но "
                    "проверяемых источников по "
                    f"запросу «{query}» не "
                    "нашлось: все кандидаты не "
                    "прошли оценку качества. "
                    "Результаты не записаны как "
                    "знание."
                ),
                "query": query,
                "results": raw_results,
                "evaluated_sources": [
                    self._evaluation_dict(
                        item
                    )
                    for item in evaluated
                ],
                "rejected": rejected,
                "external_records": [],
                "interpretation": None,
            }

        filtered_web_result = {
            "status": "OK",
            "query": query,
            "results": accepted,
            "count": len(accepted),
        }

        # -----------------------------------------
        # PAGE CONTENT (топ-3 источника)
        # -----------------------------------------

        try:
            web_tool = self.registry.require(
                "web"
            )

            web_executor = (
                web_tool.executor
            )
        except Exception:
            web_executor = None

        if web_executor is not None:
            for item in accepted[:3]:
                page = (
                    web_executor.read_page(
                        item.get("url", "")
                    )
                )

                if (
                    page.get("status") == "OK"
                    and len(
                        page.get("text", "")
                    )
                    >= 150
                ):
                    item["text"] = page[
                        "text"
                    ][:2000]

        # -----------------------------------------
        # EXTERNAL KNOWLEDGE
        # -----------------------------------------

        external_records = (
            self.external_recorder.record(
                filtered_web_result
            )
        )

        # -----------------------------------------
        # SELF INTERPRETATION
        # -----------------------------------------

        interpretation = (
            self.self_interpreter.interpret(
                query=query,
                limit=len(accepted),
            )
        )

        return {
            "status": "OK",
            "query": query,
            "results": accepted,
            "raw_results_count": len(
                raw_results
            ),
            "accepted_count": len(
                accepted
            ),
            "rejected_count": len(
                rejected
            ),
            "evaluated_sources": [
                self._evaluation_dict(
                    item
                )
                for item in evaluated
            ],
            "rejected": rejected,
            "external_records": [
                {
                    "title": record.title,
                    "url": record.url,
                }
                for record in external_records
            ],
            "interpretation": interpretation,
        }

    def _evaluation_dict(
        self,
        item,
    ):
        return {
            "title": item.title,
            "url": item.url,
            "score": item.score,
            "accepted": item.accepted,
            "source_class": item.source_class,
            "reasons": item.reasons,
        }

    def _execute_web_search(
        self,
        query: str,
        limit: int = 5,
):
        tool = self.registry.require(
            "web"
        )

        if getattr(self, "curiosity", None) is not None:
            try:
                self.curiosity.track_action("web")
            except Exception:
                pass

        return tool.executor.search(
            query=query,
            limit=limit,
        )

    def _execute_real(
        self,
        tool_name: str,
        action,
    ):
        tool = self.registry.require(
            tool_name
        )

        if tool_name == "filesystem":
            return self._execute_filesystem(
                tool,
                action,
            )

        if tool_name == "llm":
            return self._execute_llm(
                tool,
                action,
            )

        if tool_name == "web":
            return self._execute_web(
                tool,
                action,
            )

        if tool_name == "research":
            return self._execute_research(
                action
            )

        if tool_name == "powershell":
            return self._execute_powershell(
                tool,
                action,
            )

        if tool_name == "programs":
            return self._execute_programs(
                tool,
                action,
            )

        if tool_name == "install":
            return self._execute_install(
                tool,
                action,
            )

        if tool_name == "screen_control":
            return self._execute_screen_control(
                action,
            )

        if tool_name == "perceive":
            return self._execute_perceive(
                action,
            )

        return {
            "status": "UNAVAILABLE",
            "error": (
                f"Real executor for "
                f"'{tool_name}' is not implemented."
            ),
        }

    def _execute_filesystem(
        self,
        tool,
        action,
    ):
        if action.action_type == "READ_FILE":
            return tool.executor.read(
                path=action.parameters["path"],
                max_bytes=action.parameters.get(
                    "max_bytes",
                    200_000,
                ),
            )

        if action.action_type == "WRITE_FILE":
            return tool.executor.write(
                path=action.parameters["path"],
                content=action.parameters[
                    "content"
                ],
            )

        if action.action_type == "LIST_DIR":
            return tool.executor.list(
                path=action.parameters["path"],
            )

        if action.action_type == "SEARCH_FILES":
            return tool.executor.search(
                pattern=action.parameters["pattern"],
                limit=action.parameters.get(
                    "limit",
                    100,
                ),
            )

        return {
            "status": "UNSUPPORTED",
            "error": (
                "Filesystem executor does not "
                f"support {action.action_type}."
            ),
        }

    def _execute_llm(
        self,
        tool,
        action,
    ):
        if action.action_type == "THINK":
            return tool.executor.think(
                target=action.target,
                context=action.parameters.get(
                    "context",
                    "",
                ),
            )

        if action.action_type == "RESEARCH":
            return tool.executor.research(
                target=action.target,
                context=action.parameters.get(
                    "context",
                    "",
                ),
            )

        if action.action_type == "WRITE":
            return tool.executor.write(
                target=action.target,
                context=action.parameters.get(
                    "context",
                    "",
                ),
            )

        return {
            "status": "UNSUPPORTED",
            "error": (
                "LLM executor does not "
                f"support {action.action_type}."
            ),
        }

    def _execute_web(
        self,
        tool,
        action,
    ):
        if action.action_type == "WEB_SEARCH":
            if getattr(
                self, "curiosity", None
            ) is not None:
                try:
                    self.curiosity.track_action(
                        "web"
                    )
                except Exception:
                    pass
            return tool.executor.search(
                query=action.parameters[
                    "query"
                ],
                limit=action.parameters.get(
                    "limit",
                    5,
                ),
            )

        return {
            "status": "UNSUPPORTED",
            "error": (
                "Web executor does not "
                f"support {action.action_type}."
            ),
        }

    def _execute_powershell(
        self,
        tool,
        action,
    ):
        command = action.parameters.get(
            "command"
        )

        cwd = action.parameters.get(
            "cwd"
        )

        result = tool.executor.execute(
            command,
            cwd=cwd,
        )

        return {
            "status": result["status"],
            "output": result["stdout"],
            "error": result["stderr"],
            "exit_code": result["exit_code"],
            "command": result["command"],
        }

    def _execute_programs(
        self,
        tool,
        action,
    ):
        command = action.parameters.get(
            "command"
        )

        result = tool.executor.launch(command)

        return {
            "status": result["status"],
            "reason": result.get("reason", ""),
            "command": result.get("command", command),
        }

    def _execute_install(
        self,
        tool,
        action,
    ):
        package = action.parameters.get(
            "package"
        )

        manager = action.parameters.get(
            "manager"
        )

        result = tool.executor.install(
            package,
            manager,
        )

        return {
            "status": result["status"],
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "reason": result.get("reason", ""),
        }

    def _execute_screen_control(
        self,
        action,
    ):
        try:
            from identity.screen_controller import (
                ScreenController,
            )
        except ImportError:
            return {
                "status": "FAILED",
                "error": (
                    "ScreenController "
                    "не импортируется."
                ),
            }

        sc = ScreenController()
        params = action.parameters
        op = action.target

        if op == "click":
            sc.click(
                params.get("x", 0),
                params.get("y", 0),
            )
        elif op == "right_click":
            sc.right_click(
                params.get("x", 0),
                params.get("y", 0),
            )
        elif op == "double_click":
            sc.double_click(
                params.get("x", 0),
                params.get("y", 0),
            )
        elif op == "type_text":
            sc.type_text(
                params.get("text", ""),
            )
        elif op == "key":
            sc.key(
                params.get("hotkey", ""),
            )
        elif op == "scroll":
            sc.scroll(
                direction=params.get(
                    "direction", "down"
                ),
                amount=params.get("amount", 3),
            )
        elif op == "get_active_window":
            return {
                "status": "OK",
                "window": sc.get_active_window(),
            }
        elif op == "list_windows":
            return {
                "status": "OK",
                "windows": sc.list_windows(),
            }
        elif op == "focus_window":
            ok = sc.focus_window(
                params.get("title", ""),
            )
            return {
                "status": "OK" if ok else "FAILED",
            }
        else:
            return {
                "status": "UNSUPPORTED",
                "error": (
                    f"ScreenControl не поддерживает "
                    f"операцию '{op}'."
                ),
            }

        return {"status": "OK"}

    def _execute_perceive(
        self,
        action,
    ):
        source = action.parameters.get(
            "source", "webcam"
        )
        try:
            from identity.screen_perceiver import (
                ScreenPerceiver,
            )

            sp = ScreenPerceiver(
                model_orchestrator=(
                    self.model_orchestrator
                ),
            )
            if source == "webcam":
                desc = sp.webcam_describe()
            elif source == "screen":
                current = sp.capture_now()
                desc = current.get(
                    "description", ""
                )
            else:
                return {
                    "status": "FAILED",
                    "error": (
                        f"Неизвестный источник "
                        f"восприятия: {source}"
                    ),
                }
            if not desc or not desc.strip():
                return {
                    "status": "EMPTY",
                    "description": "",
                }
            return {
                "status": "OK",
                "description": desc,
                "source": source,
            }
        except Exception as exc:
            return {
                "status": "FAILED",
                "error": str(exc),
            }
