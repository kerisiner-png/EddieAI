# Аудит ALL — батч 4

Файлы: autonomy_runtime_factory.py, autonomy_scheduler.py, claim_adapter.py
Модель: deepseek-v4-flash

Мы провели аудит двух файлов: core/autonomy_runtime_factory.py и core/autonomy_scheduler.py, а также core/claim_adapter.py. Начнем с первого.

Файл: core/autonomy_runtime_factory.py (479 строк)

Проблемы:

1. Строка 1-3: импорты из core.agent_loop, core.autonomy_arbitrator и т.д. — все импорты корректны, но есть потенциальная проблема циклических импортов? Не видно, но не проверяем.

2. Строка 10-11: импорт из identity.action_planner и т.д. — все ок.

3. Строка 12-13: импорт из identity.adaptive_plan_controller и adaptive_planner — ок.

4. Строка 14-15: импорт из identity.behavior_pattern_detector — ок.

5. Строка 16-17: импорт из identity.evidence_consolidator — ок.

6. Строка 18-19: импорт из identity.filesystem_executor — ок.

7. Строка 20-21: импорт из identity.goal_generator, goal_manager, goal_plan_generator, goal_planner, goal_review — ок.

8. Строка 22-23: импорт из identity.llm_executor — ок.

9. Строка 24-25: импорт из identity.motivation — ок.

10. Строка 26-27: импорт из identity.reflection_engine — ок.

11. Строка 28-29: импорт из identity.self_experience — ок.

12. Строка 30-31: импорт из identity.task_controller — ок.

13. Строка 32-33: импорт из identity.tool_registry, tool_runner — ок.

14. Строка 34-35: импорт из identity.web_executor — ок.

15. Строка 36-37: импорт из memory.external_knowledge — ок.

16. Строка 38-39: импорт из memory.research_context — ок.

17. Строка 40-41: импорт из memory.self_interpretation — ок.

18. Строка 42-43: импорт из memory.source_evaluator — ок.

19. Строка 44-45: импорт из memory.tool_experience — ок.

20. Строка 47: class AutonomyRuntimeFactory — ок.

21. Строка 48-55: __init__ с параметрами. filesystem_root по умолчанию r"C:\EddieAI" — это Windows-путь, но код может работать на других ОС. Лучше использовать pathlib или os.path.expanduser. Но это не критично, если проект только для Windows.

22. Строка 57-60: сохранение параметров.

23. Строка 62: def build(self): — метод.

24. Строка 64-66: создание GoalPlanner с self.agent.self_state. Предполагается, что у agent есть self_state. Ок.

25. Строка 68-70: GoalManager с self.agent.self_state и goal_planner.

26. Строка 72-73: GoalReview(goal_manager).

27. Строка 75-77: MotivationEngine(self.agent.self_state, self.agent.personality_lifecycle). Предполагается, что personality_lifecycle существует.

28. Строка 79-83: GoalPlanGenerator(goal_planner, model_orchestrator=self.agent.model_orchestrator). Ок.

29. Строка 85-91: GoalGenerator(motivation_engine=motivation, goal_manager=goal_manager, goal_review=goal_review, goal_plan_generator=goal_plan_generator). Ок.

30. Строка 93-97: AdaptivePlanner(model_orchestrator=self.agent.model_orchestrator). Ок.

31. Строка 99-101: AdaptivePlanController(goal_planner). Ок.

32. Строка 103-105: ExternalKnowledgeRecorder(self.agent.memory). Ок.

33. Строка 107-112: SelfInterpretation(self.agent.memory, model_orchestrator=self.agent.model_orchestrator). Ок.

34. Строка 114-115: ResearchContext(self.agent.memory). Ок.

35. Строка 117-118: SourceEvaluator(acceptance_threshold=0.45). Ок.

36. Строка 120-121: комментарий "TOOLS" и пусто. Ок.

37. Строка 123-124: model_orchestrator = self.agent.model_orchestrator. Ок.

38. Строка 126: registry = ToolRegistry().

39. Строка 128-133: регистрация "llm" с LLMExecutor(model_orchestrator). Ок.

40. Строка 135-140: регистрация "filesystem" с FilesystemExecutor(self.filesystem_root). Ок.

41. Строка 142-147: регистрация "web" с WebExecutor(). Ок.

42. Строка 149-154: регистрация "research" с executor=object(). Это подозрительно: research executor — это просто object(), а не реальный исполнитель. В комментарии сказано, что research маршрутизируется отдельно, и фактический composite execution выполняется внутри ToolRunner. Но регистрация с object() может привести к ошибкам, если кто-то попытается вызвать executor. Лучше было бы создать заглушку с методом execute, который вызывает ToolRunner. Но возможно, это намеренно, и ToolRunner обрабатывает research отдельно. Однако это хрупкое место: если ToolRunner не обработает research, то вызов упадет. Также object() не имеет метода execute, что может вызвать AttributeError. Это потенциальная проблема.

43. Строка 156-158: self.agent.capabilities = registry.describe(); self.agent.self_consistency.capabilities = self.agent.capabilities. Предполагается, что у agent есть self_consistency. Ок.

44. Строка 160-167: создание ToolRunner с registry, filesystem_root, external_recorder, self_interpreter, source_evaluator. Ок.

45. Строка 169-171: ToolExperienceRecorder(self.agent.memory). Ок.

46. Строка 173-176: SelfExperienceConsolidator(self.agent.memory, self.agent.evidence). Ок.

47. Строка 178-181: ActionPreferenceDetector(self.agent.memory, self.agent.evidence). Ок.

48. Строка 183-186: HabitPatternDetector(self.agent.memory, self.agent.evidence). Ок.

49. Строка 188-191: BeliefPatternDetector(self.agent.memory, self.agent.evidence). Ок.

50. Строка 193-195: TaskController(goal_manager, goal_planner). Ок.

51. Строка 197-203: ReflectionEngine(self.agent.memory, self.agent.evidence, self.agent.personality_lifecycle, model_orchestrator=self.agent.model_orchestrator). Ок.

52. Строка 205-207: EvidenceConsolidator(self.agent.evidence). Ок.

53. Строка 209-211: BehaviorPatternDetector(self.agent.memory, self.agent.evidence). Ок.

54. Строка 213-249: создание AgentLoop с множеством параметров. Здесь есть параметр max_actions=1. Это может быть ограничением, но возможно намеренно.

55. Строка 251: runtime_agent_loop = agent_loop — лишнее присваивание, но не ошибка.

56. Строка 253-260: AutonomyOrchestrator(goal_manager, goal_generator, goal_plan_generator, agent_loop, agent=self.agent, affective_behavior_policy=self.agent.affective_behavior_policy). Ок.

57. Строка 262-270: AutonomyScheduler(autonomous_cycle=orchestrator, interval_seconds=self.scheduler_interval_seconds, max_ticks_per_window=self.scheduler_max_ticks_per_window, window_seconds=3600). Ок.

58. Строка 272-276: AutonomousRuntime(scheduler=scheduler, memory=self.agent.memory, orchestrator=orchestrator). Ок.

59. Строка 278: self.agent.autonomous_runtime = runtime.

60. Строка 280-281: runtime.behavior_pattern_detector = behavior_pattern_detector; runtime.evidence_consolidator = evidence_consolidator.

61. Строка 283-284: runtime.goal_manager = goal_manager; self.agent.goal_manager = goal_manager.

62. Строка 286-289: self.agent.autonomy_arbitrator = AutonomyArbitrator(goal_manager, agent=self.agent). Ок.

63. Строка 291-292: runtime.autonomy_arbitrator = self.agent.autonomy_arbitrator.

64. Строка 294-306: присваивание множества атрибутов runtime. Ок.

65. Строка 308: self.agent.cognition_worker.start() — запуск фонового процесса. Это может быть опасно, если метод вызывается несколько раз (повторный запуск потока). Нет проверки, запущен ли уже. Это потенциальная проблема: если build() вызывается повторно, поток запустится снова, что может привести к ошибке или дублированию. Нужно проверить, есть ли защита.

66. Строка 309: return runtime.

Проблемы:

- Регистрация research с object() — HIGH.
- Запуск cognition_worker.start() без проверки — MEDIUM.
- Жестко заданный window_seconds=3600 в scheduler — возможно, стоит параметризовать.
- Использование r"C:\EddieAI" — LOW (переносимость).
- Многострочные выражения с скобками — стиль ок.

Файл: core/autonomy_scheduler.py (179 строк)

Проблемы:

1. Строка 1-2: импорты dataclass, datetime, timezone, timedelta — ок.

2. Строка 4-7: dataclass ScheduleDecision с полями should_tick, reason, next_allowed_at. Ок.

3. Строка 9-12: class AutonomyScheduler — ок.

4. Строка 14-19: docstring — ок.

5. Строка 21-31: __init__ с параметрами. interval_seconds, max_ticks_per_window, window_seconds. Приводит к int, ограничивает минимум 1. window_seconds = max(self.interval_seconds, int(window_seconds)) — ок.

6. Строка 33-34: self.enabled = True; self.last_tick_at = None; self.tick_history = [].

7. Строка 36-56: метод evaluate(). Проверяет enabled, очищает историю, проверяет лимит тиков за окно, проверяет интервал. Возвращает ScheduleDecision.

8. Строка 58-76: метод tick(). Вызывает evaluate(), если не should_tick, возвращает SCHEDULED_IDLE. Иначе вызывает autonomous_cycle.tick(), записывает время, добавляет в историю, возвращает TICK_EXECUTED.

9. Строка 78-81: enable/disable/reset — ок.

10. Строка 83-89: _cleanup_history(now) — удаляет записи старше window_seconds.

11. Строка 91-98: _next_window_time() — возвращает время, когда станет доступен следующий тик (самый старый + window_seconds). Ок.

Проблемы:

- В evaluate() при проверке лимита тиков за окно: если len(tick_history) >= max_ticks_per_window, то возвращается отказ. Но если история не очищена, то после истечения окна, _cleanup_history удалит старые записи, и лимит перестанет действовать. Это правильно.

- В tick() после выполнения autonomous_cycle.tick() записывается время. Но если autonomous_cycle.tick() бросит исключение, то last_tick_at не обновится, и история не пополнится. Это может привести к повторным попыткам. Возможно, стоит обернуть в try/except.

- В evaluate() при проверке интервала: если last_tick_at не None, вычисляется elapsed. Если elapsed < interval_seconds, возвращается отказ с next_allowed_at. Но если last_tick_at в будущем (например, из-за сдвига времени), то elapsed будет отрицательным, и условие сработает, вернет отказ. Это нормально.

- В _next_window_time() используется min(tick_history) — это самый старый тик. Но если история не пуста
