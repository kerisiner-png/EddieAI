# Аудит EddieAI (ночь 23.08)

Аудитор: читающий агент, ночной отряд №7, попытка 2. Мандат: AUDIT_TASK_EDDIEAI.md.
Метод: только чтение (read/grep/glob) + безопасные python-подсчёты по текстам;
data/*.db не открывались; self_state.json/user_state.json прочитаны только до уровня
ключей верхнего уровня. Все номера строк проверены чтением. API ollama-python сверены
через Context7 (/ollama/ollama-python): chat(keep_alive, think, format) — параметры
валидны; таймаут по умолчанию у модульного клиента — бесконечное ожидание.

---

## Реестр находок

### HIGH

1. **[HIGH] core/prompts.py:228-244, 284-416** -> системный промпт-персона
   `build_system_prompt` поражён двойным перекодированием («Ð¢Ñ‹ â€” EddieAI…»),
   78 строк из 420 файла -> если функцию вернуть в строй, LLM будет получать мусор
   вместо личности; уже сейчас файл нарушает правило кодировок проекта ->
   восстановить русские строки из git-истории (коммит 5f28a25 или ранее), затем
   решить, подключать ли функцию обратно (см. находку MEDIUM №14).

2. **[HIGH] core/agent.py:950-967** -> живой путь USER_QUERY: метод
   `build_system_prompt` возвращает блок «ТЕКУЩЕЕ СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ…»
   полностью в mojibake -> при каждом вопросе обо мне LLM получает перекодированный
   system-промпт; прямой вклад в «мимо-ответы» голоса -> заменить литералы
   на корректный русский (минимальный дифф, 8 строк).

3. **[HIGH] core/agent.py:1623-1650** (`_store_user_changes`) -> в knowledge и
   events (USER_FACT) пишутся факты о пользователе с mojibake-обёрткой
   («ÐŸÐ¾Ð»ÑŒÐ·Ð¾Ð²Ð°Ñ‚ÐµÐ»ÑŒ ÑÐ¾Ð¾Ð±Ñ‰Ð¸Ð»…») -> порча продакшн-данных личности при
   каждом сообщении с фактами; мусор потом всплывает в контекстах памяти ->
   починить строки; существующие записи БД — отдельное решение совета (бэкап +
   легитимный конвейер очистки), самовольно БД не трогать.

4. **[HIGH] core/agent.py:4987-4990** -> фолбэк-ответ пользователю после
   неуспешного ремонта identity guard — «Пока я не выбрал себе имя» хранится
   в mojibake -> пользователь видит «ÐŸÐ¾ÐºÐ° Ñ Ð½Ðµ Ð²Ñ‹Ð±Ñ€Ð°Ð»…» своими глазами ->
   исправить литерал.

5. **[HIGH] core/agent.py:4923-4926, 5007-5011, 5299-5303** -> содержимое
   событий PERSPECTIVE_CONTRADICTION, SELF_CONTRADICTION, PERSONALITY_PROMOTION
   формируется из mojibake-литералов и уходит в memory.db и personality_history ->
   журнал развития личности загрязнён; трассировка proposal→decision→promotion
   читается как мусор -> исправить литералы; исторические строки БД — решением совета.

6. **[HIGH] identity/self_reflection.py:374-384** -> список `user_markers`
   ownership-guard’а превращён в «????», «??? » — совпадения с реальной речью
   невозможны -> защита «факты пользователя не становятся фактами агента»
   ФУНКЦИОНАЛЬНО ОТКЛЮЧЕНА: само-знание может поглощать утверждения пользователя
   -> восстановить маркеры («у меня», «меня зовут» и т.п.) по git-истории; это
   починка контура самосогласованности, а не косметика.

7. **[HIGH] identity/self_state.py:77-90** -> запись self_state.json неатомарна
   (открыл файл → перезаписал), без ротации бэкапов; каждый `set()` переписывает
   весь файл (сейчас 57 829 байт) -> сбой питания/Ctrl+C в момент записи =
   потерянный/битый self_state (личность); риск растёт с частотой set()
   (self_conclusion_store/state, affective_state, goal_manager — суммарно ~20
   точек записи) -> писать во временный файл + os.replace; периодический бэкап.

8. **[HIGH] core/model_orchestrator.py:506-522** -> `chat()` вызывается без
   таймаута; по Context7 дефолт модульного клиента ollama-python — бесконечное
   ожидание -> зависший Ollama (например, под свопом на 8 ГБ RAM) навсегда
   замораживает respond(), а вместе с ним world-tick симуляции (process_eddie_event
   синхронен) -> передавать клиент с явным timeout (ollama.Client(timeout=…)) или
   обкладывать watchdog’ем.

9. **[HIGH] Потокобезопасность памяти: 20+ мест дергают
   `memory.connection.execute` напрямую, минуя RLock Memory** ->
   memory/evidence.py:39,54,60,86,120,197; identity/promotion.py:54;
   memory/manager.py:86; identity/action_selector.py:208;
   identity/action_preference_detector.py:46,215; identity/belief_pattern_detector.py:51,168;
   identity/goal_affective_memory.py:48,102,137; identity/behavior_pattern_detector.py:43;
   identity/habit_pattern_detector.py:50; memory/personality_history →
   identity/personality_history.py:31,73,91; memory/retrieval.py:16,27;
   memory/research_context.py:57; memory/self_interpretation.py:215;
   identity/self_consistency.py:553 -> при работающем CognitionWorker
   (старт: core/autonomy_runtime_factory.py:446; цикл: cognition_worker.py:113-135)
   один sqlite3-коннект используется из двух потоков без блокировки: вероятны
   «cannot start a transaction within a transaction», потеря коммитов, редкие
   падения под нагрузкой ночного прогона -> либо все обращения через
   @_synchronized-методы Memory, либо отдельные коннекты на поток.

10. **[HIGH] simulation_framework/persistence/memory_sandbox.py:41-56** ->
    `_reset_experimental_memory` делает DELETE FROM «memories», но такой таблицы
    в текущей схеме нет (все CREATE TABLE проверены: events, self_proposals,
    evidence, knowledge, personality_history, evidence_events,
    goal_affective_events; ни один код обоих репозиториев «memories» не создаёт)
    -> песочница, вероятно, выживает только за счёт legacy-таблицы в продакшн
    memory.db [ВЕРОЯТНО]; на свежей/чистой БД создание песочницы упадёт на старте
    каждого прогона -> убрать несуществующие имена из списка или делать
    удаление только фактически существующих таблиц (sqlite_master).

### MEDIUM

11. **[MEDIUM] data/cognitive_queue.json — 3 048 593 байта, рост не ограничен**
    -> полный rewrite файла на каждое сообщение (core/cognitive_queue.py:65-84:
    _save сериализует всё), плюс каждое 8-е сообщение добавляет REFLECTION-
    снапшот всего self_state (identity/reflection_scheduler.py:24,30-45,80-93;
    significant=True всегда — core/agent.py:5142-5144) -> тормоза диска на каждом
    шаге, файл в продакшн-данных содержит 702 группы «???» и 192 mojibake-символа
    (мусор из reason/content кода) -> ротация DONE-записей, снапшоты рефлексии
    не дублировать в JSON-очередь бессрочно; чистка существующего файла — решением
    совета.

12. **[MEDIUM] Схема SQLite без индексов** -> memory/database.py:58-128: нет
    индексов events(event_type), evidence_events(category,value),
    personality_history(field,value); EvidenceEngine.get() сканирует
    evidence_events целиком на каждый вызов, а all_records() даёт N+1 запрос
    (memory/evidence.py:114-129,196-211) -> сейчас база маленькая (memory.db
    794 624 байт), но retrieval деградирует квадратично по мере роста
    evidence_events -> добавить индексы одним миграционным шагом.

13. **[MEDIUM] Неограниченный рост таблиц** -> events/evidence_events/
    personality_history — append-only; DELETE встречается только в тестовых
    скриптах (core_regression_test.py:124, super_system_stress_test.py:175,1632);
    механизма ротации/архива нет -> определить политику хранения (например,
    архив CONVERSATION старше N дней) — проектом, не аудитором.

14. **[MEDIUM] Персона-промпт GENERAL_QUERY отсутствует, его заменяет контекст
    памяти** -> core/agent.py:969-979: else-ветка build_system_prompt возвращает
    memory_manager.build_context(limit=4) КАК system prompt; настоящий
    persona-промпт (core.prompts.build_system_prompt) импортирован
    (core/agent.py:30), но не вызывается ни разу в репозитории -> основной
    маршрут диалога идёт без правил персоны в system (частично объясняет
    диагноз голоса T0-T2: 20% детерминистики) -> после починки кодировок
    (находка №1) решить советом: включать ли persona-промпт в deep-путь.

15. **[MEDIUM] Двойной роутинг и повторный detect_language в respond()** ->
    _route_message: core/agent.py:3672 и 4463; detect_language: 3676 и 4471 ->
    лишняя работа; при появлении состояния в ContextRouter возможен конфликт
    маршрутов gate_route vs route внутри одного запроса -> использовать
    уже вычисленный gate_route.

16. **[MEDIUM] CognitionWorker умирает навсегда** -> core/cognition_worker.py:127-131:
    неперехваченное исключение вне analyze-try → state="ERROR", return; рестарта
    нет -> фоновая когниция молча останавливается до конца процесса (очередь копится
    PENDING) -> перезапуск воркера при следующем event_happened/wake или retry-цикл.

17. **[MEDIUM] Прогрев держит обе модели в RAM постоянно** ->
    core/model_orchestrator.py:348-375: warm_up_models грузит phi4-mini И qwen3.5:4b
    с keep_alive=-1; Agent() вызывает прогрев всегда (core/agent.py:92-94), мост
    создаёт Agent на каждый прогон (bridge.py:40-51) -> ~3+ ГБ резидентно на машине
    8 ГБ ещё до старта мира; совместно с дашбордом — риск свопа и деградации
    latency -> прогревать только нужную модель / keep_alive по профилю.

18. **[MEDIUM] Fallback только на phi4-mini** -> core/model_orchestrator.py:553-564:
    если упала сама phi4-mini (или её нет), fallback=None → raise наружу ->
    исключение пролетает respond() (он без try/except) до вызывающего -> второй
    fallback на qwen или осмысленная деградация (шаблонный ответ + событие в память).

19. **[MEDIUM] Хрупкий текстовый контракт моста** -> агент парсит наблюдение
    разбором строк: split("Обстановка"), split("Событие") + поиск JSON в хвосте
    (core/agent.py:3417-3445); роутер узнаёт канал по трём маркерам-подписям
    (core/context_router.py:84-88), дублирующим формат bridge.build_observation
    (eddie/bridge.py:288-308) -> любое изменение формулировок в bridge молча ломает
    и роутинг, и парсинг события -> зафиксировать контракт константами/версией
    (это уже предложено как задача D «Структурирование контракта моста»).

20. **[MEDIUM] Автономный цикл не запускается боевыми рантаймами** ->
    AutonomyRuntimeFactory строит runtime и стартует только cognition_worker
    (core/autonomy_runtime_factory.py:446); start_background_loop/tick_background
    вызываются только внутри autonomous_runtime.py:145,211,268 — внешних вызовов
    в core/identity нет; main.py и bridge их не дергают -> автономия (цели,
    планирование, consolidation по тику) в консоли и в симуляции спит; каркас жив,
    но не заведён -> осознанно решить: запускать ли loop в main.py/по событию.

21. **[MEDIUM] BOM: 149 файлов проекта имеют UTF-8 BOM** -> включая main.py,
    core/model_orchestrator.py, memory/database.py, identity/identity_seed.py и
    почти всю identity/ -> Python это терпит, но нарушено правило AGENTS.md
    («UTF-8 БЕЗ BOM»), ломаются инструменты, чувствительные к BOM, и git-диффы
    выглядят грязно -> массовая зачистка BOM отдельной одобренной операцией
    (не смешивать с логическими правками).

### LOW

22. **[LOW] Мёртвый код** -> (а) core.prompts.build_system_prompt — импорт без
    единого вызова (core/agent.py:30); (б) memory/manager.py:82-129
    build_conversation_context не вызывается никем (и содержит «???»:101,116,127);
    (в) core/autonomous_cycle.py (AutonomousCycle, InitiativeEngine) не
    используется фабрикой — параметр autonomous_cycle фабрики получает
    AutonomyOrchestrator (autonomy_runtime_factory.py:368-373) -> путаница и
    двойное сопровождение -> пометить/удалить по решению (минимальные диффы).

23. **[LOW] Комментарии-руины «?????»** -> core/agent.py:181-182,
    memory/evidence.py:161-162, core/autonomy_runtime_factory.py:203-204 ->
    смысл комментариев утрачен -> восстановить по git или удалить.

24. **[LOW] reason идентичности в «?????»** -> core/agent_loop.py:296-297 ->
    попадает в proposal.reason → память/историю (известная проблема №1 из
    PROJECT_STATE — подтверждена чтением) -> та же починка, что и №1-№5.

25. **[LOW] Описания инструментов в mojibake** ->
    core/autonomy_runtime_factory.py:165,177,186-188,191-193,198 -> через
    registry.describe() → capabilities → промпты самооценки возможностей
    -> LLM видит мусорные описания собственных инструментов -> восстановить строки.

26. **[LOW] Строки capability-рассуждений в «?????»** ->
    identity/self_consistency.py:484-512 -> ответы/валидация про возможности
    агента содержат мусор -> восстановить.

27. **[LOW] data/ захламлена** -> рядом с продакшн memory.db лежат
    consolidator_test.db, *_stress_test.json, cognitive_queue.*.json,
    self_state.json.before_relationships.backup и ~44 тестовые папки ->
    риск перепутать продакн/тест при ручных операциях -> разделить каталоги
    (давняя проблема №6 PROJECT_STATE — подтверждена listing’ом).

28. **[LOW] ActionObserver канала действий узкий** ->
    eddie/action_observer.py:6-35: 5 локаций × 13 фраз-шаблонов, распознаются
    только перемещения -> богатые ответы мира не порождают действий (известное
    ограничение №5 PROJECT_STATE, подтверждено числами) -> эволюционное расширение
    по плану «канала моста», не срочно.

29. **[LOW] Пустой блок в respond()** -> core/agent.py:5128-5134: заголовки
    «REFLECTION SCHEDULER»/«COGNITIVE QUEUE» без кода между ними -> косметика,
    след недописанного раздела -> удалить при следующем касании.

---

## Карта подсистем

**core/ (агентский мозг, 57 файлов)**
- `agent.py` (5415 строк) — класс Agent: сборка всех подсистем в __init__
  (87-383), capability-алиасы (384-499), системные промпты (596-979),
  detect_language (985), build_context (1012), генерация LLM (1153-1320),
  ремонты перспектив/идентичности (1414-1613), быстрые каноны SELF_QUERY
  (1691-3335), мировой канал (3336-3510), роутер-обёртка (3512), respond
  (3589-5153), personality_review/apply_reflection_cycle/reflect/close
  (5159-5387).
- Роутинг: `context_router.py` (regex-маршруты SELF/USER/MEMORY +
  WORLD_OBSERVATION по маркерам моста), `cognitive_gate.py`,
  `processing_plan.py`, `cognitive_triage.py`.
- Познание: `cognitive_queue.py` (JSON-очередь в data\), `cognitive_processor.py`
  (двухфазная обработка: фон-анализ / применение в главном потоке),
  `cognitive_reasoner.py`, `cognitive_decision_engine.py`, `cognition_worker.py`
  (daemon-поток), `epistemic_engine.py`/`epistemic_intent_detector.py`.
- Клеймы: claim_engine/policy/router/shadow/schema, semantic_claim_extractor/
  auditor, lexical_claim_adapter, self_claim_validator/triage, predicate_registry,
  evidence_provider.
- Автономия: autonomy_scheduler/orchestrator/arbitrator/runtime/factory,
  autonomous_cycle (мёртв — см. №22), initiative.py (используется только мёртвым
  cycle).
- Само-выводы: self_conclusion_store/state (847/728 строк), self_concept_resolver/
  policy, self_observation_bridge, self_state_interface, current_mind_state,
  runtime_state, dialogue_state.
- Санитайзеры: output_sanitizer, response_packet_sanitizer, perspective_guard,
  identity_consistency/repair, fast_verbalizer, quick_reflex, prompts.

**identity/ (личность, 53 файла)**
- Состояние: self_state.py (JSON-персистентность data\self_state.json),
  user_state.py, identity_seed.py (сид: миссия, ценности, устремления — текст
  чистый).
- Конвейер черт: proposal.py → promotion.py (пороги 0.80/2.8/≥2 независимых
  ключей) → personality_lifecycle.py (CANDIDATE→EMERGING→ACTIVE→WEAKENING→DORMANT→
  REJECTED; promote/reinforce/contradict/decay) → personality_history.py
  (журнал в SQLite) → identity_manager.py (единственная точка promote:128).
- Детекторы паттернов: interest/preference/habit/belief/behavior/action_* —
  питают evidence.
- Аффект: appraisal_engine, affective_state (персистентна в self_state через
  set), affective_self_observer/dialogue_policy/behavior_policy.
- Цели: goal.py/goal_manager/goal_planner/generator/review/plan_generator,
  adaptive_planner/controller, motivation.
- Рефлексия: reflection_engine/cycle/scheduler, self_reflection (сломан
  ownership-guard — №6), self_consistency, self_experience, behavioral_validator,
  belief_challenge_detector, personality_reflection.
- Инструменты: tool_registry/policy/runner, filesystem_executor (sandbox root
  C:\EddieAI — умеет писать в собственные исходники!), web_executor, llm_executor,
  task_controller, action_selector/planner/executor/router/choice.

**memory/ (SQLite-память, 15 файлов)**
- database.py: единый коннект к data\memory.db, RLock, WAL, busy_timeout 5000;
  таблицы events, self_proposals, evidence, knowledge, personality_history.
- evidence.py: таблица evidence_events (миграция ADD COLUMN independence_key),
  формула уверенности: repetition_signal*0.7 + diversity*0.3.
- manager/retrieval/patterns/knowledge*/external_knowledge/source_evaluator/
  provenance/tool_experience/self_interpretation/research_context — контексты,
  запись знаний, оценка источников.

**Точка входа**: main.py — Agent() → AutonomyRuntimeFactory(agent).build()
(стартует cognition_worker) → консольный цикл respond/exit → close().

**Мост (simulation_framework)**: engine/runtime.py (prepare→MemorySandbox→
attach_eddie→start; process_eddie_event: try/except → failed=True + rollback,
runtime.py:630,742-753) ↔ eddie/bridge.py (build_observation → respond →
snapshot) ↔ eddie/state_reader.py (читает self_state.data: emotional_state,
goal_plans, self_conclusion_state + autonomy_execution_state) ↔ eddie/
action_observer.py (перемещения по фразам).

**Конвейер личности (проверка целостности)**: источники evidence —
SelfObservationBridge, UserEvidenceRecorder, детекторы паттернов, ответ агента
(respond:5030-5085; beliefs туда не проходят — 5035-5040) →
EvidenceConsolidator.consolidate → PromotionEngine.evaluate → IdentityManager.
evaluate → PersonalityLifecycle.promote (единственная точка promote в коде:
identity_manager.py:128) → PersonalityHistory.record. Обходных записей черт
мимо конвейера не найдено; поля goals/emotional_state/self_conclusions ведутся
своими легитимными владельцами (goal_*, affective_state, self_conclusion_*),
что соответствует архитектуре. Глубина GoalManager/AffectiveState [НЕ ПРОВЕРЕНО]
(вне объёма этого прохода).

---

## Кодировка

Скан всех .py/.json/.md проекта C:\EddieAI (без .venv/__pycache__/.git):
199 файлов. Признаки: mojibake = символы «Ð»/«Ñ» (двойное UTF-8↔cp1252);
«???» = серии из ≥3 знаков вопроса.

| Файл | Mojibake (символов) | «???» (серий) | BOM | Примечание |
|---|---|---|---|---|
| core/prompts.py | 1880 (78/420 строк) | 0 | нет | мёртвая persona-функция |
| core/agent.py | 824 | 3 | нет | промпты USER_QUERY, события, фолбэки |
| data/cognitive_queue.json | 192 | 702 | — | ПРОДАКШН-ДАННЫЕ заражены |
| core/autonomy_runtime_factory.py | 97 | 3 | да | описания tools |
| identity/self_consistency.py | 0 | 15 | нет | capability-строки |
| identity/self_reflection.py | 0 | 13 | нет | сломанный ownership-guard |
| identity/action_planner.py | 0 | 12 | да | шаблоны планов |
| memory/manager.py | 0 | 9 | нет | метки «Эдди:»/«Память пока пуста» |
| data/cognitive_queue.before_reset.json | 0 | 6 | — | тестовый артефакт |
| memory/evidence.py | 0 | 6 | нет | комментарии |
| identity/behavior_pattern_detector.py | 0 | 5 | да | шаблоны |
| core/agent_loop.py | 0 | 4 | да | reason идентичности |
| voice_checker.py | 1 | 0 | нет | НАМЕРЕННЫЙ regex-детектор mojibake — не баг |
| docs_engineer/CHANGELOG.md, MEMORY.md, AGENTS.md, SESSION_BRIEF | по 1-2 | — | — | цитаты мусора |

BOM: **149 файлов** (полный список зафиксирован аудитом; основные массивы —
identity/* (~50), core/* (~40), memory/* (15), все root-тесты *.py).
Чистые от mojibake ключевые файлы: identity/personality_lifecycle.py,
identity/promotion.py, identity/evidence_consolidator.py,
identity/reflection_scheduler.py, core/context_router.py, core/cognition_worker.py,
core/cognitive_processor.py, core/cognitive_queue.py, memory/database.py,
identity/self_state.py, identity/identity_seed.py.

---

## Готовность к мосту (чек-лист)

- [x] `Agent.respond(str)->str` существует, сигнатура стабильна (core/agent.py:3589).
- [x] Канал WORLD_OBSERVATION разведён: маркеры роутера согласованы с форматом
      bridge.build_observation (context_router.py:84-88 ↔ bridge.py:288-308);
      свой промпт и пост-валидатор голоса (agent.py:3336-3510, voice_checker).
- [x] Наблюдения и ответы канала пишутся в память с source=world_bridge/world_voice
      (agent.py:3703-3731) — изоляция источников соблюдается.
- [x] Снимок состояния сбоку: EddieStateReader.compact() по self_state.data +
      autonomy_execution_state; ключи self_state подтверждены (18 шт., содержимое
      не публиковалось).
- [x] Изоляция памяти прогона: MemorySandbox копирует data\memory.db в run_dir
      и подменяет connection агенту (memory_sandbox.py:25-103).
- [x] Защита от падения одного цикла: runtime ловит исключения observe_world →
      failed=True, журнал, rollback (engine/runtime.py:630,742-753); console-main
      тоже защищён (main.py:42-45).
- [ ] НЕТ таймаута LLM: зависание Ollama замораживает мир (см. №8) — главный
      технический риск моста.
- [ ] Хрупкий строковый парсинг наблюдения («Обстановка»/«Событие»+JSON,
      agent.py:3417-3445) и дубль маркеров в двух репозиториях (№19).
- [ ] Sandbox зависит от legacy-таблицы «memories», которой нет в схеме (№10).
- [ ] voice_checker импортируется как корневой модуль C:\EddieAI (agent.py:3403-3411) —
      работает только потому, что bridge вставляет корень в sys.path (bridge.py:9-17).
- [ ] Прогрев двух моделей при создании агента до старта мира (~3+ ГБ RAM, №17).
- [ ] Канал действий — только перемещения, 13 фраз (action_observer.py:6-35).

---

## Общее здоровье

Архитектурно система здоровее, чем выглядит по числу файлов: конвейер
личности evidence→promotion→lifecycle целостен и имеет одну точку PROMOTE;
двухфазная фоновая когниция грамотно разводит потоки (анализ в фоне —
применение в главном); изоляция памяти прогонов через песочницу работает;
WORLD_OBSERVATION-канал уже встроен в respond(). Монолит agent.py огромен,
 но декомпозиция на ~110 модулей вокруг него реальна и читаема.

Главные болезни: (1) кодировочная зараза добралась до ЖИВЫХ промптов,
пользовательских фолбэков и записываемых данных, включая отключение
ownership-guard’а — это уже не косметика; (2) ресурсные риски ночного прогона:
нет таймаута LLM, постоянный прогрев обеих моделей, потокобезопасность памяти
на прямых SQL-обходах; (3) накопление: cognitive_queue.json 3 МБ, отсутствие
индексов и ротации, неатомарная запись self_state.json.

Риски полного прогона с LLM сегодня ночью (по убыванию):
1. Зависание Ollama без таймаута → мир стоит (№8).
2. Своп/OOM из-за прогрева двух моделей + дашборд на 8 ГБ (№17).
3. Разовое исключение в respond() → прогон завершится failed=True раньше времени
   (защита runtime сработает, но прогон будет остановлен).
4. Тихая смерть CognitionWorker → деградация фоновой когниции (№16).
5. Гонки прямых SQL без RLock при активном фоне — редкие, но вероятные ошибки
   SQLite (№9).

Что НЕ проверялось: содержимое data/*.db (запрещено), внутренности
quick_reflex/cognitive_reasoner/epistemic_engine/claim-стека (карта — по
именам), retrieval под нагрузкой, GoalManager/AffectiveState вглубь,
dashboard симуляции. Помечено [НЕ ПРОВЕРЕНО]/[ВЕРОЯТНО] по месту.

---

## Топ-5 находок

1. **Кодировка в живых путях и данных** — USER_QUERY-промпт, фолбэк-ответ,
   события памяти, knowledge о пользователе, сломанный ownership-guard
   (№2-№6): лечится малыми диффами строк, но затягивать нельзя — каждый день
   прогонов пишет мусор в личность.
2. **Неатомарная запись self_state.json** (№7) — единственная точка полного
   отказа личности; фикс на 3 строки (tmp+replace).
3. **LLM без таймаута + прогрев обеих моделей** (№8, №17) — определяет,
   состоится ли ночной прогон вообще на 8 ГБ RAM.
4. **Прямой SQL мимо RLock при фоновом воркере** (№9) — тихая порча памяти
   под нагрузкой; сводится централизацией доступа.
5. **Persona-промпт основного маршрута отсутствует/мёртв** (№14, №1) —
   стратегическая причина слабого «голоса»; после починки строк — решение
   совета о его включении.

*Отчёт создан читающим аудитором, ночь 23.08.2026. Единственный изменённый
файл — этот. Процессы LLM/симуляций не запускались; data/*.db не открывались.*
