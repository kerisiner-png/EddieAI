# Аудит ALL — батч 37

Файлы: reflection_cycle.py, reflection_engine.py, reflection_scheduler.py
Модель: deepseek-v4-flash

Мы провели глубокий аудит трех файлов: identity/reflection_cycle.py, identity/reflection_engine.py, identity/reflection_scheduler.py. Ниже представлены находки по каждому файлу с указанием строк, типов проблем, серьезности и рекомендаций.

## Файл: identity/reflection_cycle.py

### 1. Строка 12: `MODEL_NAME = "phi4-mini"` — дублирование модели
- **Тип**: Дублирование конфигурации, нарушение DRY.
- **Серьезность**: LOW.
- **Описание**: В файле `reflection_engine.py` также определена `MODEL_NAME = "phi4-mini"`. Это дублирование может привести к рассинхронизации при изменении модели.
- **Исправление**: Вынести в общий конфигурационный модуль или использовать `self.agent.model_orchestrator` для получения модели.

### 2. Строки 30-35: `run_snapshot` — потенциальная проблема с `snapshot.get("candidates", [])`
- **Тип**: Логическая ошибка (не критичная).
- **Серьезность**: LOW.
- **Описание**: Если `candidates` не является списком, то `candidates = []`, но если это, например, строка, то `isinstance(candidates, list)` вернет False, и candidates станет пустым списком. Это нормально, но потенциально может скрыть ошибку в данных.
- **Исправление**: Можно добавить логирование или явную проверку типа.

### 3. Строки 63-66: `cloud_content = self.agent.model_orchestrator._cloud_chat(...)` — обращение к приватному методу
- **Тип**: Нарушение инкапсуляции, хрупкость.
- **Серьезность**: MEDIUM.
- **Описание**: Используется приватный метод `_cloud_chat` (с подчеркиванием). Это может сломаться при изменении внутренней реализации `model_orchestrator`.
- **Исправление**: Добавить публичный метод `cloud_chat` в `model_orchestrator` или использовать существующий публичный интерфейс.

### 4. Строки 70-75: `free_gb = orchestrator.available_ram_gb()` и `need_gb = orchestrator.MODEL_RAM_GB.get("phi4-mini:latest")` — хардкод имени модели
- **Тип**: Дублирование, хрупкость.
- **Серьезность**: MEDIUM.
- **Описание**: Имя модели "phi4-mini:latest" захардкожено, тогда как `MODEL_NAME` определен выше. Если модель изменится, это место не обновится.
- **Исправление**: Использовать `MODEL_NAME` или получать имя из orchestrator.

### 5. Строки 80-82: `print("[reflection] мало RAM для ...")` — использование `print` для логирования
- **Тип**: Нарушение стиля, отсутствие логирования.
- **Серьезность**: LOW.
- **Описание**: В проекте, вероятно, используется модуль логирования, а здесь прямой `print`. Это может засорять стандартный вывод.
- **Исправление**: Заменить на `logging`.

### 6. Строки 95-100: `response = chat(...)` — вызов `chat` напрямую, без обработки ошибок
- **Тип**: Отсутствие обработки исключений.
- **Серьезность**: MEDIUM.
- **Описание**: Если локальная модель недоступна или произойдет ошибка, исключение не будет перехвачено, что приведет к падению потока.
- **Исправление**: Обернуть в try/except и вернуть пустой результат.

### 7. Строки 104-106: `raw = response["message"]["content"].strip()` — предполагается, что ответ всегда содержит "message" и "content"
- **Тип**: Хрупкость.
- **Серьезность**: MEDIUM.
- **Описание**: Если API вернет ошибку или другую структуру, будет KeyError.
- **Исправление**: Проверить наличие ключей.

### 8. Строки 110-115: `result = self._parse_json(raw)` — `_parse_json` возвращает `None` при ошибке, но здесь не проверяется `None` перед `isinstance(result, dict)`. Однако `isinstance(None, dict)` вернет False, так что это безопасно, но лучше явно проверить.

### 9. Строки 118-120: `candidate_decisions = result.get("candidate_decisions", [])` — если `result` не dict, то `result.get` вызовет AttributeError. Но выше проверка `if not isinstance(result, dict): return ...` — это защищает.

### 10. Строки 125-127: `valid_candidates = { (str(item.get("field")), str(item.get("value"))) for item in candidates }` — если `item` не dict, то `item.get` вызовет ошибку. Но `candidates` уже проверен как список, но элементы могут быть не dict. Нет проверки `isinstance(item, dict)`.
- **Тип**: Потенциальная ошибка.
- **Серьезность**: MEDIUM.
- **Исправление**: Добавить проверку `isinstance(item, dict)`.

### 11. Строки 133-150: фильтрация решений — в целом корректно.

### 12. Строки 156-160: `run()` — метод `run` не использует `run_snapshot`, а дублирует логику. Это нарушение DRY.
- **Тип**: Дублирование кода.
- **Серьезность**: MEDIUM.
- **Исправление**: Вынести общую логику в отдельный метод.

### 13. Строки 163-165: `memory_context = self.agent.memory_manager.build_context(limit=20)` — переменная не используется в методе `run()`.
- **Тип**: Мертвый код.
- **Серьезность**: LOW.
- **Исправление**: Удалить или использовать.

### 14. Строки 170-175: `candidate_data` — собирается из `candidates`, но затем в `run()` используется `candidates` напрямую для `valid_candidates`. Это нормально, но `candidate_data` используется только в промпте.

### 15. Строки 178-180: `self_state = self.agent.self_state.snapshot()` — в `run()` используется `self.agent.self_state`, но в `run_snapshot` используется переданный snapshot. Это разные пути.

### 16. Строки 183-200: Промпт в `run()` — дублирует промпт из `run_snapshot`, но с дополнительными правилами. Это дублирование.

### 17. Строки 202-210: `response = chat(...)` — снова прямой вызов `chat` без обработки ошибок.

### 18. Строки 212-214: `raw = response["message"]["content"].strip()` — та же проблема.

### 19. Строки 216-220: `result = self._parse_json(raw)` — если `_parse_json` вернет `None`, то `result` будет `None`, но дальше `if result is None: result = {...}` — это обработано.

### 20. Строки 222-226: `if not isinstance(result, dict): result = {...}` — это избыточно, так как `_parse_json` возвращает dict или None.

### 21. Строки 228-240: `candidate_decisions = result.get(...)` — если `result` не dict, то `result.get` вызовет ошибку, но выше уже проверено.

### 22. Строки 242-250: `valid_candidates = { (candidate.field, str(candidate.value)) for candidate in candidates }` — предполагается, что `candidate` имеет атрибуты `field` и `value`. Это объекты, вероятно, из `personality.candidates()`. Нет проверки типа.

### 23. Строки 252-270: фильтрация решений — в целом корректно.

### 24. Строки 272-274: `return {"candidate_decisions": filtered_decisions}` — возвращается только список решений, но не используется `memory_context` и `self_state` из начала метода. Это нормально.

### 25. Строки 276-295: `_parse_json` — функция обрабатывает JSON, но есть небольшой недочет: если `raw` начинается с "```json", то после удаления первой строки, `cleaned` может начинаться с "json", и код удаляет первые 4 символа. Это работает, но лучше использовать `json.loads` с `strict=False` или более надежный парсер.

### 26. Строка 280: `if raw.startswith("```"):` — если строка начинается с "```json", то `raw.startswith("```")` вернет True, но затем `lines[0].strip().lower() in {"```json", "```"}` — это проверка в `_parse` в другом файле, здесь просто `if raw.startswith("```"):` без проверки "```json". В `_parse_json` нет проверки на "```json", только на "```". Это может привести к тому, что строка "```json\n{...}\n```" будет обработана неправильно: после удаления первой строки, `cleaned` будет "json\n{...}\n```", затем `cleaned.startswith("json")` — да, удалит "json", но останется "\n{...}\n```", и `json.loads` может не сработать из-за лишних символов. Лучше обработать "```json" явно.

### 27. Строка 295: `return None` — если ничего не удалось распарсить.

## Файл: identity/reflection_engine.py

### 1. Строка 1: `import json` — используется.

### 2. Строка 2: `from memory.events import Event` — импорт, но в коде используется `Event.create`. ОК.

### 3. Строка 5: `MODEL_NAME = "phi4-mini"` — дублирование с reflection_cycle.py.

### 4. Строка 6: `MODEL_OPTIONS` — дублирование.

### 5. Строки 20-25: `__init__` — принимает `model_orchestrator=None`, но затем создает `CloudFirstLlm(model_orchestrator)`. Если `model_orchestrator` None, то `CloudFirstLlm` может упасть. Нет проверки.

### 6. Строка 27: `self.llm = CloudFirstLlm(model_orchestrator)` — импорт внутри `__init__` — это нормально, но лучше импортировать на уровне модуля.

### 7. Строки 29-31: `reflect` — метод, который вызывает `self.llm.chat`. В `CloudFirstLlm` может быть свой `chat` метод.

### 8. Строки 33-35: `result_text = self._result_text(result)` — метод `_result_text` определен ниже.

### 9. Строки 37-100: Промпт — большой, но корректный.

### 10. Строки 102-104: `raw = self.llm.chat(...)` — нет обработки ошибок. Если `chat` вернет None или выбросит исключение, метод упадет.

### 11. Строки 106-108: `data = self._parse(raw)` — `_parse` возвращает dict или None.

### 12. Строки 110-116: Если `data is None`, то устанавливаются значения по умолчанию.

### 13. Строки 118-120: `lesson = str(data.get("lesson", "")).strip()` — если `data` не dict, то `data.get` вызовет ошибку, но выше проверено.

### 14. Строки 122-124: `error = data.get("error")` — если `error` не None, то `str(error).strip()`.

### 15. Строки 126-128: `confidence = self._confidence(data.get("confidence", 0.0))` — метод `_confidence` определен ниже.

### 16. Строки 130-132: `signals = self._clean_signals(data.get("signals", []))` — метод `_clean_signals`.

### 17. Строки 134-136: `self._save_reflection(...)` — сохраняет рефлексию в память.

### 18. Строки 138-140: `follow_up_goals = self._clean_follow_up_goals(...)` — метод.

###
