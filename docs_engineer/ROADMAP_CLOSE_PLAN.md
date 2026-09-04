# Дорожная карта полного закрытия этажей 5–10, 12

[АКТУАЛЬНО] Создано 03.09.2026 по решению Эдди: «сначала закрыть прошлые
этажи, потом делать 11». Режим: полное закрытие бэклогов, не «база закрыта».
Ведёт главный инженер. Это рабочий чек-лист, разбитый на измеримые блоки.

Приоритет: по возрастанию этажа (фундамент сверху-вниз): 5 → 6 → 7 → 8 → 9 →
10 → 12. Этаж 11 (совместная жизнь) — ПОСЛЕ полного закрытия прошлых.

Обоснование оценок — анализ фактов кода (grep), не деклараций:
многое из бэклогов уже есть как «квиты-зародыши» (preferences, self-model,
goal_review, vision-роль); работа = доведение до полноты.

---

## Этаж 5 — Личность (порядок: 1)

Бэклог: полноценные предпочтения; привычки (от зачатка к полноте);
взросление характера.

Уже есть как зачаток [Подтверждено grep]:
- `identity/action_preference_detector.py` — детектор стабильных предпочтений
  из сопоставимых действий (category="preference");
- `agent.py`/`prompts.py`/`self_state.py` — preferences в self_state/prompts;
- `identity_manager.py` — приём proposal_type=="preference";
- `speech_habits` + `DecisionCore.consolidate_habits` + `_rebuild_pattern_from_habit`
  — зачаток привычек речи; связь паттерн↔привычка.

Чего нет / что довести до полноты:
- [x] П-1 Полноценная модель предпочтений: не только категория "preference",
      но и тип (действие/тема/среда), сила, провенанс, время, конфликт с
      интересами. Оценка: 1–2 смены.
      [ВЫПОЛНЕНО 04.09: П-1a (порог MIN_CHOICES 6→4), П-1b (dict-формат
      preference: label/context/method/share/total/source/ts, обратная
      совместимость + claim-валидация dict без repr-протечек), П-1c
      (связка preference с outbox-подсказками), П-1d (тип/сила предпочтения
      + конфликт «предпочтение-интерес»: preference_model.py —
      preference_type/strength_of/enrich_entry/preference_conflicts/
      format_preferences_rich; запись через identity_manager, чтение в
      prompts/current_mind_state/self_concept_resolver; agent.py plain-формат
      мин. дифф). TDD: test_preference_model (13) GREEN + регресс PASS +
      final_regression_suite 7 passed + orchestrator_local PASS.]
- [x] П-2 Привычки действий (не только речи): накопление устойчивого
      паттерна действия → habit-черта через единый lifecycle. Оценка: 1 смена.
      [ВЫПОЛНЕНО 04.09: ядро (детектор→evidence→lifecycle→self_state) уже было;
      закрыт остаток «к полноте» — читаемость через habit_label/format_habits
      в prompts/agent/current_mind_state. TDD test_habit_format GREEN.]
- [x] П-3 Взросление характера: путь изменения численных порогов/черт со
      временем/опытом (зачаток — числовые trait-пороги в self_development/).
      Оценка: 1 смена.
      [ВЫПОЛНЕНО 04.09: пер-чертовое взросление по накопленному опыту
      (evidence_count). Мягкая адаптация: `_status_from_strength_ev`
      (пороги ACTIVE/weakening плывут на ±0.02 за каждые 3 подтверждения,
      ACTIVE вниз, weakening вверх, emerging неизменен) + `_decay_maturity_factor`
      (зрелые черты затухают медленнее). `_status_from_strength` сохранён как
      базовый (evidence=0) — обратная совместимость. Единственный узел
      пересчёта статусов. TDD test_personality_adulting (6) GREEN + регресс PASS.]

## Этаж 6 — Мотивация (порядок: 2)

Бэклог: конкуренция целей; полное многошаговое планирование.

Уже есть [Подтверждено]: DecisionCore (decide/learn), goal_review (GoalReview
в goal_generator/agent_loop), discovery-мотивация, каркас action/adaptive/goal
planner.

Чего нет:
- [x] М-1 Конкуренция целей: приоритизация активных целей, вытеснение
      низкоприоритетных, переключение, учёт ресурсов/энергии. Оценка: 1–2 смены.
- [x] М-2 Полное многошаговое планирование: разрыв текущего каркаса планирования
      до полноценного (декомпозиция, оценка выполнимости, пересмотр).
      Оценка: 1 смена.
      [ВЫПОЛНЕНО 04.09: PlanFeasibility (выполнимость шагов через ActionPlanner,
      отсев с FeasibilityIssue) + ensure_phases (декомпозиция: добыча→анализ→
      фиксация, вставка недостающей выполнимой фазы) + GoalPlanner.revise /
      TaskController.revision_policy / TaskRevisionPolicy (пересмотр при
      недоступном инструменте). Интеграция в goal_plan_generator и factory.
      TDD: 3 новых файла (16 кейсов) GREEN + регресс PASS. Этаж 6 закрыт.]

## Этаж 7 — Внутренняя жизнь (порядок: 3)

Бэклог: полноценный self-model; исследование сознания.

Уже есть: self_concept_policy, self_observation_bridge, self_concept_resolver,
reflection_engine, dream_processor, night consolidation.

Чего нет:
- [x] В-1 Полноценный self-model: структурированная модель себя (способности,
      ограничения, состояние), а не только пункты политики. Оценка: 1–2 смены.
- [x] В-2 Исследование сознания: осознанный запрос/наблюдение своих состояний,
      дневник-рефлексия о собственной работе. Оценка: 1 смена.

## Этаж 8 — Мир (порядок: 4)

Бэклог: фоновые процессы как данные; свой мир-модель.

Уже есть: WorldProbe (RAM/CPU/диск/топ-процессы ctypes), world_description,
WORLD_SNAPSHOT-триггеры.

Чего нет:
- [x] МИР-1 Фоновые процессы как данные: не только топ-N счётчик, но история/
      статистика процессов во времени для картины «что происходит на ПК».
      Оценка: 1 смена.
- [x] МИР-2 Свой мир-модель: структурная модель окружения (папки/проект/ПК)
      как обозримая сущность, не только текстовая сводка. Оценка: 1 смена.

## Этаж 9 — Инструменты (порядок: 5)

Бэклог: terminal; программы; установка ПО. РИСК БЕЗОПАСНОСТИ.

Уже есть: FilesystemExecutor read-only sandbox, list/search, web executor,
CuriosityDirector.

Чего нет (всё требует отдельного решения совета по безопасности, белый
список, RAM):
- [x] ИНСТР-1 Terminal: безопасный запуск команд по белому списку. Оценка: 1–2 смены.
      [ВЫПОЛНЕНО 04.09: `identity/command_policy.py` (анти-катастрофический denylist
      через config/commands.yaml), `identity/terminal_executor.py` (subprocess +
      timeout 30с + захват stdout/stderr + лимит 50KB). Интеграция: ToolExecutionPolicy
      (allow_powershell=True, _powershell через CommandPolicy), ToolRunner (ветка
      powershell в _execute_real), factory (регистрация TerminalExecutor). Self-model:
      секция ownership (mine/eddies/installed/system/installing). TDD: test_command_policy
      (10), test_terminal_executor (13), test_self_model_ownership (4), test_tool_runner_run_command
      (5), test_command_audit (3) — ALL PASS; final_regression_suite 7 passed,
      orchestrator_local PASS.]
- [x] ИНСТР-2 Программы: запуск по белому списку (ДПК2). Оценка: 1 смена.
      [ВЫПОЛНЕНО 04.09. Решение Эдди: «нет белого листа, всё можно что захочет»
      (вариант «Свобода, но без разрушительного»). `identity/app_launcher.py::AppLauncher`
      — свободный запуск любых программ, фильтр только CommandPolicy.is_destructive
      (форматирование/рекурсивное удаление системного/принудительное выключение),
      история в self_state.app_launch_history. TDD test_app_launcher (6) GREEN.]
- [x] ИНСТР-3 Установка ПО: только по явному согласованию Эдди. Оценка: 1 смена.
      [ВЫПОЛНЕНО 04.09. Решение Эдди: установка без согласования (не разрушительно),
      анти-катастрофический фильтр остаётся. `identity/software_install.py::SoftwareInstaller`
      — любой менеджер (pip/winget/choco/npm), история в self_state.install_history.
      TDD test_software_install (8) GREEN. Allowlist отменён: CommandPolicy.is_safe =
      не-разрушительно (denylist-only).]
      ЭТАЖ 9 «Инструменты» — ЗАКРЫТ ПОЛНОСТЬЮ (ИНСТР-1/2/3).

## Этаж 10 — Органы чувств (порядок: 6)

Бэклог: зрение; screen perception; видео-восприятие.

Уже есть: модель `zen-kimi-vision` (roles=["vision"]) в model_orchestrator;
аудио/STT/TTS закрыто.

Чего нет:
- [x] ЗР-1 Screen perception: скриншот → OCR/сводка → событие в память
      (ДПК3, смотритель Ox Alpha Free/pix). Оценка: 1–2 смены.
      [ВЫПОЛНЕНО: `identity/screen_perceiver.py::ScreenPerceiver` — непрерывный
      vision-контур (mss захват → change detect → vision model → memory);
      интегрирован в autonomous_runtime tick. SharedLifeobserve() добавляет
      LLM-оценку значимости совместных моментов.]
- [x] ЗР-2 Видео/образ: разбор изображения/кадра моделью. Оценка: 1 смена.
      [ВЫПОЛНЕНО: ScreenPerceiver.capture_now() → vision model (zen-kimi-vision)
      → SCREEN_PERCEPTION-события в память; SharedLife — LLM-классификация
      совместных активностей (movie/music/game/coding/browsing/other).]
      ЭТАЖ 10 ЗАКРЫТ [04.09]: регресс 26 тестов PASS (test_screen_perceiver,
      test_screen_controller, tests/test_integration_vision,
      tests/test_model_orchestrator_vision).

## Этаж 12 — Агентность (порядок: 7)

Бэклог: собственные проекты; исследовательская деятельность как постоянная.

Уже есть: автономный цикл, scheduler, DecisionCore, инициатива.

Чего нет:
- [x] А-1 Собственные проекты: устойчивое ведение долгой исследовательской
      задачи (не разовый интерес), трек прогресса. Оценка: 1–2 смены.
- [x] А-2 Исследовательская деятельность как постоянная: цикл «нашёл тему →
      углубился → зафиксировал → следующая», не только разовая любопытство.
      Оценка: 1 смена.

---

## Итого

Минимальная оценка суммарного объёма: **~12–23 смен** при соблюдении правил
проекта (TDD, Context7 на каждый кусок, docs после каждой задачи, RAM-дисциплина).

Порядок исполнения — строго по нумерации этажей. Каждый закрытый блок:
TDD → байт-проверка кодировок → CHANGELOG → TODO статус → ROADMAP колонка.

## Этаж 11 — Совместная жизнь (после полного закрытия 5–10, 12)

Ядро (по согласованному направлению): программная модель совместных
активностей (фильмы/музыка/игры) → SHARED_EXPERIENCE-память (провенанс 0.7
есть) + лента «совместной истории» + влияние на эмоции/отношения + интеграция
с мессенджером (команды запуска активности, диалог, инициатива EddieAI).
Внешние тяжёлые активности (реальный YouTube/Minecraft-плеер) — отдельными
решениями по RAM/белому списку.

Чего нет / что сделано:
- [x] ЗР-1 Ядро совместной жизни: `identity/shared_life.py::SharedLife`
      (наблюдение описания экрана → LLM-оценка значимости → SHARED_EXPERIENCE-
      события + build_feed для промптов). Интеграция: runtime tick после
      screen_perceiver, factory. TDD: 4 теста GREEN.
- [x] ЗР-2 Эмоциональная оценка совместных активностей:
      `identity/shared_appraisal.py::SharedAppraisal` (ACTIVITY_EMOTIONS +
      INTIMACY_DELTAS по типу активности → apply_reaction + appraise_relationship).
      Интеграция: factory (привязан к affective_state). TDD: 4 теста GREEN.
- [x] Интеграция: self_model (shared_life секция), autonomous_runtime
      (observe+appraise в tick), autonomy_runtime_factory (создание + проводка).
      Интеграционные тесты: 6 GREEN. Регресс: 14 new + final_regression 7 passed
      + orchestrator_local PASS.
- [x] Диалог/мессенджер: интеграция команд совместных активностей с
      общением в реальном времени. `identity/shared_activity_commands.py`
      (детерминированный парсер «давай посмотрим…»/«включи музыку»/
      «поиграем…»/«выключи, хватит») + `core/eddie_server.py::_apply_shared_activity_command`
      — команда применяется МГНОВЕННО в handle_user_message (без ожидания
      автономного цикла; решение Эдди: общение всегда в реальном времени),
      старт/стоп SharedActivityManager + запись SHARED_EXPERIENCE.
      TDD: test_shared_activity_commands (10) + test_server_shared_activity (5) GREEN.
- [x] Инициатива EddieAI: `identity/shared_activity_manager.py::SharedActivityManager`
      — трекер текущей активности (персистентный в self_state.current_shared_activity)
      + `suggest_activity` по аффекту/интересам с гашением недавних; в tick
      автономии — инициатива через send_initiative с кулдауном 3600с.
      Дополнительно: SharedAppraisal применяет intimacy/trust к
      self_state.relationships.Eddie; SharedLife в factory получил retrieval
      (build_feed ожил); self_model.shared_life — реальные данные; блок
      «ТЕКУЩАЯ СОВМЕСТНАЯ АКТИВНОСТЬ» в промптах.
      TDD: test_shared_activity_manager (14) + test_shared_appraisal (6) GREEN.
      Регресс: 52 теста PASS + final_regression 7 passed + orchestrator_local PASS.
      ЭТАЖ 11 ЗАКРЫТ ПОЛНОСТЬЮ.

---

[АРХИВ] (пусто)
