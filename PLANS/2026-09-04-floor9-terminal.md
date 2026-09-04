# Этаж 9 «Терминал» — План реализации

> **Для агентов:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development или superpowers:executing-plans.

**Цель:** EddieAI получает возможность безопасно выполнять системные команды через терминал, понимая границы собственности.

**Архитектура:** `CommandPolicy` (анти-катастрофический denylist) + `TerminalExecutor` (subprocess + timeout + захват вывода) → интеграция в `ToolRunner` через существующий `RUN_COMMAND` action type.

**Tech Stack:** Python 3.11+, subprocess, pyyaml, TDD.

**Спека:** Секция 1–9 (в чате, основные решения: понимание границ вместо жёстких ограничений, единый контур диалог+автономия, конфигурируемый allowlist).

## Глобальные ограничения

- Все файлы UTF-8 без BOM
- PowerShell не используется для записи файлов (только python/write)
- TDD: каждый модуль начинается с теста
- Нет коммитов без явного запроса Эдди
- Context7 при любом коде
- $env:PYTHONIOENCODING="utf-8" для запуска Python

---

### Задача 1: CommandPolicy (анти-катастрофический denylist)

**Файлы:**
- Создать: `identity/command_policy.py`
- Создать: `config/commands.yaml`
- Создать: `test_command_policy.py`

**Интерфейсы:**
- Потребитель: `ToolExecutionPolicy._powershell()` (Задача 2)
- Продюсер: `CommandPolicy.is_safe(command: str) -> bool`

**Шаги:**

- [ ] **1.1** Создать `config/commands.yaml` с allowlist (git, system, filesystem, scripts, programs) и denylist (Format-Volume, Remove-Item -Recurse C:\, winget install, pip install, curl/wget)

- [ ] **1.2** Написать `test_command_policy.py`: 6+ кейсов — разрешённая команда проходит, заблокированная нет, regex-паттерны работают, пустая команда → False, команда с аргументами → regex матчит

- [ ] **1.3** Запустить тест → RED (модуля нет)

- [ ] **1.4** Реализовать `identity/command_policy.py`: `CommandPolicy` с `__init__(config_path)`, `is_safe(command: str) -> bool`, `load_config(path)`, `_matches_denylist(command)`, `_matches_allowlist(command)`

- [ ] **1.5** Запустить тест → GREEN

- [ ] **1.6** Байт-проверка (UTF-8, без BOM)

---

### Задача 2: TerminalExecutor (subprocess + timeout)

**Файлы:**
- Создать: `identity/terminal_executor.py`
- Создать: `test_terminal_executor.py`

**Интерфейсы:**
- Потребитель: `ToolRunner._execute_real()` (Задача 4)
- Продюсер: `TerminalExecutor.execute(command: str, cwd: str | None) -> dict` → `{"status": "OK"|"TIMEOUT"|"ERROR", "stdout": str, "stderr": str, "exit_code": int}`

**Шаги:**

- [ ] **2.1** Написать `test_terminal_executor.py`: 8+ кейсов — выполнение команды (echo), таймаут (Start-Sleep 60 → TIMEOUT), захват stderr, лимит вывода 50KB, пустая команда → ERROR, exit_code, working directory

- [ ] **2.2** Запустить тест → RED

- [ ] **2.3** Реализовать `identity/terminal_executor.py`: `TerminalExecutor` с `execute()`, `subprocess.run()`, timeout=30, capture_output=True, max_output_bytes=50KB, encoding='utf-8', errors='replace'

- [ ] **2.4** Запустить тест → GREEN

- [ ] **2.5** Байт-проверка

---

### Задача 3: Self-model ownership

**Файлы:**
- Изменить: `identity/self_model.py` (добавить `ownership` в `capabilities_and_limitations()`)
- Создать: `test_self_model_ownership.py`

**Интерфейсы:**
- Потребитель: `self_concept_resolver.py`, оба промпта
- Продюсер: `self_model.ownership` dict

**Шаги:**

- [ ] **3.1** Написать `test_self_model_ownership.py`: 3 кейса — ownership присутствует в capabilities, ключи mine/eddies/installed/system/installing, ownership_text содержит ключевые фразы

- [ ] **3.2** Запустить тест → RED

- [ ] **3.3** Добавить `ownership` в `SelfModel.capabilities_and_limitations()` — dict с ключами `mine`, `eddies`, `installed`, `system`, `installing` + `ownership_text()` хелпер

- [ ] **3.4** Запустить тест → GREEN

- [ ] **3.5** Проверить self_concept_resolver.py — ownership в render (grep)

---

### Задача 4: Интеграция в ToolRunner + ToolExecutionPolicy + Factory

**Файлы:**
- Изменить: `identity/tool_policy.py` (_powershell → CommandPolicy + TerminalExecutor)
- Изменить: `identity/tool_runner.py` (_execute_real → ветка "powershell")
- Изменить: `core/autonomy_runtime_factory.py` (регистрация)
- Создать: `test_tool_runner_run_command.py`
- Создать: `test_command_audit.py`

**Интерфейсы:**
- Потребитель: `agent_loop.py` (существующий, не трогаем)
- Продюсер: `tool_runner.run(Action(action_type="RUN_COMMAND", ...))` → результат

**Шаги:**

- [ ] **4.1** Написать `test_tool_runner_run_command.py`: 5 кейсов — RUN_COMMAND проходит через конвейер, результат содержит stdout, команда из denylist → отказ, таймаут → статус TIMEOUT, команда записывается в память как EVENT

- [ ] **4.2** Написать `test_command_audit.py`: 3 кейса — каждая команда → EVENT с типом TOOL_EXECUTION, EVENT содержит command + exit_code + stdout_preview

- [ ] **4.3** Запустить тесты → RED

- [ ] **4.4** Изменить `identity/tool_policy.py`: `_powershell()` → `CommandPolicy().is_safe(command)` + если safe → `TerminalExecutor().execute()`, иначе DENY

- [ ] **4.5** Изменить `identity/tool_runner.py`: в `_execute_real()` ветка `"powershell"` → `tool.execute(command, cwd)`

- [ ] **4.6** Изменить `core/autonomy_runtime_factory.py`: `registry.register("powershell", TerminalExecutor(), "Безопасный терминал")`

- [ ] **4.7** Запустить тесты → GREEN

---

### Задача 5: Регресс + документация

**Файлы:**
- Запустить: `final_regression_suite.py`
- Запустить: `test_orchestrator_local.py`
- Обновить: `CHANGELOG.md`, `TODO.md`, `PROJECT_STATE.md`

**Шаги:**

- [ ] **5.1** Запустить `final_regression_suite.py` → 7+ passed

- [ ] **5.2** Запустить `test_orchestrator_local.py` → ALL PASS

- [ ] **5.3** Байт-проверка всех новых/изменённых файлов

- [ ] **5.4** Обновить CHANGELOG, TODO, PROJECT_STATE

- [ ] **5.5** llm_procs = 0
