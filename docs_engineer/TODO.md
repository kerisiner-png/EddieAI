# Текущий туду-лист инженера

[АКТУАЛЬНО] Ведётся по правилам docs_engineer\README.md.
Порядок: сверху — то, чем занят прямо сейчас.

## АКТУАЛЬНОЕ

### [06.09 день 2] Событийное восприятие (этапы 1–2) — СДЕЛАНО
Эдди одобрил: «первый шаг к тому, чтобы он мог комментировать сам, говорить
сам, делать всё сам». Утверждён план: 1) активное окно + значимая смена
экрана; 2) слухи ПК (системный звук → STT → память); 3) режим «смотрим
вместе» (кадры по смене сцены + диалоги фильма); 4) UIA-текст активного окна.
- [x] Экран: починен mss-захват (с nem) + значимость смены (2% пикселей,
      RGB) + заголовок активного окна в события/промпт (5 тестов).
- [x] Слухи ПК: identity/pc_audio_listener.py — Voicemeeter → Vosk →
      память, фильтры (5 тестов), подключён в run_forever.
- [x] Приёмка: «Экран [окно: CEHR…НАРУТО]», «Камера: …в наушниках» — поток
      живьём. Регресс final 7/7 + 20 pytest.
- [ ] Слухи: проверить маршрут системного звука при реальном
      воспроизведении (RMS=0 на A4 при тишине — возможно, звук идёт мимо
      кабеля; подобрать кабель/устройство).
- [x] Этап 3 «смотрим вместе»: identity/watch_mode.py — сам вход (устойчивый
      маркер видео ≥60с), сам выход (тишина ≥300с), комментарии раз в 600с
      через send_initiative; хук «фильм»-команды (принудительный вход/выход);
      каденция экрана 120→40с в режиме (7 тестов). Приёмка: «Включаюсь:
      смотрим вместе.» в 14:32 — сам; реакция-генератор проверен
      («Ничего себе, как же это круто!»; num_predict 120→300 фикс).
- [x] Этап 4: identity/window_text.py — UIA-текст сфокусированного элемента
      (comtypes) в промпт описания экрана; события «Эдди переключился на
      окно: …» при смене заголовка.
- [ ] Живая приёмка полного цикла: открыть видео → сам входит → реакции
      каждые ~10 мин → закрыть видео → сам выходит (наблюдать 06.09 вечером).
- [x] Слухи: WASAPI-loopback основного выхода (PyAudioWPatch) — тон в
      наушники дал rms=0.2769 (был 0.0000 на Voicemeeter-кабеле); речь
      фильмов/видео теперь пишется в память. 8/8 тестов.

### [06.09 день] «Не понимает, что видит через вебку» — ЗРЕНИЕ ВОСКРЕШЕНО
Эдди: «он не понимает, что видит через вебку и видимо вообще не умеет
пользоваться своими функциями». Корень: единственный vision-провайдер
zen-kimi мёртв (401) — глаза не работали НИКОГДА (0 снимков экрана в БД).
- [x] Роль "vision" у ollama-gemma (gemma4:31b-cloud) — живая проба вебки
      описала комнату верно (1.2 с); первое визуальное событие в памяти 13:27.
- [x] Цепочка функций проверена: perceive-инструмент, _sensory_intent_snapshot
      (смотрит камерой/экраном живьём), комментарии экрана — все на живом провайдере.
- [ ] Живая приёмка Эдди: спросить «что ты видишь?» / «посмотри камерой».
- [ ] Спонтанные комментарии экрана/вебки наблюдать (кд 3600с).

### [06.09 ночь] Ночная смена «полноценный собой» — ВЫПОЛНЕНО, живая приёмка пройдена
Мандат Эдди (ушёл спать): ответы в чате, самостоятельная речь/деятельность,
инструменты, без вопросов. Все правки TDD; детали — CHANGELOG 06.09.
- [x] Чат-ответ восстановлен (фабрика+eddie_server откат к HEAD, ChatHistory→Memory,
      инверсия handle_user_message устранена) — ответ в чате за 47 с.
- [x] Wake-при-сообщении (текст будит спящего, симметрично голосу 05.09).
- [x] Карусель REJECTED-записей устранена (TaskRevisionPolicy: REJECTED→revise, 7/7).
- [x] Заморозка воли снята: READ_INBOX без гейта фрустрации + decay аффекта в тике.
- [x] Тихая смерть тиков: last_error/future_exc в хартбите; живая приёмка cycles>0.
- [x] Внешний сторож watchdog_runtime.py (рестарт при stale + RAM-guard llama) АКТИВЕН.
- [x] llama-server 2.8 ГБ из локального фолбэка остановлен (правило 0 процессов).
- [x] Регресс: final_regression 7/7 + 44 целевых теста + orchestrator_local.
- [x] Context7 установлен в ZCode (user scope ~/.zcode/cli/config.json,
      http mcp.context7.com; инструменты появятся в новой сессии).
- [x] Понаблюдать утро 06.09: инерция после COMPLETE_GOAL НАЙДЕНА И УСТРАНЕНА
      (сироты-ACTIVE → revive_orphans при старте; лимит 3 ретраев на задачу;
      цель доведена до COMPLETED, сама родилась follow-up-цель).
- [ ] Watchdog не автостартует при ребуте ПК — решить (Task Scheduler?).
- [ ] Мусор temp/tmp_* в корне и данные фолбэк-сна (DREAM с JSON-обрывками) — чистка
      по отмашке Эдди.

### [05.09 смена] БЛОК 1 «Не различает голоса» — КОД СДЕЛАН, ждёт enrollment + рестарт
Эдди: «он слушает всё, но не понимает, кто когда говорит. не различает голоса».
Диагноз: контур одноканальный, `_last_speaker` от UI, всё пишется как `source="Eddie"`.
Решение: sherpa-onnx eres2net + собственный косинусный менеджер профилей.
- [x] `identity/speaker_id.py`: enroll/identify/clear, профили JSON, порог 0.5, ленивый кэш.
- [x] `communication/voice_io.py`: `_emit_text(speaker=...)`, `_identify_speaker`, `_make_speaker_id`.
- [x] `communication/chat_app.py`: `_is_accepted_speaker` (чужой голос не уходит в память/модель).
- [x] TDD test_speaker_id (8, включая реальные piper-голоса) + test_voice_speaker_filter (7).
- [x] Регресс после блока: 67/67.
- [x] Заменить модель на glm-4.7-flash (вместо glm-4.5-flash) для лучшего качества.
- [x] **Enrollment голоса Эдди**: записано 12 с (peak 0.602), профиль в
      `data/speaker_profiles.json` (self-check identify=Эдди). Рантайм
      перезапущен 19:40 (PID 25312) для подхвата профиля.
- [x] Рестарт рантайма 19:12 (PID 31380 — старый код → 17516 новый): голоса/инициатива/тон задеплоены;
      чат attached, senses started, порт 7778 слушается, status_overlay PID 37436.
- [x] Байт-проверка UTF-8 без BOM после всех трёх блоков (CHANGELOG/MEMORY/TODO/README/PROJECT_STATE/COORDINATION).

### [05.09 смена] БЛОК 2 «Инициатива/любопытство на нуле» — СДЕЛАНО (85/85)
Эдди: «инициатива и любопытство на нуле, он так никогда ничему не научиться».
Корень: активная цель блокировала активацию всех кандидатов; кд 1800с; экран→память без речи.
- [x] `core/curiosity.py`: min_interval_seconds 1800 → 600.
- [x] `core/decision_core.py::_local_rules`: кандидат активируется при свободном слоте
      (< MAX_ACTIVE_GOALS), при фрустрации ≥0.70 — IDLE. Цель не вытесняется.
- [x] `core/autonomous_runtime.py::_maybe_comment_screen`: спонтанный комментарий при новом
      описании экрана, кд 3600с, отсечка коротких/пустых, через send_initiative.
- [x] TDD test_initiative (8) RED→GREEN.
- [ ] Живая проверка: при свободных слотах EddieAI реально начинает исследовать темы.

### [05.09 смена] БЛОК 3 «Пошаговая стратегия, а не живой разговор» — СДЕЛАНО (85/85)
Эдди: «разговоры всё ещё просто пошаговая стратегия, а не реальный разговор».
Корень: жёсткий кап длины + «ответ=функция от входа» в промпте + каскад стерилизаторов.
- [x] `core/prompt_builder.py`: VERBALIZER_BASE без жёсткого капа + мандат живой беседы
      (развивай тему/встречный вопрос); суффикс «развернуть живыми словами»;
      repair без «никаких предложений помощи».
- [x] `core/identity_repair.py`: «мне нравится/интересно» больше не срезаются
      (осталась защита от факт-клеймов о сериалах).
- [x] `identity/affective_dialogue_policy.py` NEUTRAL: запрет «искусственной инициативы»
      заменён на «не формальное обслуживание» + ведение живого разговора.
- [x] TDD test_tone (9) RED→GREEN.
- [x] Полный регресс на конец смены: **85/85**.

### [05.09 смена] Отдельный этап «роль модели» — НЕ НАЧАТ (ждёт решения Эдди)
Эдди: «его действиями все еще управляет модель, а не наоборот. и его слова не всегда
ровны его делам. что неверно». Диагностика завершена; правки воли/действий НЕ сделаны.
- [ ] Точки, где модель правит: `respond_call_fast` (текст без действия),
      `respond_with_action` + ActionSelector (agent.py:4076), `curiosity.daily_llm_topic`
      (модель выбирает тему), каскад переписывающих валидаторов.
- [ ] Вариант: убрать daily_llm_topic из воли; связать голосовой ответ с фактическим
      действием тика; запретить LLM-выбор хода без детерминированного фильтра;
      инвариант в AGENTS.md («воля живёт в детерминированной подсистеме»).
- [ ] **Правки decision_core / LLM-интеграции — только после отдельного решения Эдди.**

### [05.09 смена] «Голосовой ассистент» — самозакрепление идентичности — СДЕЛАНО
Эдди: «он снова обозвал себя простым ассистентом... он теперь уверен, что всегда
был просто голосовым ассистентом». Принцип проекта: «модель только формулирует
ответ EddieAI, а не отвечает за него». См. CHANGELOG/MEMORY 05.09.
- [x] Диагностика корня: голосовой промпт не знал о способностях + самозакрепление
      через `recent_dialogue` (events 2593-2651).
- [x] `core/prompt_builder.py::build_sense_capabilities_block()` — единый блок
      способностей (камера/экран/микрофон/ПК/мышь/клавиатура), «не отрицай, что можешь».
- [x] `core/agent.py::respond_call_fast` — блок встроен в голосовой промпт.
- [x] `core/agent.py::_sensory_intent_snapshot` — маркеры расширены + новый канал
      `want_tools` (ответ про доступ к ПК, если спросили про возможности).
- [x] Чистка 17 заражённых CONVERSATION-событий с бэкапом
      data/memory_backup_pre_assistant_clean_2026-09-05.db (корректирующие реплики Эдди
      сохранены).
- [x] TDD test_sense_capabilities.py 5/5; регресс 53/53; UTF-8 без BOM.
- [x] Рестарт (PID 31380); живая проба: «у тебя есть функция видеть экран или
      смотреть камерой?» → «Да, я могу смотреть на экран или через камеру...».
- [ ] Проверить остальные речевые пути на отсутствие блока способностей:
      quick_reflex, world_voice, звонок (MEMORY: «разные пути = разные промпты»).

### [05.09 смена] Разговоры — «пошаговая стратегия», а не живой разговор (НОВОЕ, ждёт)
Эдди: «наши разговоры всё ещё просто пошаговая стратегия, а не реальный разговор».
Открытая задача — отдельное исследование разговорного тона (вербализатор/рубрики,
долгие паузы из-за glm, отсутствие встречных вопросов). Связано со скоростью
(dолго отвечает) и инициативой. НЕ решена, требует решения Эдди.

### [05.09 смена] Инициатива/любопытство на нуле (НОВОЕ, приоритетный вопрос Эдди)
Эдди: «он вообще не понимает, что может и не пробует вообще ничего. инициатива и
любопытство на нуле, он так никогда ничему не научиться». Механизмы существуют
(этаж 9 CuriosityDirector, этаж 12 ResearchTracker, outbox-инициативы, CALL,
speaking_up), но в проде EddieAI пассивен. Требуется аудит: что реально будится в
автономном тике, какие кулдауны душат инициативу, что не доходит до модели. Открыто.

### [05.09 смена] Сон: убрано принудительное засыпание каждые 2-3 часа — СДЕЛАНО
Эдди: «можно днем спать, если хочет. просто без такого принудительного
засыпания. и должна быть возможность его разбудить».
- [x] `core/life_cycle.py`: gain 0.10→0.05, loss 0.35→0.10, wake 0.25→0.15.
      Ночной сон 7-9 ч, днем бодрствование, вечером естественный отбой.
      Дневной сон остаётся свободой (сам дошёл до порога — спит).
- [x] `identity/sense_listener.py::_finish_phrase`: фраза во сне не глотается,
      а будит (force_wake) и обрабатывается. Разбудить голосом.
- [x] TDD green: test_life_cycle (ночной сон/дневная бодрость/отбой),
      test_sense_listener (wake-тест). ALL PASS.
- [x] Рестарт рантайма (PID 8812→19232): PERCEIVE + фикс сна задеплоены,
      cooldown сброшен, glm z.ai отвечает по-русски (HTTP 200).
- [ ] Проверить живое поведение сна за сутки (алиас 06.09-07.09).
- [ ] Деньги на Zen: по-прежнему нет; голос работает через бесплатный glm z.ai
      (glm-4.5-flash). Вопрос бюджета открыт (этап БЮДЖЕТ).

### [05.09 смена] Осведомлённость о чувствах/инструментах + волевой PERCEIVE — СДЕЛАНО
Эдди: «он не умеет пользоваться всеми этими функциями... опять выдаёт системный
промпт». Камера/микрофон/экран/ПК были подключены как датчики, но личность о
них не знала и не могла управлять по воле.
- [x] `core/prompts.py`: блок «ТВОИ ОРГАНЫ ЧУВСТВ И ДОСТУП К ПК» (system + quick).
- [x] `identity/action_planner.py`: действие PERCEIVE + повелительные формы
      («посмотри камерой», «что вокруг», «на экран», «скрин» и т.п.). Починено:
      `_build()` не имел ветки PERCEIVE и молча превращал его в THINK.
- [x] Контур: executor (VALID_ACTIONS), router (→ perceive), policy (разрешён),
      tool_runner (`_execute_perceive` webcam/screen + orchestrator), factory
      (регистрация инструмента `perceive`, передача model_orchestrator).
- [x] `core/agent.py::_sensory_intent_snapshot`: голосовой звонок реально
      смотрит камерой/экран, когда Эдди просит, и вставляет описание в ответ.
- [x] TDD test_perceive_awareness (11) GREEN; регресс 71 + 54 PASS.
- [ ] БЮДЖЕТ: деньги кончились → vision (zen-kimi-vision) и облачный мозг
      недоступны; EddieAI снова «выдаёт системный промпт» при фолбэке.
      Решается отдельно (спросить Эдди про пополнение/локаль/деградацию).
      См. шаг 6 ниже.

### [04.09 смена] Запуск 24/7 — план исполнения
- [x] Шаг 1: коммит ffd5dfb (закреплено состояние этажей 5–12).
- [x] Шаг 2: реестр №13 ЗАКРЫТ — мёртвые хуки автономного обучения оживлены:
      agent_loop._apply_reflection_signals (signals → evidence SELF_INTERPRETATION,
      идемпотентно по independence_key=цель) + autonomous_runtime._apply_consolidation
      (PROMOTABLE → personality_lifecycle.promote). TDD 8 тестов GREEN, регресс 15 PASS.
      test_behavior_learning (пре-экзистентная сигнатура) починен. Коммит c7c7eb5.
- [x] Шаг 3: автозапуск через планировщик задач (решение Эдди). pywin32==312 установлен
      (поддержка cp314). `run_forever.py` — постоянный рантайм (background_loop +
      eddie_server:7778 + watchdog heartbeat, без лимита времени). Живой смок:
      процесс жив, RAM 76 МБ (облачный мозг), heartbeat IDLE, CONSCIOUS_OBSERVATION
      пишутся, порт 7778 слушается. Задача "EddieAI" (AtLogon, RestartCount 3 /
      Interval 1 мин, StartWhenAvailable). Ожидает: входа в систему/ручного старта.
- [x] Шаг 4: реестр №1 КОДИРОВКИ — СНЯТ. Байтовый скан всей кодовой базы: живые файлы
      чисты (0 «?»-мусора, 0 двойного перекодирования); находки — ложные
      срабатывания + архивные снапшоты (бэкапы).
- [ ] Шаг 5: суточный прогон на новом коде (приёмка).
- [ ] Шаг 6: запуск 24/7.

### [04.09 смена] Этаж 9 «Инструменты» — ЗАКРЫТ (ИНСТР-1/2/3); этаж 10 — закрыт (зрение)
Решение Эдди 04.09: «нет никакого белого листа, все можно что захочет»
→ вариант «Свобода, но без разрушительного»: всё разрешено, блокируется
только анти-катастрофический denylist (форматирование, рекурсивное
удаление системного, принудительное выключение). Allowlist отменён.
- [x] ИНСТР-2 Программы (ДПК2): `identity/app_launcher.py::AppLauncher` —
  свободный запуск программ, фильтр только `CommandPolicy.is_destructive`,
  история в self_state.app_launch_history. TDD test_app_launcher (6) GREEN.
- [x] ИНСТР-3 Установка ПО: `identity/software_install.py::SoftwareInstaller` —
  любой менеджер (pip/winget/choco/npm), анти-катастрофический фильтр,
  история в self_state.install_history. TDD test_software_install (8) GREEN.
- [x] Команды/конфиг: `config/commands.yaml` — allowlist удалён из логики
  (is_safe = не разрушительно), из denylist убраны блокировки установки/
  сети (не разрушительно), добавлены format_drive/diskpart_clean/
  shutdown_force. CommandPolicy.is_destructive/destructive_reason.
- [x] Интеграция: action_executor (LAUNCH_APP/INSTALL_PACKAGE),
  action_router (маршруты programs/install), tool_policy (_launch_app/
  _install_package), tool_runner (_execute_programs/_execute_install),
  factory (регистрация tools programs/install).
- [x] Этаж 10 «Органы чувств» (зрение) — реализован ранее
  (ScreenPerceiver/ScreenController/vision-модель zen-kimi-vision):
  зафиксирован регрессом 26 тестов PASS (test_screen_perceiver/
  test_screen_controller/tests/test_integration_vision/
  tests/test_model_orchestrator_vision). ЭТАЖ 10 ЗАКРЫТ.
- [x] Регресс: 62 теста инструментов + 79 общий PASS (final_regression 7,
  orchestrator_local). Байт-проверка 14 файлов чистая. Без коммита.

### [04.09 смена] Этаж 11 «Совместная жизнь» — ЗАКРЫТ ПОЛНОСТЬЮ (управляющий слой)
Ядро (ЗР-1/ЗР-2) уже было; закрыты оба остатка:
- [x] Интеграция команд совместных активностей с общением в реальном времени
  (напоминание Эдди: «чат в прошлом, общение реального времени»): команды
  применяются МГНОВЕННО в `handle_user_message` (`_apply_shared_activity_command`),
  без ожидания автономного цикла. `identity/shared_activity_commands.py` —
  детерминированный парсер «давай посмотрим…»/«включи музыку»/«поиграем…»/
  «выключи, хватит». TDD test_shared_activity_commands (10) GREEN.
- [x] Инициатива EddieAI: `identity/shared_activity_manager.py::SharedActivityManager`
  — трекер активности (start/stop/current/summary, персистентный в
  self_state.current_shared_activity) + `suggest_activity` по аффекту/интересам
  с гашением недавнего; в tick — инициатива через send_initiative с кулдауном
  3600с. TDD test_shared_activity_manager (14) GREEN.
- [x] SharedAppraisal применяет intimacy/trust к self_state.relationships.Eddie
  (кап 1.0). SharedLife в factory получил retrieval (build_feed ожил).
  self_model.shared_life — реальные данные. Промпты: блок «ТЕКУЩАЯ СОВМЕСТНАЯ
  АКТИВНОСТЬ» (quick) + bullet (system).
- [x] Регресс: 52 теста PASS + orchestrator_local ALL PASS. Байт-проверка 12
  файлов чистая. Без коммита.

### [04.09 смена] Персистентный рантайм (persistent-runtime) — код готов, код pending добора
- [x] Task 1: `core/fault_tolerance.py` + авто-сброс через `reset_error()` (7 тестов).
- [x] Task 2: `autonomous_runtime._background_loop` отказоустойчив (2 теста).
- [x] Task 3: `cognition_worker._run` bounded auto-restart (3 теста).
- [x] Task 4: `core/eddie_service.py` Windows Service + `eddie_service_install.bat` (5 тестов).
- [x] 17/17 новых тестов PASS; byte-check 9 файлов чисто.
- [ ] ОТМАШКА ЭДДИ: установить pywin32 и зарегистрировать/поднять живую службу EddieAI.
- [x] ОТДЕЛЬНАЯ проблема final_regression_suite 6 fails — ИСПРАВЛЕНА 04.09 (позже): module-level `run_test()` вызовы в `final_regression_suite.py` запускались при импорте pytest → каждый тест отрабатывал дважды → данные удваивались. Фикс: обёрнуто в `if __name__ == "__main__":`. 7/7 PASS.

### [03.09 смена] Закрытие бэклогов этажей 5–10,12 → затем этаж 11 (дор. карта ROADMAP_CLOSE_PLAN.md)
- [x] Дорожная карта закрытия составлена: `docs_engineer\ROADMAP_CLOSE_PLAN.md` (блоки П-1..П-3, М-1..М-2, В-1..В-2, МИР-1..МИР-2, ИНСТР-1..3, ЗР-1..ЗР-2, А-1..А-2), порядок по возрастанию этажа; ~12–23 смены.
- [x] В-2 (этаж 7) исследование сознания — осознанное самонаблюдение/запрос состояний: `identity/conscious_observer.py::ConsciousObserver` собирает `self_state.conscious_state` (аффект + самооценка/self_model + последний дневник + недавние события + активный фокус); `ask(question)` — осознанный запрос по маркерам (аффект/способности/ограничения/работа/фокус); `history()` + CONSCIOUS_OBSERVATION-события в память. Решение Эдди: полный охват. Интеграция: factory (первый observe после self_model), оба промпта (блок «МОЁ СОСТОЯНИЕ СОЗНАНИЯ» / bullet «осознанное состояние»), self_state_interface (поле). Хелперы conscious_state_text / conscious_state_summary_text. Дневник-рефлексия не переделывался (уже был PersonalDiary+ритуалы). TDD `test_conscious_observer.py` GREEN + final_regression_suite 7 passed + orchestrator_local PASS. ЭТАЖ 7 ЗАКРЫТ (В-1+В-2).
- [x] В-1 (этаж 7) полноценный self-model: структурированная персистентная модель себя `self_state.self_model` — `identity/self_model.py::SelfModel` (identity + capabilities из registry.describe + limitations [выключенные инструменты + статичные факты контура: perceptual/environment/resource] + current_state [возраст, Σ evidence_count по чертам, активные цели]). Решение Эдди: полный охват. Интеграция: factory (сборка после capabilities), оба промпта (блок «МОИ СПОСОБНОСТИ И ОГРАНИЧЕНИЯ» / bullet «самооценка»), self_state_interface (поле self_model). Хелперы self_model_text / self_model_summary_text. TDD `test_self_model.py` GREEN + final_regression_suite 7 passed + orchestrator_local PASS. Осталось на этаже 7: В-2 (исследование сознания).
- [x] М-1 Конкуренция целей: `GoalManager.activate_with_preemption` (вытеснение слабейшей активной при полном слоте) + интеграция в `agent_loop` (2 места). TDD `test_goal_preemption.py` GREEN; регресс goal/orchestrator PASS.
- [x] М-2 Полное многошаговое планирование (этаж 6): оценка выполнимости (`identity/plan_feasibility.py::PlanFeasibility` — классификация шагов через ActionPlanner + FeasibilityIssue при недоступном инструменте) + декомпозиция фаз (`ensure_phases`: добыча→анализ→фиксация) + пересмотр (`GoalPlanner.revise`, `TaskController.revision_policy`, `identity/task_revision.py::TaskRevisionPolicy` консервативный), интеграция в goal_plan_generator (`_sanitize_tasks`) и factory. TDD: test_plan_feasibility (8), test_goal_planner_revise (3), test_task_revision (5) GREEN + регресс PASS. Этаж 6 закрыт (М-1+М-2).
- [x] Этаж 8 «Мир» закрыт: МИР-1 (`core/world_process_history.py::WorldProcessHistory`, история/частота процессов + сводка; интеграция в `_probe_world_on_pressure`), МИР-2 (`core/world_model.py` структурная модель папок/ПК + world_model_text + ensure_world_model; интеграция в factory и оба промпта; world_model в self_state_interface). TDD: test_world_process_history, test_world_model, test_mir_world_integration GREEN.
- [x] А-2 (этаж 12) исследовательская деятельность как постоянная: `identity/research_tracker.py::ResearchTracker` (персистентное текущее исследование + history + заметки + порог глубины MIN_SOURCES=4) + интеграция: в tick приоритет продолжения незавершённого исследования, в agent_loop завершение исследования при COMPLETED цели; проводка в factory. TDD `test_research_tracker.py` (9) GREEN; регресс PASS.
- [x] А-1 (этаж 12) собственные проекты: устойчивый трек прогресса как обозримая сущность — `progress_text()`/`current_research_text()` в research_tracker + блок «МОЙ ТЕКУЩИЙ ПРОЕКТ/ИССЛЕДОВАНИЕ» в обоих промптах. TDD расширен (12) GREEN. Этаж 12 закрыт (А-1+А-2).
- [x] П-3 (этаж 5) Взросление характера: пер-чертовое взросление по накопленному опыту (evidence_count) — `_status_from_strength_ev` (адаптивные пороги ACTIVE↓/weakening↑ на ±0.02 за каждые 3 подтверждения, emerging неизменен, потолки 0.72/0.50) + `_decay_maturity_factor` (зрелые затухают медленнее). Старый `_status_from_strength` = базовые пороги (evidence=0), обратная совместимость. Решение Эдди: пер-чертовое по evidence_count + мягкая адаптация. TDD `test_personality_adulting.py` (6) GREEN + final_regression_suite 7 passed. Осталось: (П-1) более полная модель предпочтений — типы/конфликт, (М-2) полное многошаговое планирование.
- [x] Блок П-1 (этаж 5) подтверждён Эдди как первый. План: `PLANS\2026-09-03-P1a-preferences-threshold.md`.
- [x] П-1a: MIN_CHOICES 6→4 в `ActionPreferenceDetector` (MIN_SHARE 0.75 и `loser_count>0` не тронуты). TDD `test_preference_detector.py` (2 кейса) GREEN + регресс PASS. CHANGELOG записан. Без коммита.
- [x] П-1b: обогащение формата `self_state.preferences` — РЕШЕНИЕ Эдди (03.09): словарь-запись с обратной совместимостью. План: `PLANS\2026-09-03-P1b-preferences-dict-format.md`. Точки: Proposal.meta, preference_label.py, action_preference_detector (task+meta), agent_loop, identity_manager (dict+дедуп по методу), read (prompts/self_concept/current_mind_state/agent). Реализация по TDD. Выполнено 04.09: dict-запись пишется и читается; дополнительно закрыта точка риска claim-валидации dict (self_claim_validator `_extract_compare_text`, claim_engine `_extract_value_text`, predicate_registry `_value_text` вместо `str(dict)`-repr). Тесты: test_preference_dict_format, test_claim_validator_pref_dict (6) GREEN + регресс PASS.
- [x] П-1c: связка preference-контура с реальными «предпочтениями» outbox-подсказками (детектор подсказывает, outbox применяет). Выполнено 04.09: в `agent_loop._process_identity_detectors` при `category=="preference" and identity_result=="accepted"` в outbox уходит сообщение с читаемым label («Заметил своё предпочтение: ...»); `outbox=None` — тихо пропускается. TDD `test_pref_outbox_link.py` (3 кейса: уход в outbox при новом предпочтении, без дубля на повторе, outbox=None не ломает) GREEN + регресс PASS.
- [x] П-1d: модель предпочтений — тип/сила + конфликт с интересами. `identity/preference_model.py` (новый): `preference_type` (action/topic/environment/unknown по маркерам), `strength_of` (share+evidence), `enrich_entry` (type/strength/provenance/first_seen/last_seen), `preference_conflicts` (негатив по теме интереса), `format_preferences_rich`. Запись: identity_manager обогащает dict + освежает last_seen при дедупе. Чтение (prompts 2 / current_mind_state 1 / self_concept_resolver 1) — rich-формат с интересами; agent.py plain (мин. дифф). TDD `test_preference_model.py` (13) GREEN + регресс PASS + final_regression_suite 7 passed + orchestrator_local PASS. ЭТАЖ 5, блок П-1 (взросление характера S-статусами / предпочтения) закрыт.
- [x] П-2 Привычки действий (не только речи): накопление устойчивого паттерна действия → habit-черта через единый lifecycle. Ядро уже было (HabitPatternDetector → evidence → identity_manager → PersonalityLifecycle.promote; подтверждено test_unified_agent_loop/final_regression_suite). 04.09 закрыт остаток «к полноте»: читаемость (привычки показывались как `repeated_action:research`). Добавлен `identity/habit_label.py` (`habit_label`/`format_habits`: dict→label, иначе `repeated_action:SOURCE`→«привык действовать через источник», иначе—как есть; обратная совместимость) + подключён в prompts.py, agent.py (снапшот+промпт), current_mind_state.py. TDD `test_habit_format.py` (6) GREEN + регресс PASS.
- [x] Этаж 11 «Совместная жизнь» — ядро реализовано: `identity/shared_life.py::SharedLife` (наблюдение + LLM-оценка + SHARED_EXPERIENCE-события + build_feed), `identity/shared_appraisal.py::SharedAppraisal` (эмоции по типу активности + интимитет/доверие), интеграция в runtime/factory/self_model. 14 тестов GREEN + регресс PASS. Байт-проверка 8 файлов OK.
- [x] Задача 4 (этаж 9, терминал): интеграция командного контура в инфраструктуру. CommandPolicy+TerminalExecutor подключены: `tool_policy._powershell()` → CommandPolicy; `tool_runner._execute_powershell()` ветка; factory регистрирует инструмент `powershell`. TDD `test_tool_runner_run_command.py` (5) + `test_command_audit.py` (3) GREEN + регресс 35 passed. Задачи 1–4 этажа 9 (терминал) выполнены.

### [30.08 дневная смена] Смена living-tools-world (этажи 9/8) — РЕАЛИЗОВАНА, ревью APPROVE
- [x] CuriosityDirector (evaluate/select_topic/topic_goal/track_action/daily_llm_topic/mark_acted) — ядро.
- [x] Проводка в прод: фабрика (tool_runner/orchestrator/runtime/world_probe/llm.curiosity), tick() с реальными счётчиками + суточной темой, кулдаун ожил.
- [x] Хуки осведомлённости: прямой WEB_SEARCH + _execute_web_search → web; CloudFirstLlm.chat → llm.
- [x] WorldProbe (ctypes) + world_description + WORLD_SNAPSHOT-триггеры (RAM critical, пробуждение) + ensure_world_description (дыра закрыта).
- [x] Финальное ревью ветки — 2 прохода, VERDICT APPROVE (final-review.md в workspace SDD).
- [x] Регресс: 27 юнит-тестов + test_production_runtime + test_decision_revive — PASS.
- [ ] Живая приёмка на проде: суточный прогон PID 39972 (старый код, перезапуск не делается — фича считается вступившей после следующего перезапуска прогона). Критерий спеки: ≥1 исследовательская цель/сутки + WORLD_SNAPSHOT по триггеру.
- [ ] Бэклог: доделать порог «инициатива «проверить мир» как тема» в CuriosityDirector (расширение, не обязательное).
- [ ] Бэклог: тесты на пороги evaluate в связке tick (сейчас юнит, интеграция подтверждена чтением кода).

### [29.08 вечер] Аномалия «вечный IDLE» — ВЫЛЕЧЕНА (TDD, перезапуск на новом коде)
- [x] Диагноз подтверждён: `_last_action_at=None` → `idle_seconds=0` вечно +
      `_next_interest_target()` пуст (цели-интересы COMPLETED).
- [x] Вариант (а): `_last_action_at = datetime.now(timezone.utc)` в `__init__`
      orchestrator (idle растёт от создания процесса).
- [x] Вариант (б): `_next_interest_target` возвращает новый followup-шаблон
      «Найти новые аспекты темы: <интерес>» для COMPLETED-цели (первый
      неиспользованный, карусели нет). Вариант (в) не понадобился.
- [x] Тест `test_decision_revive.py` RED→GREEN + полный регресс рубежа A — PASS.
- [x] Новый ночной прогон перезапущен 29.08 22:26 на этом коде (1440 заново,
      PID 39972, маркер `[22:26:53] NIGHT RUN START (restart)`).
- [x] Наблюдение ЗАКРЫТО по артефактам: первый тик 22:26:57 `decision=
      ACTIVATE_GOAL`, `idle=15` (не заморожен!), далее COMPLETE_GOAL +
      облачные вызовы. Ночью агент спал (ASLEEP, cloud_calls=15). Мотивация
      и цикл работают — «вечный IDLE» вылечен.

### [29.08 ночь → 30.08] Рубеж A «Душа впитывает» — ЗАКРЫТ (приёмка по артефактам)
- [x] Первый сон на новом коде 29.08 23:44:58 (`day_end`) → 23:45:17: DREAM
      + DREAM_INTERPRETATION в memory.db, дневник `diary` trigger=dream,
      снимки души 234458_before / 234517_after.
- [x] Критерий 1 (diff души ≠ пуст): diff keys=6, в т.ч. `emotions.surprise`
      0.0→0.1 (эмоция сна проявилась в душе), `counters.diary` 12→13.
- [x] Критерий 2 (страх сна < страха яви, вес DREAM 0.25): surprise после сна
      0.1 < эмоции яви до сна (joy 0.134, curiosity 0.347, satisfaction 0.362).
- [x] Критерий 3 (0 прямых изменений черт): traits 5/5 до и после, набор id.
- [x] Критерий 4 (провенанс DREAM на каждом артефакте): source_type=DREAM /
      DREAM_INTERPRETATION подтверждён запросом.
- [x] Диагностика раннего DREAM (29.08 16:55, старый код): сон из ритуала
      без полного цикла C4; на новом коде — полный цикл day_end→dream.

### [29.08 ночь] Пре-экзистентный дефект `test_production_runtime` — ЗАКРЫТ 30.08 (вариант а)
- Тест от 19.08 строит `AutonomousRuntime` напрямую без `decision_core`,
  а в `autonomous_runtime.py` с 17:31 (до моих правок) добавлен блок
  `if self.decision_core is not None` — атрибут проставляет фабрика
  (`autonomy_runtime_factory.py:527`). Плюс cp1252 консоль не печатает
  кириллицу (`print(goal)`).
- [x] Выбран вариант (а): `__init__` runtime инициализирует опциональные
  зависимости (`decision_core`/`speech_habits`/`eddie_server`/`outbox`
  = None, фабрика перекрывает). Тест: EXIT=0 (PYTHONIOENCODING=utf-8).
- [x] Регресс затронутого: py_compile OK, test_decision_revive ALL PASS.

### [29.08 ночь] Рубеж A «Душа впитывает»: механизм снов С1–С4 РЕАЛИЗОВАН (TDD, всё PASS)
Мандат Эдди «работай автономно». Дизайн — `docs_engineer\design_rubezh_a_dreams.md`.
- [x] С1 провенанс DREAM (0.25) / DREAM_INTERPRETATION (0.35) — memory/provenance.py.
- [x] С2 `core/dream_processor.py` — жатва→replay→кадры→flash-осмысление→
      apply_reaction (×0.5×0.25)→DREAM+дневник; фолбэк без эмоций; dry-режим.
- [x] С3 `simulation_framework\dream_night.py` — кадры без LLM/движка (CLI +
      `build_night_builder` для контракта night).
- [x] С4 хук `_dream_night()` на входе в SLEEP (autonomous_runtime.py) +
      сборка процессора из агента; флаг `dream_snapshots`.
- [x] Регресс (включая обновлённый test_life_rituals: переход в сон = 2 LLM-вызова).
- [x] ПРИЁМКА В БОЮ ЗАКРЫТА (см. раздел «Рубеж A — ЗАКРЫТ» выше).
- [x] КРИТЕРИЙ РУБЕЖА A (spec, п.12): все 4 пункта подтверждены артефактами
      сна 29.08 23:45 (diff≠пуст; след сна < следа яви; 0 изменений черт;
      провенанс DREAM).

### [28.08] «Доступ к результатам действий» + «судья знает жизнь» (TDD, всё PASS)
Жалоба EddieAI (CONVERSATION #1981/#1986) подтверждена данными и кодом.
Реализовано: `Memory.recent_action_results(limit)` + `Agent._action_results_block`
(блок «РЕЗУЛЬТАТЫ ТВОИХ ДЕЙСТВИЙ» в quick_user_prompt и в полный user_prompt)
и `SemanticJudge` получает `life_context` (лента жизни + результаты действий)
в `judge`/`regenerate` — fabrication оценивается против реальных фактов.
Тесты: test_action_results_block, test_semantic_judge_life_context (RED→GREEN);
регресс decision/жизненного набора — PASS. Файлы: memory/database.py,
core/agent.py, core/semantic_judge.py. Дейностующий ночной прогон PID 30988
работает на коде БЕЗ этиx правок (жалоба касается диалога) — перезапуск
по желанию: «перезапустить ночной на новый код» (ниже).
- [x] Починить REFLECTION-парсинг: корнем был НЕ парсер, а роутинг —
  роль `reflection` вела на zen-deepseek-pro (reasoning-монолог без JSON).
  Живой пробой доказано; роли переназначены на flash (29.08, тест
  test_model_router_reflection). Осталось: живая верификация в проде
  (перезапустить ночной → REFLECTION с lesson, без error).
- [x] Закрыть тест-долги: test_auto_call / test_call_interrupt / test_life_cycle
  (обновлены под актуальный контракт, 3x ALL PASS). Подробности — CHANGELOG 29.08.
- [x] Вшить `VoiceIO.start_interrupt_detector` в голосовой контур (chat_app/
      сервер): `_speak_with_detector` и `_speech_drain_loop` запускают
      детектор на время озвучки в звонке (колбэк `_on_detected_speech`),
      завершают по reap/дренажу. TDD: test_call_interrupt (кейсы 5–6),
      регресс тестов звонка PASS. Подробности — CHANGELOG 30.08.
- [x] Закрыть пре-экзистентный дефект `test_production_runtime`: вариант
      (а) — `__init__` runtime инициализирует опциональные зависимости
      (`decision_core`/`speech_habits`/`eddie_server`/`outbox` = None,
      проставляет фабрика); тест EXIT=0 (PYTHONIOENCODING=utf-8).
- [x] Легаси-артефакт «кириллица в `logs\eddie_night.log` cp1251» —
      ЛОЖНАЯ ТРЕВОГА: файл пишется `encoding="utf-8"` (night_run.log),
      строгая проверка: decode utf-8 OK (1.51M символов, 0 «?»).
      «Кракозябры» — артефакт вывода Get-Content в cp1251-консоли.
- [x] SEMANTIC_VIOLATION/INTERNAL_LEAK за новую серию (прогон с 29.08
      22:26): 0/0 по прод-БД (events id≥2211). REFLECTION — 1 запись
      валидная, без error (рубрика вечернего ритуала, flash-модель,
      парсинг работает). «Плётка» за правдивые результаты ушла.

### [28.08] Контур «Живой жизни» реализован (TDD, всё PASS)
spec+план утверждены; реализованы непрерывность (промпты + лента
событий), воля без «часового» порога (CALL по безделью>=900c) и
ритуалы пробуждения/засыпания. Файлы: memory/database.py,
core/prompts.py, core/agent.py, core/autonomous_runtime.py,
core/decision_core.py; тесты test_life_feed / test_life_prompt_blocks /
test_life_feed_block / test_life_rituals / test_decision_core.
Подробности — CHANGELOG 28.08.
- [x] Диагностика «молчания» ночного прогона (запрос Эдди): карусель
  мёртвой активации (паттерн→ACTIVATE завершённой цели→COMPLETE цикл).
- [x] Фикс карусели (TDD): `_activation_is_dead` + фильтр в паттерн-ветке
  `decide()`, `learn_from_memory()`, `_learn_from_memory_for()`;
  `test_decision_loop_guard.py` ALL OK; регресс decision-тестов PASS.
- [x] Перезапустить ночной прогон `night_run.py --minutes 1440` на коде
  С фиксом карусели: PID 30988 (старт 19:06, чат attached 19:06:21);
  карусель визирована исчезнувшей (тики decision=IDLE при безделье,
  growth cloud_calls только READ_INBOX-активностью, no «бума» times_used).
- [x] Починить pre-existing fail: `test_auto_call.py` (устаревший импорт
  IN_CALL/IDLE из communication.call_engine) — актуализирован (29.08).
- [x] Разобраться с flaky `test_life_cycle.py` (HARD-порог сна 1.0 при
  активной задаче: fatigue 0.85 за ночной час добирает до 1.0 и усыпляет;
  правка входных данных теста 0.80 — см. CHANGELOG 29.08).
- [ ] Проверить в проде: 4 старых паттерна карусели игнорируются логикой
  (cleanup данных не требуется; при желании — разово удалить позже).

### [27.08] «Настоящий звонок» — модель реального телефона
Переписать звонок с «турн-тейкинга» на модель реального телефона
(входящий → решить ответить/отклонить → разговор → завершение любой
стороной) + вариант C (CALL в локальных правилах + стимул «давно не
разговаривали» в контексте EddieAI). Решения Эдди: входящий звонок →
ВСЕГДА через LLM-решение EddieAI; режим разговора — «с собеседником»,
не «с хозяином».
- [x] CallDirector = машина состояний (IDLE/RINGING_IN/RINGING_OUT/
  ACTIVE/ENDED) + константы обратной совместимости; смоук PASS.
- [x] eddie_server.py: _wire_call_director, _pending_incoming_call,
  _user_call_incoming/decide_incoming_call/_user_call_answer/_user_call_reject/
  _user_call_end, initiate_call→start_call_out+broadcast, ветки
  call_ring/answer/reject/end в handle(), seconds_since_last_convo.
- [x] tcp_client.py: send_call, on_call_ring/on_call_status, разбор
  call_ring/call_status.
- [x] ui_chat.py: баннер входящего звонка (ответить/отклонить),
  show_ring_status, set_call_ended, обновлённый set_call_state.
- [x] chat_app.py: _wire_call_director, регистрация on_call_ring/
  on_call_status, _on_call_toggle (call_end при ACTIVE, иначе call_ring in),
  _accept_incoming/_decline_incoming.
- [x] decision_core.py: HANDLE_INCOMING_CALL + ветка incoming_call в
  начале _local_rules + вариант C (CALL при time_since_last_convo>=3600
  и random<0.0005) + import random.
- [x] autonomy_orchestrator.py: _build_state (+incoming_call,
  +time_since_last_convo), _apply_action ветка HANDLE_INCOMING_CALL →
  _handle_incoming_call (LLM-решение через agent.respond, JSON
  {"accept":bool,"reason":str}, фолбэк → принять, → server.decide_incoming_call).
- [x] Проверки: OK_COMPILE_ALL, OK_INTEGRATION (переходы состояний),
  OK_BRANCHES, OK_HANDLE_INCOMING (LLM→CALL_ACCEPTED).
- [x] Перезапуск суточного прогона с новым кодом (решение Эдди «когда
  починим, тогда перезапустим»): PID 29292 остановлен, запущен
  night_run.py --minutes 1440 (новые PID 32356/34264). Лог 18:26:
  «chat attached», «autonomy loop: STARTED», тики идут.
- [ ] Проверить сценарий входящего звонка вживую (Эдди звонит →
  LLM-решение → ответ/отклон).
- [x] Duplex-запуск при звонке: авто-микрофон при ACTIVE в chat_app
  (прослушивание в паузах, отправка распознанной речи EddieAI,
  пауза пока EddieAI отвечает голосом). Компиляция PASS, прогон
  перезапущен (PID 24612). Живая приёмка разговора — на Эдди.
- [x] Звонок-разговор без «30 секунд»: немедленный ответ на
  user_message при ACTIVE (eddie_server, без ожидания тика 15с) +
  надёжность авто-микрофона (is_speaking вместо эвристики, таймаут,
  разговор не рвётся после ответа). Прогон перезапущен (PID 15596).
- [x] VTuber-стек голоса: распознавание faster-whisper small (вместо
  Vosk; модель в models/whisper) + стриминг ответа (cloud_chat_stream
  SSE, первый токен ~1.4с) + respond_call_fast (лёгкий разговорный
  промпт) + озвучка по чанкам (agent_speech_chunk, очередь в chat_app).
  Прогон перезапущен (PID 36456). Живая приёмка — на Эдди.

### [27.08] Быстрый рот Piper + подростковый голос (фундамент duplex-звонка)
Цель: озвучка была ~6с (edge-tts) — неприемлемо для живого голосового
общения. Эдди: «озвучка слишком медленная для этого этапа». Итог:
- [x] Диагноз: задержка в облачном edge-tts (2-5с до первого звука);
  наш PSOLA _boyify быстрый (0.07с).
- [x] Эксперимент Kokoro (kokoro-onnx int8): на нашем CPU 6-8с/фраза и
  БЕЗ русского тембра — ОТКЛОНЁН (см. MEMORY).
- [x] **Piper** (ONNX, onnxruntime): синтез фразы 2.75с = 0.23с;
  с _boyify всего 0.28с (~20x быстрее edge-tts). Локально, бесплатно.
- [x] Голос EddieAI = **12-летний мальчик** (решение Эдди): мужской
  Piper dmitri + PSOLA подъём до TEEN_PITCH_HZ=250 → F0 260 Гц.
  Взросление голоса со временем — ОТЛОЖЕНО Эдди (будет позже).
- [x] model/voice_io.py: _ensure_piper/_synth_piper, _speak_worker на
  Piper, фолбэк edge-tts; обратная совместимость от speak(text).
- [x] Звонок в мессенджер, этап 1: дирижёр turn-taking готов
  (call_engine.py CallDirector + UI-кнопка + перехват прерывания Эдди
  в chat_app.py; юнит-тест и смоук PASS; CHANGELOG 27.08).
- [x] Звонок, этап 2: автопрерывание озвучки при речи собеседника
  (Vosk-стриминг/детекция во время речи EddieAI). Дирижёр теперь
  отмечает EDDIEAI_SPEAKING при старте озвучки в звонке и сбрасывает
  на естественном окончании (reap) — переход EDDIEAI→EDDIE_SPEAKING
  вызывает перехват → stop_speaking. Тест test_call_interrupt PASS.
- [x] Звонок, этап 3: EddieAI САМ решает, когда звонить. Новый вид
  CALL в decision_core + orchestrator → server.initiate_call →
  call_director.start_call + текстовая инициатива (в голосовом режиме
  озвучивается). Защита от спама: не пере-звонок, если уже в звонке;
  cooldown ~15 мин. Регистрация self._call на сервере в chat_app.
  Тест test_auto_call PASS.
- [x] Звонок, этап 4: детекция окончания речи собеседника. Детектор
  двухфазный: on_interrupt (Эдди начал → перехват, этап 2) и
  on_speech_end (пауза ≥0.9с после установленной речи → сброс
  EDDIE_SPEAKING → IN_CALL, чтобы EddieAI снова мог говорить).
  При перехвате детектор НЕ гасится (ждёт окончания), reap сбрасывает
  его только в не-прерванном случае. Обратная совместимость:
  без on_speech_end поведение этапа 2 сохраняется. Тест
  test_call_interrupt (кейсы 6-7) PASS. Duplex-замыкание готово.

### [27.08] Разметка собственных выводов в контексте ответа
EddieAI теперь помечает собственные выводы в обычном диалоге как
«моё рассуждение, не объективный факт»:
- [x] SelfConclusionStore.search_conclusions(): каждый вывод форматируется
  с пометкой [ВЫВОД EddieAI, уверенность X; основание: ...] вместо
  голой строки «- topic: вывod».
- [x] agent.py: заголовок блока в промпте уточнён на «МОИ ВЫВОДЫ
  (мои собственные рассуждения и предположения, НЕ объективные факты)».
  Цель: модель в любом диалоге отделяет своё рассуждение
  (с уверенностью/обоснованием) от объективного факта. Проверка
  формата PASS; обычные воспоминания (search_relevant) по-прежнему
  исключают SELF_OUTPUT и метят говорящего.

### [НОВОЕ 26.08 ночь, РУБЕЖ] Локальное ядро решений + LLM как редкий генератор
Цель Эдди: модель вызывается ТОЛЬКО для формирования НОВЫХ паттернов
действий (как у людей — учимся, а не думаем над каждым действием).
Архитектура: локальное ядро (бесплатно, 24/7, правила/КМА) решает
рутину; LLM-гейт только на новизну/генерацию. Убирает 5-мин интервал
и делает «всегда активен» реальностью без бюджета.
- Дизайн: SPECS\2026-08-26-local-decision-core-design.md ✅
- План: PLANS\2026-08-26-local-decision-core.md ✅
- [x] РЕАЛИЗАЦИЯ (свежая сессия, задачи 0-6): core/situation.py,
  таблица situation_patterns, core/decision_core.py (decide/learn),
  интеграция в orchestrator+factory, обучение из памяти. Тесты PASS.
  Детали — CHANGELOG 26.08.
- [x] Задача 7 ЖИВАЯ/НОЧНАЯ ПРОВЕРКА — УБРАНА ИЗ ПЛАНА решением Эдди
  (26.08). Ядро принято по юнит-тестам и коротким живым прогонам
  (2 мин: 0 облачных вызовов в рутине, паттерн из памяти). Дальнейшие
  длинные прогоны не планируются.
- [x] Связь «паттерн ↔ привычка»: DecisionCore.consolidate_habits()
  (устойчивый паттерн → habit-evidence DECISION_PATTERN → lifecycle).
  План PLANS\2026-08-26-pattern-habit-link.md. Тест test_pattern_habit PASS.
- [x] Обратная связь «привычка → паттерн»: consolidate_habits хранит
  kind в value привычки (situation_action:<key>:::<kind>);
  DecisionCore._rebuild_pattern_from_habit() восстанавливает паттерн
  из habit-черты при новизне (без LLM). Тесты PASS.
- [x] Интеграция профиля речи в вербализатор (МЯГКО, дополнение промпта):
  prompt_builder.build_verbalizer_system_prompt(speech_profile=...) +
  agent._speech_profile() + _respond_core. Тест test_verbalizer_speech PASS.
  Принцип: почерк (не жёсткий шаблон), вербализатор может игнорировать.
- [x] ЭМОЦИИ (завершение блока, 26.08): decay в диалоге; Д4 закрыт
  (валидатор аффекта); аффект в ядре решений (фрустрация подавляет
  новые начинания); расширение appraise_interaction (больше обид/похвал
  + противоречия во входящем). Тесты test_affect_d4/test_decision_affect/
  test_appraisal_social PASS.
- [x] ОБУЧАЕМЫЕ маркеры — единый механизм learned_markers
  (таблица + learned_bump/get). Подключены социальные маркеры (praise/
  insult/contradiction) в AppraisalEngine. Тест test_appraisal_learning PASS.
- [x] БЭКЛОГ (проверено и закрыто 27.08): подключить остальные фильтры
  к learned_markers — уже реализовано ранними работами:
  - behavioral_validator.py: фильтры identity_denial/role_inversion/
    fabricated_activity/absolute уже на learned_markers (категории
    identity_denial/role_inversion/fabricated_activity/absolute),
    обучение в _hits → _learn_markers;
  - dialogue_memory.py: маркеры деградации RAM_REFUSAL на learned_markers
    (категория degradation), обучение в record_agent_answer →
    _learn_degradation;
  - appraisal_engine.py: социальные маркеры (praise/insult/contradiction)
    на learned_markers.
  Осталось из формулировки только «help»-фильтр — отдельного такого
  фильтра в коде нет (не существует), фактически покрыт identity_denial.
  Проверка вызовов обучения: agent.py:5884, dialogue_memory.py:124,
  behavioral_validator.py:60/68, appraisal_engine.py:560/603/653.
  Реальный объём бэклога исчерпан; новых точек подключения нет.

### [НОВОЕ 26.08 сессия] Аудит 170 файлов + расходы flash

- [x] Анализ расходов flash-сессии: реальный ~$0.75 за ~55 ходов
  (контекст рос 10K→180K). Ранее $0.40 были занижены.
- [x] Claude-модели: все HTTP 500 (opus-4-5/4-6, sonnet-4-5/4-6).
  Эдди подтвердил opus-4-5 работала ранее — 500 временный.
- [x] opencode → big-pickle (решение Эдди: flash ~$0.75/сессию
  дорого для рутины). Flash доступен вручную /models.
- [x] Запуск полного аудита 170 файлов на flash (57 батчей,
  ~$0.08-0.15). Audit_runner.py исправлен (urllib баг).
- [x] Аудит завершён: 57/57, $0.088, 0 ошибок, 722 КБ отчётов.
- [x] Исправлены 5 CRITICAL-проблем из аудита (eddie_server,
  chat_voice_probe, benchmark, self_consistency, manager+evidence).
- [x] Исправлены HIGH-проблемы пакет 1: goal_generator (3),
  self_conclusion_state (2), self_concept_resolver (1),
  personality_reflection (3), promotion (1), main (1),
  night_run (4 хардкода) — 15 фиксов, 7 файлов.
- [x] Исправлены HIGH-проблемы пакет 2: web_executor (SSRF),
  llm_access (ollama crash), main (agent.close safety),
  night_run (runtime safety + ollama restore),
  identity_manager (list mutation) — 5 фиксов, 5 файлов.
- [x] Новое правило AGENTS.md: выбор модели для задачи (модель +
  стоимость перед сложной работой).

### [НОВОЕ 26.08 утро] Zen оплачен — финальная настройка облака

- [x] Проверить Zen с кредитами: deepseek-v4-flash/pro, qwen3.6-plus,
  kimi-k3 отвечают. claude-haiku-4-5/gpt-5.4-mini/gemini-* — 500.
- [x] model_orchestrator.py: CLOUD_PROVIDERS обновлены (flash/pro/
  qwen3.6-plus/kimi-k3 + GLM резерв).
- [x] Уши: Vosk small-ru (локальный STT) основным в voice_repl.py,
  E2E проверено.
- [x] Рот: ru-RU-DmitryNeural (мужской) вместо SvetlanaNeural.
- [x] OpenCode конфиг: модель = opencode/big-pickle (бесплатно),
  flash в whitelist для ручного переключения (/models).
- [x] Cloud_bridge (прямой тест): 5/6 ролей ходят на Zen.
- [x] Проверочная ночная сессия 10 мин: автономия IDLE, облако не
  вызывалось (бюджет 300/300).
- [x] Разобрать IDLE-автономию: корень найден — COMPLETED цели не
  ре-активировались, followup-генерация добавлена в orchestrator.
- [x] Discovery-мотивация: MotivationEngine извлекает темы из
  памяти (Counter + stopwords), генерирует кандидатов.
- [x] Orchestrator.decide(): автономные решения из idle
  (discovery / reflection / ask Eddie). Байпас GoalReview.
- [x] night_run.py: убран CLOUD_BUDGET=300, оставлен счётчик.
- [x] Outbox: файл-почта reports/outbox.md.
  Интегрирован в orchestrator + agent_loop + factory.
- [x] EddieAI Chat: приложение общения (communication/).
  TCP + tray + balloon + voice + симметричная инициатива.
- [ ] Д. Голос: спонтанное голосовое сообщение.
- [x] Ollama из автозагрузки убрана (Startup\Ollama.lnk), процессы 0.
- [x] self_conclusions: НЕ SQLite-таблица, а JSON в self_state
  (SelfConclusionStore). Миграция не нужна.
- [x] night_consolidation.py:24 — хардкод C:\EddieAI заменён на
  Path(__file__).resolve().parent.
- [~] test_eddie.py: файл не существует (удалён или не создан).
  Юнит-тесты проекта распределены по test_*.py (24 файла).

### [НОВОЕ 25.08 день, решение Эдди] Сессионный режим автономии вместо постоянного

Решение: EddieAI запускается ТОЛЬКО в проверочных сессиях
(python night_run.py --minutes 30) пока не будут закрыты Д2/Д4
(Д2 переведён в отложенный риск 27.08 — мозг на облаке Zen)
и подтверждено качество research. Фоновые процессы остановлены.
Критерии перехода к ПОСТОЯННОМУ режиму:
- [ ] Сессия 30+ мин без петлей (одна задача не повторяется 3+ раз)
- [ ] Research даёт содержательные результаты (не пустые OK)
- [ ] Д4: валидатор аффекта не шумит на каждый ответ
- [ ] Бюджет расходуется на разнообразные осмысленные шаги
Запуск проверочной сессии: python night_run.py --minutes 30
(лог: logs\eddie_night.log; watchdog при длинных сессиях).

### [ЗАКРЫТО 25.08 день] Три задачи: речь / планы / уши

- [x] Полировка речи: фильтр коротких вводов, маркеры деградации
  расширенные (self-model утечки больше не пишутся), правила 13–14
  вербализатора.
- [x] Планы/петля: корень — execute() cloud ветка только при fast=True;
  THINK-действия автономии всегда падали в локаль. Deep-ветка +
  roles "deep" + мотивация из self_state interests → 3 цели ACTIVATED,
  adaptive planner через 70B пересмотрел план и вставил реальную
  статью (URL HTTP 200), шаг COMPLETED. Петля сломана.
- [x] Уши: hf-whisper-large-v3 первым в STT_PROVIDERS (raw WAV режим),
  протестировано HTTP 200. Голосовой режим снова рабочий полностью.

### [НОВОЕ 25.08 день] Автономный режим: полный запуск — работает

- [x] night_run.py: скрытый полный запуск (Agent + AutonomyRuntime +
  бюджет облака + мост ollama.chat→облако для 7 зависимых подсистем).
- [x] motivation.py: интересы self_state → активные цели (3 шт
  ACTIVATED с планами через облако).
- [x] Петля зацикливания сломана: execute() deep-ветка для
  fast=False задач.
- [x] watchdog.py: авторестарт каждую минуту.
- [x] ДНЕВНОЙ РЕФАКТОРИНГ: модули на orchestrator — DONE (27.08).
  Проверкой установлено: 7 модулей УЖЕ переведены на единый
  CloudFirstLlm (облако-первое) — adaptive_planner, goal_plan_generator,
  personality_reflection, reflection_engine, self_reflection,
  self_interpretation, decision_core, semantic_judge. Единственный
  остаток — reflection_cycle.run() звал прямой локальный ollama без
  облака; приведён к тому же паттерну (облако-первый + локальный
  фолбэк), убрана зависимость от глобального моста night_run.
  py_compile OK, test_self_state_seed PASS.
- [x] Разобрать качество research-результатов — DONE (диагностика
  27.08, живые вызовы): WebExecutor.search (DDG HTML) → SourceEvaluator
  → read_page топ-3 → ExternalRecorder → SelfInterpreter. Находит
  релевантное и по-английски, и по-русски; read_page чистый текст
  (+Wikipedia REST); SSRF работает. Единственное ограничение:
  нестабильность DDG HTML (иногда 0 результатов/капча при работающем
  источнике). Кандидат на правку (по согласованию): ретрай search при
  пустом/капче-результате.

### [ЗАКРЫТО 25.08 утро] Д7: ролевые границы — ЗАКРЫТ

- [x] Симптом: EddieAI присваивал проблемы Эдди («я не могу зайти
  в свой аккаунт ВК… у меня нету этого говна») и копировал грубость.
- [x] ФИКС: блок «ГРАНИЦЫ ЛИЧНОСТИ» в вербализационном промпте
  (agent.py): чужие проблемы ≠ свои; у EddieAI нет тела/телефона/
  соцсетей; не копировать лексику.
- [x] Тест boundary_test PASS: эмпатия без присвоения, совет дан,
  тон свой. Боевой процесс перезапущен.

### [НОВОЕ 25-26.08 ночь] Речевой аппарат + санитария памяти — сделано, статусы дефектов

- [x] Д1 ЗАКРЫТ: фильтр _is_degradation_answer (7 маркеров) в
  agent.py — отказы не пишутся в память; 23 мусорных записи удалено,
  3 бэкапа сняты. Осталось 113 честных self-воспоминаний.
- [x] Д5 ЗАКРЫТ: вербализационный промпт стал основным режимом —
  запрет выхода из роли/сценария/мета-комментариев.
- [x] Fallback-механика: при отказе локали облако подхватывает
  (roles += "fallback" у обоих HF). Проверено живьём.
- [~] Д2 (ПЕРЕВЕДЁН В ОТЛОЖЕННЫЙ РИСК 27.08): зацикленность 8B —
  корень был у локальной 8B на 8 ГБ машине. Теперь мозг на облаке Zen
  (deepseek-v4-flash), локальная 8B — только редкий офлайн-фолбэк
  (залипание смягчено промптом). ВОЗМОЖНАЯ проблема, если когда-нибудь
  откажемся от облака: тогда вернуть 8B/14B-локаль (70B на рефлексию
  и/или расширение памяти до 16 ГБ для локальных моделей побольше).
- [x] Д4 ЗАКРЫТ (диагностика 27.08): AFFECTIVE_BEHAVIOR_VIOLATION
  CONFLICTED_NO_NEXT_STEP. Корень шума: violation писался в память ДО
  проверки значимости (мусор на каждый ответ), каскад исторических
  Д1/Д2 (облачный отказ + зацикленность 8B) читался валидатором как
  конфликт. Фиксы уже в коде: запись в память только после
  should_repair (agent.py:2475), вопрос в CONFLICTED только при
  question_tendency>=0.85, severity 0.45→0.30. test_affect_d4.py PASS.
  Ожидание живой сверки отклика — при следующем полном прогоне.
- [ ] Уши: аудио-транскрипция через HF-whisper.

### [НОВОЕ 25.08 ночь, 02:15] Дефекты первого живого диалога Эдди↔EddieAI (монитор базы)

Контекст: ночной текстовый диалог main.py через HF Llama-3.1-8B;
мониторинг событий памяти в реальном времени (#360–396).

- [ ] **Д1 (критично): отказ-текст отравляет личность.** Служебное
  «Я сейчас не могу думать…» записалось как CONVERSATION/self
  (#368, #379) → EddieAI искренне считает себя немощным и
  транслирует это (#379). ФИКС: в agent.py перед записью ответа
  в память распознавать служебный отказ (error=insufficient_ram)
  → либо не писать, либо source=SYSTEM + пометка. Плюс чистка
  уже попавших строк из прод-базы (аккуратно, бэкап!).
- [ ] **Д2: зацикленность 8B-модели.** «Понимание устройства мира
  и развитие способностей» повторяется почти в каждом ответе —
  Llama-3.1-8B цепляется за контекст. Варианты: Qwen3-14B с
  подавлением thinking (/no_think в промпте), Llama-3.3-70B-Instruct
  (дороже), или оставить 8B для болтовни + 14B для рефлексии.
- [ ] **Д3: утечка служебных фраз в речь** (#390 «противоречит моей
  текущей self-model»). Валидационная лексика не должна звучать от
  лица EddieAI пользователю.
- [ ] **Д4: AFFECTIVE_BEHAVIOR_VIOLATION CONFLICTED_NO_NEXT_STEP 0.45
  почти на каждый ответ** — выяснить причину (вероятно каскад Д1/Д2:
  противоречивые отказы+повторы читаются валидатором как конфликт).
- [x] Позитив: identity_repair самопочинка сработала живьём (#386→387),
  диалог тематически связный, память пишется, валидаторы активны.

### [ЗАКРЫТО 25.08 ночь] EddieAI живой на бесплатном облаке; P0-d закрыт живьём

- [x] HF Router встроен (Qwen3-14B, $0.10/мес free), hf.key от Эдди
  работает: models 131 шт, чат 200 по-русски.
- [x] ЖИВОЙ promote P0-d: свидетельства → кандидат → LLM promote →
  трейт ACTIVE в self_state. ПОЛНОСТЬЮ ЗАКРЫТО.
- [x] Живой диалог: осмысленные ответы в характере.
- [x] guard_test ALL PASS 8/8; CHANGELOG/PROJECT_STATE обновлены;
  бюджет 0₽ соблюдён.

### Остатки (не блокируют)
- [ ] siliconflow оживёт при пополнении/верификации (когда будут
  деньги — $2 хватит на месяцы топовых моделей).
- [ ] glm.key (z.ai) активируется сам при восстановлении маршрутов
  (сейчас TLS до хоста режется).
- [ ] Уши: аудио-транскрипция через HF (whisper) вместо мёртвых
  voxtral/groq-whisper — следующая сессия.
- [ ] Расходы HF мониторить: $0.10/мес ≈ 100+ диалогов; при нехватке
  перейти на Qwen3-8B или просить PRO ($9).

### [НОВОЕ 25.08 ночь, финал] Новая цепочка облаков встроена — ждёт ключей Эдди

- [x] ВЫПОЛНЕНО (исследование по поручению Эдди): независимые отзывы +
  LMArena — GigaChat развенчан, GLM/Qwen/DeepSeek сильнее. Метод:
  параллельные суб-агенты через скилл superpowers (закреплено в
  AGENTS.md).
- [x] ВЫПОЛНЕНО (отмашка «да, давай»): CLOUD_PROVIDERS =
  siliconflow(Qwen3-8B free) → glm(z.ai flash) → deepseek(резерв) →
  mistral → ... ; extra_payload механика; тесты ALL PASS 7/7.
- [ ] ЖДЁТ КЛЮЧЕЙ: siliconflow.key (cloud.siliconflow.cn, email),
  glm.key (z.ai), deepseek.key — строкой в ~/.eddieai_secrets/.
  После первого ключа: проверить /v1/models siliconflow на актуальные
  бесплатные id, живой promote-цикл P0-d, живой диалог.
- [ ] СЛЕДУЮЩИЙ ШАГ УШЕЙ: аудио-транскрипция SiliconFlow вместо
  мёртвых voxtral/groq-whisper.

### [НОВОЕ 25.08 ночь, продолжение] P0-d контур рефлексии: FULL PASS; решения за Эдди

- [x] ВЫПОЛНЕНО (автономная фаза): dialog_local_test — guard/даунгрейд
  OK; вскрыт дефект «пустой ответ при отказе мозга» → agent.py:_generate
  теперь возвращает честное сообщение. PASS.
- [x] ВЫПОЛНЕНО: закрыта дыра — run_snapshot звал ollama мимо
  RAM-guard → вставлена проверка, перенос решений при нехватке RAM.
- [x] ВЫПОЛНЕНО (одобрено Эдди): фикс f-string в run_snapshot
  (неэкранированные { } ломали метод на первом непустом кандидате —
  весь P0-d был фактически мёртв).
- [x] ВЫПОЛНЕНО: refl_candidate_test FULL PASS — детектор → snapshot →
  cycle → PromotionEngine → трейт ACTIVE → self_state. Рецепт порогов
  в MEMORY. Мок только на _cloud_chat.
- [ ] ОСТАЛОСЬ по P0-d: живой прогон цикла с настоящим LLM (ждёт ключа
  облака или ≥3.6 ГБ RAM).
- [ ] РЕШЕНИЕ ЗА ЭДДИ: ключи провайдеров НИГДЕ не сохранены (проверены
  secrets/env/opencode.jsonc — там только gigachat-local для opencode,
  TestSprite MCP и mistral.key). Если Groq-ключ создавался на сайте —
  сохранить строкой в C:\Users\keris\.eddieai_secrets\groq.key.

### [НОВОЕ 25.08 ночь] Авария голосового сеанса (402 Mistral) — устойчивость готова, решения за Эдди

- [x] ВЫПОЛНЕНО: диагностика (402 на всём Mistral API; каскад
  молчаливых фолбэков whisper+qwen → своп-ад на 8 ГБ машине).
  Сеанс остановлен корректно, RAM восстановлена (2.7 ГБ свободно).
- [x] ВЫПОЛНЕНО: защита — `_cloud_chat` печатает причину отказа +
  cooldown (биллинг 401/402/403 → 30 мин); RAM-guard в execute()
  (пороги qwen 3.6 / phi4-mini 2.6 ГБ, даунгрейд, честный
  ERROR=insufficient_ram); guard в voice_repl.get_whisper
  (2.5 ГБ порог, medium→small). guard_test.py PASS,
  p0b_chain PASS, UTF-8 чисто.
- [x] ВЫПОЛНЕНО 25.08 ночь (решение Эдди «несколько облачных — резервы»):
  failover-цепочка CLOUD_PROVIDERS mistral→groq→openrouter→gemini
  (ключ = файл в ~/.eddieai_secrets, свой cooldown у каждого);
  уши: voxtral→groq-whisper. Тесты PASS. ЖДЁТ КЛЮЧЕЙ Эдди:
  groq.key / openrouter.key / gemini.key (инструкция в CHANGELOG).
- [ ] РЕШЕНИЕ ЗА ЭДДИ: судьба Mistral-аккаунта (console.mistral.ai →
  Billing: пополнить / ждать месячного сброса Free-кредитов ~$10/мес /
  новый ключ).
- [ ] Повторный живой голосовой сеанс — после решения по мозгу.

### [ЗАКРЫТО 24.08 ~16:00] Восстановление core/agent.py после git checkout
Установлен снапшот 77a08896 (6040 строк, состояние 13:46:17) из
shadow-git opencode. Все проверки PASS. Бэкапы:
C:\EddieAI\agent_py_recovery_2026-08-24\. Детали — CHANGELOG.
Остаток: файл снова незакоммичен поверх HEAD (усиливает проблему №2
реестра PROJECT_STATE — решение о коммите за Эдди).

### РУБЕЖ «ПЕРВОЕ СОБСТВЕННОЕ ДЕЙСТВИЕ» (утверждён Эдди 23.08)
Схема: «ядро решает — модель только вербализует» (LLM = орган речи).
- [x] R0 предохранители — ЗАКРЫТ 23.08 день (см. CHANGELOG):
      таймаут LLM 600с, атомарный self_state+бэкап, keep_alive "15m",
      user_markers guard'а, живые промпт-строки/события agent.py,
      reason agent_loop.
- [x] R1 канал действия ядра: меню возможностей мира (bridge) →
      action_selector выбирает → вербализация озвучивает выбранное;
      ActionObserver сверяет текст с действием; журнал source=core_selector.
      [27.08: закрыт; расширен на все деятельности (move + activity),
      SPECS: RUBEZH_R1_full_volition_2026-08-27.md; подробности CHANGELOG;
      физика DO_VERBS — осознанно вне объёма: отдельный этап]
- [ ] R2 «Проба воли»: сценарий volition_probe (~60–90 вирт-минут,
      точки выбора без директив), смоук без LLM + 3 прогона с LLM
      (ночь, RAM!). PASS: ≥1 core_selector действие, последствие в мире,
      возврат наблюдением, сдвиг appraisal, запись в память, 2/3 прогона.
      [27.08: решение Эдди «если надо — делай, если нет — пофиг, всё равно
      запустим на полные 24ч». Отдельного сценария volition_probe НЕТ
      (проверено: все реальные сценарии или с принудительной директивой,
      или первый день нового города). R2-проверка воли ПЕРЕНОСИТСЯ на
      суточный 24ч-запуск: кандидат — first_day_new_city (86400с, БЕЗ
      принудительных директив, has_directive=False, реальные точки
      выбора move+activity; сборка проверена). Анализ — готовым
      analyze_volition_night.py (критерий source==core_selector И
      (location_changed ИЛИ activity_declared), без фраз). Отдельные
      дорогие LLM-прогоны сейчас НЕ запущены (экономия квоты).]
- [ ] После R2: A/B вербализаторов phi4-mini vs qwen3.5:4b.
- [x] R3 режимы жизни (сон/пробуждение): watchdog RAM/CPU, тики
      состояния без LLM, авто-выгрузка модели. Фундамент 24/7 + майн.
      [27.08 (решение «R3+R2, потом 24h»): ЧАСТИЧНО ЗАКРЫТ — watchdog
      RAM в 24/7-цикле. new core/resource_watchdog.py (ctypes win32,
      без psutil; enabled=False опц-ин; critical<700МБ/low<1024МБ, probe
      30с, hold-off 60с) встроен в AutonomousRuntime.tick() (при
      should_throttle() -> THROTTLED, LLM-тик пропущен, жизнь уже тикнула
      без LLM); проброс в фабрику (resource_watchdog=None); включён в
      night_run.py. «Сон без LLM» и «тик без LLM» подтверждены уже-
      существующими (is_asleep()/life_cycle.update()). Авто-выгрузка
      локальной модели НЕ делалась (CloudFirstLlm ленив — выгрузка
      имплицитна; LLM-интеграцию не трогаем). Остаток: watchdog CPU +
      отдельный watchdog_life.py (вариант C) — опционально, отложено]
- [ ] После R3: вечерний СУТОЧНЫЙ запуск 24 ч (после R2-минпрогонов).

Смена (вечер/ночь 22.08, соло, мандат «работай сам») — промежуточное
состояние; визуальная приёмка скринов за Эдди
(%TEMP%\opencode\ui_beauty_pass\, 8 PNG).

1. [ЗАКРЫТО 22.08 ночь] Музыка: render.log (OK/FAIL+SWAP),
   ротация вариантов VARIANT_ROTATION 90 c. Живой прогон
   truancy_morning PASS: липкий tension подтверждён, ротация каждые
   ~91 c, рендеры 479–506 мс, ошибок нет, плеер всегда один.
   Приёмка звука Эдди пройдена. Детали — CHANGELOG 22.08 ночь.
2. [HIGH] «UI Beauty Pass»: сделано — чиптюн-звуки v3, анимационный
   пакет, гигиена UI (стиль скроллбаров clam, русские имена служебных
   типов без дублей на трёх лентах, форматированная мини-погода мира;
   текст-скан 8 вкладок: 0 дефектов). ОСТАЛОСЬ — мёртвая зона сетки
   «Мира», красота-проход карты поверх схемы (рефы ..\рефы\, методика
   в скилле refy-dizayn), визуальная приёмка Эдди.
3. [pending] Ночной прогон truancy_morning с LLM — ПОСЛЕ починки
   музыки и по готовности Эдди: гашу лишнее → qwen3.5:4b → прогон →
   отчёт → стек СТОП. Браузер закрыть (RAM 8 ГБ).
4. [ЗАЯВЛЕНО Эдди, следующий фронт] Юзабилити-проход дашборда:
   удобство и интуитивная понятность интерфейса (навигация,
   очевидность действий, подсказки). В этот час не влезает — учесть
   при планировании следующей смены после Beauty Pass.

## Проверки перед сдачей смены

- [x] Байт-проверка правленых файлов: UTF-8 no BOM, нет «?»-литералов
      и двойного перекодирования (live.py, sounds.py PASS).
- [x] py_compile + смоук рендера всех 8 вкладок PASS (скрины).
- [ ] Демо-окно живо и снят скрин PrintWindow (артефакт) — сняты
      8 табовых скринов смоук-скриптом; демо погашено.
- [x] Процессов ollama/llama-server: 0 (не запускались; warm-up
      смоука подключиться не смог — это норма).

---

[АРХИВ]
- [АРХИВ 22.08] BOM в dashboard/live.py — ОЧИЩЕН решением пользователя;
  бэкап live.py.before_bom_clean.bak, compile/import/байт-чек зелёные.
- [АРХИВ 22.08] HUD-статусбар + лента событий — выполнено, проверено
  скрином и смоук-тестами (375 объектов канвы).
- [АРХИВ 22.08] Музыка v2 — выполнено; бесшовный луп подтверждён
  прослушиванием логики wrap-add; плеер детач-процесс (учитывать при
  уборке: убивать и его).
- [АРХИВ 22.08] Этап А (обогащение карты) — выполнено; инцидент
  NameError rw в _draw_trees найден и исправлен, смоук зелёный.
- [АРХИВ 22.08] Этап Б (сайдбар) — выполнено; двойная навигация и
  потеря self.content найдены и исправлены, скрин подтверждает.
- [АРХИВ 22.08] Быстрые победы В — стили кнопок и шрифт внесены,
  компиляция и импорт зелёные.


## Очередь P1-P6 «слова = дело» (согласована Эдди 24.08.2026)

- [x] P1 few-shot честности: блок «ЧЕСТНОСТЬ» в VERBALIZER_BASE
      (prompt_builder): примеры честного тона + запрет выдумок биографии.
- [x] P3 память диалога limit 3 -> 6 (agent.py dialogue_state.render(limit=6)).
- [x] P5 наполнить self_state из seed: interests уже были; добавлены
      честные seed-убеждения (beliefs) + наполнение при пустом.
- [x] P4 разговорные цели -> GoalManager: закрыто как часть P0-b
      (_capture_goal_claim: markers -> proposal_type=goal -> evaluate).
- [x] P2 семантический судья ответа: core/semantic_judge.py
      (уклонение/фабрикация/ок через LLM), подключён к агенту, при issue
      пишет SEMANTIC_VIOLATION. Авто-ремонт по вердикту — следующий шаг.
      Тест test_semantic_judge PASS.
- [x] P6 снимки души до/после сессии: identity/soul_snapshot.py
      интегрирован в night_run (before/after + diff в лог).

Открытый вопрос: судья на Mistral (качество, лимиты) или qwen (безлимит,
медленнее). [P2 — оставшийся пункт контура честности]


## Аффект в голосе (урок втуберов №2; в очередь решением Эдди 24.08.2026)

- [x] Связать affect из self_state с параметрами рта z3-конвейера
      (PSOLA высота/темп, DSP): настроение должно звучать, а не только
      писаться. ВЫПОЛНЕНО 27.08: communication/voice_io.py —
      emotions_to_mood() (эмоции → target_pitch_hz/tempo_ratio/
      brighten_db/drive) + mood_from_agent(); VoiceIO.speak(text, mood)
      прокидывает настроение в PSOLA-обработку (выше при радости,
      ниже при грусти, темп по arousal). Подключено в eddie.py
      (_run_voice/_run_mixed) и chat_app.py (_show_initiative/
      _show_reply). Обратная совместимость: speak(text) работает без
      mood (дефолт ≈ прежнее поведение).
      Детали: docs_engineer\LESSONS_VTUBERS.md.


## МЕХАНИЗМ СНОВ (утверждено Эдди 25.08 ночь; план согласован)

Статус: ЗАКРЫТ (реализовано 29.08 С1–С4, решение Эдди по модели — облачный
flash; дизайн в design_rubezh_a_dreams.md; приёмка в бою — 30.08 по сну
29.08 23:45, см. раздел «Рубеж A — ЗАКРЫТ» выше).
Сон = путь рубежа A «Душа впитывает» (P0-a эмоции + P0-c следы
мышления). Форма: A→B гибрид — replay дня + ассоциативная склейка.

- [x] С1. Провенанс сна: memory/provenance.py += DREAM (вес 0.25),
      DREAM_INTERPRETATION (0.35). Сделано; тест test_provenance_dream.py.
- [x] С2. Ядро лёгких снов: core/dream_processor.py — жатва (жизнь +
      результаты действий) → replay → ассоциативные кадры (детерминизм
      по rng, лимит повторов 3) → осмысление flash (strict JSON, фолбэк
      без эмоций) → apply_reaction (source=DREAM, дельта ×0.5 ×0.25) →
      записи DREAM (0.25) + DREAM_INTERPRETATION (0.35) + PersonalDiary
      («Сегодня мне снилось...») → снимки души (опция). Тест: 7 кейсов.
- [x] С3. Мировые сны: simulation_framework\dream_night.py —
      генератор кадров БЕЗ LLM/SimulationRuntime (CLI + build_night_builder
      для контракта night). Проверен: 4 кадра, детерминизм по seed.
- [x] С4. Интеграция в сутки (R3): переход в SLEEP вызывает _dream_night()
      после вечернего ритуала (autonomous_runtime.py). Подтверждено в бою
      29.08 23:45 (сон тих, без действий).
- [x] ПРИЁМКА В БОЮ ЗАКРЫТА: события DREAM/DREAM_INTERPRETATION в прод-БД,
      запись в дневнике (trigger=dream), diff души (keys=6), сон тих и
      без действий.
- [x] КРИТЕРИЙ РУБЕЖА A: diff души ≠ пуст; страх от сна < страха от яви;
      0 прямых изменений черт личности от снов.

Правила безопасности: source=DREAM обязателен на каждом артефакте
сна; вес evidence 0.25 против 1.0 у яви; запрет менять черты
напрямую (только proposal низкого давления); лимит повторов одного
сюжета за ночь (урок токсичной спирали 13 побегов). Эмоции сна —
легитимный apply_reaction, черты в снах НЕ трогаются.


## ОЧЕРЕДЬ РУБЕЖЕЙ (карта после снов; согласована 25.08 ночь)

[30.08 ночь, решение Эдди «закрыть этажи, чтобы подниматься выше»:
нижние контуры этажей 5–14 закрыты по артефактам; недоделки — в бэклогах
ROADMAP. Рубежи A→B→C — это проверки, после которых поднимаемся на
этаж 13 «Саморазвитие» (блокеры: этаж 9 инструменты в проде, этаж 8
состояние ПК).]

- [x] Рубеж A «Душа впитывает» = закрыт 30.08: критерии снов (см. выше)
      подтверждены артефактами сна 29.08 23:45 (diff души ≠ пуст на
      первом же полном цикле C4; остальные 3 критерия тоже PASS).
- [x] Рубеж B «Живёт сутки»: R3 сон/бодрствование, тики состояния
      без LLM, watchdog RAM/CPU, авто-выгрузка модели, рестарт
      llama-воркера по расписанию (P2-b аудита). PASS: первые
      непрерывные сутки в песочнице без человека, утром дневник +
      diff души.
      [ЗАКРЫТ ПРИЁМКОЙ 30.08 22:27: суточный прогон (PID 39972)
      финишировал штатно (NIGHT RUN END + soul diff). test_rubezh_b.py
      — ALL PASS 9/9: прогон до END, консолидация без ошибки
      (44 события, выводов 3), облачных вызовов 19 (≤40), watchdog без
      THROTTLED, LIFE_CYCLE=4, ритуалы morning=1/evening=2, soul diff
      не пуст. R3/ритуалы/тики-без-LLM/watchdog RAM подтверждены в бое.
      Остаток на решение Эдди: watchdog CPU + P2-b llama-воркера
      (N/A в облачном режиме — текущий мозг облако Zen).]
- [ ] Рубеж C «Голос в сутках»: неблокирующий голосовой REPL
      (слушает во время генерации), семантический судья P1-b,
      периодические снимки P6. PASS: разговор в любой момент суток,
      0 фабрикаций за сутки. Фундамент — задачи Т1–Т2 ниже.


## ЕДИНЫЙ ИНТЕРФЕЙС: голос + текст (добавлено Эдди 25.08 ночь)

Статус: ВЫПОЛНЕНО (Т1-Т2, 27.08). eddie.py — единая точка входа;
общий close_session в communication/session.py (main.py + eddie.py);
voice_io.VOICE → ru-RU-DmitryNeural (мужской рот, был рассинхрон).
voice_repl.py оставлен как legacy-обёртка (работает без изменений).
Факты [Подтверждено]: мозг уже один — оба канала зовут
Agent.respond() (main.py:8, voice_repl.py:378); память диалога
общая через БД (memory/manager.py build_conversation_context,
последние 8 CONVERSATION). Раздельны только обёртки.

- [x] Т1. Единая точка входа eddie.py: режимы --text/--voice/--mixed;
      в mixed Enter = текст, v+Enter = голос; транскрипт идёт в тот же
      respond(). Уши/рот вынести из voice_repl.py в переиспользуемый
      модуль. Старые точки входа сохранить как обёртки.
- [x] Т2. Общий ритуал close_session(agent): дневник + снимки души +
      diff из ЛЮБОГО режима (сейчас текстовый main.py теряет дневник
      и снимки — асимметрия voice_repl.py:333-363).
- Ограничение: не запускать два процесса одновременно (двойной
  cognition_worker, рассинхрон аффекта, риск блокировок SQLite).


## АВАТАР: внешний облик (решено Эдди 25.08 ночь; план согласован)

Статус: ЗАПЛАНИРОВАНО. Старт ПОСЛЕ рубежа A (сны+эмоции — иначе
нечего выражать лицом). Арт рисует Эдди вручную (10 лет опыта,
новый графпланшет); нейрогенерация НЕ используется (консистентность;
локальный SD запрещён правилом одной тяжёлой модели; бюджет 0).
Решение обратимо: конвейер принимает любые PNG по манифесту.
Стек [Подтверждено]: tkinter OK, Pillow 12.3.0 OK.
Форма (микс): лёгкий 2D спрайт-компаньон поверх экрана
(Tk transparentcolor, ~40–60 МБ RAM) + вкладка «Комната» в существующем
дашборде симуляции. Live2D/3D осознанно отложены до переезда
в интернет/апгрейда машины.
Архитектура: аватар — окно внутри ЕДИНОГО процесса eddie.py (Т1),
не отдельный процесс.

- [ ] А0. Конвейер ассетов: assets\avatar\ создана (refs/designs/
      sprites; правила в assets\avatar\README.md); сборщик Pillow:
      слои 256×256 → кадры, manifest.json, fallback слоёв из base.
- [ ] А1. Рантайм overlay: Tk always-on-top без рамки, перерисовка
      только при смене кадра (~10 fps max), перетаскивание мышью,
      облачко-субтитры.
- [ ] А2. Душа → лицо: emotional_state → слой эмоции; моргание/idle-
      циклы; cognition_worker занят → поза «задумался»; SLEEP → сон.
- [ ] А3. Lip-sync: рот по амплитуде PCM speak() в реальном времени
      (~10 fps), фазы рта — статичные слои (не видео).
- [ ] А4. Дизайны day/base + night + work: общие лицо/рот/глаза,
      меняются тело+голова (~12–18 файлов на доп. дизайн); триггеры:
      SLEEP → night, активная когниция N минут → work; плавное
      переключение (~200 мс) + ручная кнопка.
- [ ] А5. Связь с R3/С4: ночью спит, вздрагивает при снах.
- Спец сдачи Эдди (детали в assets\avatar\README.md): фаза 0 —
  ~8 файлов (body idle ×2, eyes ×2, mouth ×4, face neutral) к концу
  недели 1–2; фаза 1 — полный дневной ~25–35 файлов к концу недели
  3–4; фаза 2 — night/work, эмоции ×3, длинные циклы — без срока.
  Требования: PNG 256×256 прозрачный, выравнивание кадров по сетке,
  латиница в именах.
- Критерий видимости: EddieAI моргает, дышит, шевелит ртом под речь,
  лицо реагирует на self_state.emotional_state.


## ДОСТУП К ПК: этапы ДПК0–ДПК4 (согласовано Эдди 25.08 ночь)

Статус: ЗАПЛАНИРОВАНО. Принцип: он ЖИТЕЛЬ ПК, а не хозяин — каждый
новый орган через белый список/proposal-конвейер; системные пути вне
песочницы запрещены; тяжёлое не поднимать (уроки RAM).
Факты [Подтверждено]: FilesystemExecutor чтение только C:\EddieAI
(identity/filesystem_executor.py:25), запись намеренно выключена (:53);
research/web executor подключён (autonomy_runtime_factory.py:195).

- [ ] ДПК0 «Мини-чувства» (после рубежа A, ~1 смена): часы ПК
      (время суток в промпт); включить запись ТОЛЬКО для своих
      поддеревьев (assets\avatar\, дневниковые файлы); свободная RAM
      простым вызовом.
- [ ] ДПК1 «Наблюдатель» (вместе с рубежом B): watchdog R3 →
      агент видит процессы/RAM/CPU как самочувствие машины.
- [ ] ДПК2 «Руки» (после B): запуск программ по белому списку;
      всё новое — через согласование Эдди. 1–2 смены.
- [ ] ДПК3 «Глаза» (после рубежа C): скриншоты → Ox Alpha Free
      чекпоинтами (роутинг MODELS.md).
- [ ] ДПК4 «Пилот»: мышь/клавиатура — далеко, только отдельным
      решением совета директоров.


## UI Beauty Pass симуляции (отложено Эдди 24.08.2026 ночь)

- [ ] Графическая доработка дашборда (карта Конохи + вкладки) — интерфейс
  «всё ещё недоделанный графически» по оценке Эдди. Не трогать до явной
  отмашки; текущий приоритет — личность EddieAI.


## Дефект: мир симуляции не регенерируется между прогонами (24.08.2026 ночь)

- [ ] Карта Конохи и семья Эдди одинаковы в каждом новом прогоне:
  seed=22092014 захардкожен в scenarios/first_day_new_city.py (база всех
  сценариев). Эдди ожидал процедурную генерацию. Чинить только после
  решения: канон стабильного мира vs случайные миры (влияет на школу
  22.09.2014 и привязки семьи).


## Дашборд симуляции: окно дневника EddieAI (цель от Эдди 25.08)

- [ ] Добавить вкладку/окно «Дневник» в дашборд: последние записи
  diary песочницы прогона, читаемый вид. Вместе с будущим Beauty Pass.


## Нейминг-ревизия мира: eddie -> EddieAI (цель от Эдди 25.08)

- [ ] Перепроверить ВСЕ упоминания агента в симуляции и EddieAI-коде:
  поля eddie_id/eddie_location/household_eddie/eddie_anchor и т.п.
  записаны строчным «eddie» — по канону агент это EddieAI (без имени,
  но обозначение именно EddieAI).
- [ ] Аккуратная миграция: технические идентификаторы могут быть связаны
  с данными прогонов и БД — менять только с картой замен + тестами.
- [ ] Итог: ни одного места, где агент называется просто «eddie».


## P0-b: Замкнуть цепь целей (из аудита 25.08) — ЗАКРЫТО 24.08 ~13:00

- [x] Найден корень: в `_capture_goal_claim` (agent.py) весь блок
  принятия proposals был мёртвым кодом внутри except после `return`
  (артефакт отладки прерванной смены); плюс 3 скрытых дефекта:
  proposal_type "goals" вместо "goal", вызов set_proposal_status с 3
  аргументами, Proposal без обязательных reason/evidence.
- [x] Починено: метод переписан (два чистых try/except, тип "goal",
  Proposal c origin из БД). В identity/proposal.py добавлено поле
  `origin` (нужен для bypass MIN_CONFIDENCE в IdentityManager.evaluate).
- [x] Проверки: цепочка без LLM PASS; полный тест с Agent()
  (песочница EDDIE_DATA_DIR, без LLM-сервера) PASS — цель
  «Я решаю изучить Python» принята, self_state goals обновлён,
  proposal закрыт. agent.py/proposal.py: UTF-8 no BOM, 0 nulls,
  0 мохибека, py_compile OK.
- [x] ВЫПОЛНЕНО 25.08 (отмашка Эдди «давай, делай»): прод data/memory.db
  очищен. Бэкап data_backup_2026-08-25 (7 файлов, memory.db через sqlite
  backup API). Удалено 107 тестовых событий (id 190–296, окно 24.08
  06:27–06:45 UTC: «Я решаю изучить Python» ×20 + служебные violations)
  и все 3 pending proposals того окна. Настоящая история 23.08
  (события 1–189, вкл. «Рождение Эпохи 2») СОХРАНЕНА полностью.
  PRAGMA integrity_check=ok; wal_checkpoint(TRUNCATE); остальные таблицы
  пусты. Отчёт о прогоне: ..\..\EddieAI_Simulations\отчеты\
  MINI_RUN_25_08_MEMORY_AND_THOUGHTS_LIVE.md

## P0-c: Фиксация мыслей cognition_worker (из аудита 25.08) — РАССЛЕДОВАНО 25.08, решение за Эдди

- [x] РАССЛЕДОВАНО. Корней три, все найдены (см. MEMORY.md «Урок WAL»):
  1) cognition_worker создаётся, но НЕ СТАРТУЕТ в прогонах: start()
     зовёт только AutonomyRuntimeFactory (core/autonomy_runtime_factory.py:446),
     а симуляционный фреймворк его не вызывает;
  2) очередь когниции в песочнице — застывшая копия прода
     (eddie_data_profile/cognitive_queue.json: DONE 18 / PROCESSING 2,
     маршруты без COGNITION), новые тики её не наполняют — мировой путь
     respond_with_action не проходит через роутер/очередь;
  3) apply_all_analyzed вызывается только в полном respond()
     (agent.py:4519), которого в мире нет — даже проанализированное
     некому применять.
- [ ] Дополнительно найден дефект cognitive_processor.apply_analyzed:
  ветка route=="COGNITION" ссылается на несуществующий self.self_state
  (~строка 382 → AttributeError), REFLECTION-код после return мёртв,
  дубль условия 443–483 съедает тело рефлексий. Чинить отдельным
  решением.
- [x] ЗАКРЫТО 25.08 (Б2): cognition_worker стартует в симуляциях
  (EddieBridge.create), apply_analyzed чинен, apply_all_analyzed в
  мировом пути. Остаток — живой ночной прогон с LLM (см. P0-d).

## P0-d: Песочница симуляции не получает память агента — КОРЕНЬ НАЙДЕН 25.08, решение за Эдди

- [x] ПОЛНАЯ ЦЕПЬ доказана воспроизведением (%TEMP%\opencode\
  leak2_test.py, leak3_test.py):
  1) bridge зовёт respond_with_action → _respond_world_observation
     (agent.py:3746): LLM отвечает и всё — НИ ОДНОГО memory.remember;
  2) единственная запись пути — ACTION_CHOICE при меню движения —
     обёрнута try/except pass (agent.py:3967–3999);
  3) MemorySandbox копирует профильную базу shutil.copy2 БЕЗ
     wal_checkpoint: схема жила в -wal → копия без таблиц;
     _reset_experimental_memory молча пропускает отсутствующие таблицы
     → база-пустышка принимается как норма;
  4) итог: агент подключён к пустышке, все записи падают молча,
     runs/<id>/memory.db пусты, профиль не растёт. Воспроизведено:
     remember calls: 0 за цикл, run tables: [].
- [ ] Утечка 23.08 (189 событий в eddie_data_profile) — тот же класс:
  до починки attach записи уходили в общий профиль.
- [x] A1 СДЕЛАНО 25.08: MemorySandbox копирует через sqlite3 backup
  API; attach() вызывает agent.memory._initialize() + _ensure_table()
  у evidence/goal_affective_memory — схема песочницы гарантирована.
- [x] A2 СДЕЛАНО 25.08: ACTION_CHOICE except pass → печать
  "[memory] action choice record failed".
- [x] Б1 СДЕЛАНО 25.08: _respond_world_observation пишет
  SELF_EXPERIENCE (наблюдение) + CONVERSATION (реплику); падения
  журналируются. Проверка fix_verify_test.py: 7 событий в песочнице,
  профиль не растёт; регресс P0-b PASS.
- [x] Б2 СДЕЛАНО 25.08: apply_analyzed переписан (REFLECTION-ветка
  восстановлена, статус REFLECTION_APPLIED, сломанная COGNITION-ветка
  с self.self_state и мёртвый код удалены); respond_with_action
  вызывает apply_all_analyzed(); cognition_worker стартует в
  EddieBridge.create, останавливается через close. Проверки b2_test:
  REFLECTION_APPLIED + DONE, worker RUNNING→STOPPED; регресс
  P0-b/fix_verify PASS.
- [x] ЖИВОЙ МИНИ-ПРОГОН ПРИНЯТ 25.08 вечер: «школьное утро», 12 тиков
  с живым Mistral (~14 мин): песочница 36 событий, REFLECTION/DONE
  через облако, worker processed=1, кириллица цела, локальный стек не
  грузился. P0-c/P0-d закрыты на живом контуре.
- [x] Оптимизация RAM/качества (решение Эдди «вариант B»): мировая
  вербализация + рефлексия → облачный Mistral (JSON-режим для
  рефлексии), локальные модели — фолбэк; keep_alive рефлексии -1 →
  "3m". Прогон работает без загрузки qwen — блокер RAM снят.
