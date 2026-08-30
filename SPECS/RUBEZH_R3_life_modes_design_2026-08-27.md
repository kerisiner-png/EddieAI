# R3 «режимы жизни» — что есть / чего нет / что предлагаю

Дата: 27.08.2026
Статус: РЕАЛИЗОВАНО (вариант A + подтверждён уже-существующий B; C отложен).
Директива Эдди «R3+R2, потом 24h суточный запуск» — дала отмашку на R3.

## Что уже есть (ПОДТВЕРЖДЕНО по коду)

1. Сон/пробуждение — core/life_cycle.py (класс LifeCycle):
   - поля: asleep, fatigue, awake_since/asleep_since, sleep_count/wake_count;
   - окно сна 23:00-07:00 (SLEEP_WINDOW_START/END), ночной множитель
     усталости NIGHT_FATIGUE_MULTIPLIER=1.6;
   - динамика: gain/потеря усталости в час, пороги засыпания SLEEP_THRESHOLD
     0.80 / HARD_SLEEP_THRESHOLD 1.0 и пробуждения WAKE_THRESHOLD 0.25;
   - сохранение состояния (SAVE_INTERVAL_SECONDS=300).
2. Подключение: core/autonomous_runtime.py :99-105 вызывает life_cycle.update()
   и life_cycle.is_asleep(); core/autonomy_runtime_factory.py:452 создаёт
   LifeCycle и кладёт в runtime/agent.life_cycle.
3. Есть identity/reflection_scheduler.sleep_cycle (ночная консолидация).
4. Тесты: test_life_cycle.py (LifeCycle), test_live_behavior_contract и др.

## Чего НЕТ по TODO (R3 → «фундамент 24/7»)

5. watchdog RAM/CPU на PRODUCTION-цикле агента. Существующий logs\watchdog.py —
   это ТОЛЬКО рестартер legacy-процесса night_run.py (проверяет, жив ли процесс,
   перезапускает), НЕ мониторит RAM/CPU и не связан с LifeCycle/автономией.
6. Авто-выгрузка модели (model unload) при сне/простое — нет единого механизма,
   который при is_asleep()/простое выгружал бы локальную LLM и подгружал при
   пробуждении. (Облачный мозг на Zen — выгрузка не нужна, локаль — только
   фолбэк/офлайн.)
7. «Тики состояния без LLM» — нет отдельного тикера, который без вызова LLM
   периодически обновлял бы состояние (fatigue/activity/location), сохранял его
   и мог выполнять фоновые дешёвые операции в 24/7-режиме.

## Что предлагаю (вариант для решения Эдди)

A. WAR (watchdog автономной жизни) внутри core/autonomous_runtime.py:
   - фоновый тик без LLM: каждые N сек проверять RAM (по встроенному
     measurement), при просадке ниже порога — замедлить/приостановить
     циклы, вызвать life_cycle (сон при усталости), сохранить состояние;
   - без python-зависимостей на psutil не обязательно — можно через
     os-level (win32) или штатно: чтение Process.Memory e.q.
B. Привязка к LifeCycle: при is_asleep() — не вызывать LLM-запросы
   в автономном цикле (пропуск), при пробуждении — возобновление;
   локальную выгрузку модели вынести в отдельный hook (для лок/офлайн).
C. Отдельный модуль logs/watchdog_life.py (замена legacy night_run-watchdog)
   для постоянного 24/7-прогона агента: мониторит RAM/CPU/процесс, пишет
   в logs/watchdog.log, применяет life-cycle-меры.

Границы: НЕ трогаю DecisionRuntime / LLM-интеграцию без отдельного решения;
R3 меняет автономный цикл — требуется явная отмашка Эдди по объёму A/B/C.

## Критерий приёмки (предполагаемый)

- watchdog видит RAM-просадку и фиксирует решение (журнал) без падения;
- при is_asleep() автономный цикл не делает LLM-вызовов (счётчик в журнале);
- состояние (fatigue/sleep) сохраняется и восстанавливается между рестартами;
- не ломает существующие тесты life_cycle/автономии.

## Вопрос к Эдди

Какой объём R3 делать сейчас (A / B / C / все), и какие пороги RAM/CPU —
с учётом облачного мозга (локаль не грузится) и вечернего запуска на 24 ч?

## Итог реализации (27.08)

Решение Эдди: «R3+R2, потом 24h». Выбран вариант A и подтверждён B.

- B подтверждён по коду: AutonomousRuntime.tick() УЖЕ гейтит на
  is_asleep() -> ASLEEP без вызова LLM (core/autonomous_runtime.py),
  а life_cycle.update() — тик состояния без LLM. Отдельная правка не
  потребовалась; C (новый watchdog_life.py) ОТЛОЖЕН.
- A реализован: core/resource_watchdog.py (ResourceWatchdog, ctypes
  GlobalMemoryStatusEx для win32, без psutil; enabled=False по умолчанию
  — обратная совместимость; пороги CRITICAL<700МБ / LOW<1024МБ, probe
  30с, hold-off 60с). Встроен в AutonomousRuntime.tick() (гейт после
  asleep-блока): при should_throttle() -> THROTTLED, state LOW_RESOURCE,
  LLM-тик scheduler.tick() пропущен, life_cycle.update() уже отработал.
  Проброшен через AutonomyRuntimeFactory (поля resource_watchdog=None);
  включён (enabled=True) в night_run.py (24/7 раннер).
- Авто-выгрузка локальной модели (6): не добавлялась намеренно —
  CloudFirstLlm ленив (не грузит модель до первого запроса), т.е.
  выгрузка имплицитна; трогать LLM-интеграцию без отдельного решения
  запрещено (AGENTS.md).
- Пороги по умолчанию: low=1024МБ, critical=700МБ (для машины 8ГБ,
  облачный мозг локаль не грузит). При желании Эдди пороги меняются
  параметрами ResourceWatchdog.
- Проверки: py_compile OK; юнит и смоук tick (OK/disabled/THROTTLED/
  ASLEEP — без LLM при низкой RAM/сне) PASS; UTF-8 без BOM.
- Побочно исправлен предсуществующий баг: `if self.state == "PAUSED":`
  с нулевым отступом (ломал компиляцию) в core/autonomous_runtime.py — 
  выровнен к уровню метода.
