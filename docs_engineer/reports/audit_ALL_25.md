# Аудит ALL — батч 25

Файлы: action_router.py, action_selector.py, adaptive_plan_controller.py
Модель: deepseek-v4-flash

Мы провели глубокий аудит кода. Ниже представлены находки по каждому файлу.

## Файл: identity\action_router.py

### Находки:

1. **Строки 1-2**: Импорт `dataclass` и `Action`, `VALID_ACTIONS` — корректно.
2. **Строка 5**: Импорт `VALID_ACTIONS` из `identity.action_executor` — предполагается, что это множество допустимых типов действий. Проверка в `route` использует `if action.action_type not in VALID_ACTIONS`. Это нормально.
3. **Строка 10-12**: `RoutedAction` dataclass — поля корректны.
4. **Строка 15-17**: `ROUTES` словарь — все ключи соответствуют типам действий. Проверим: `THINK`, `RESEARCH`, `WRITE`, `READ_FILE`, `WRITE_FILE`, `RUN_COMMAND`, `WEB_SEARCH`, `OPEN_URL`, `WAIT`. В `VALID_ACTIONS` должны быть эти же. Если есть другие допустимые действия, они не будут иметь маршрут и вернут `tool=None` -> "не найден инструмент". Это может быть проблемой, если `VALID_ACTIONS` содержит больше, чем в `ROUTES`. Но это скорее потенциальная проблема согласованности.
5. **Строка 20-22**: `__init__` принимает `registry` — предполагается, что это реестр инструментов с методом `get`. Нет проверки типа.
6. **Строка 25-91**: Метод `route` — логика:
   - Проверка `action.action_type not in VALID_ACTIONS` — если `VALID_ACTIONS` не содержит все возможные, то вернет `allowed=False`. Это нормально.
   - `tool = self.ROUTES.get(action.action_type)` — если нет в ROUTES, то `tool=None` -> возвращает "не найден инструмент". Это корректно.
   - `spec = self.registry.get(tool)` — если `tool` не None, но `registry.get` возвращает None, то "не зарегистрирован". ОК.
   - `if not spec.enabled` — предполагается, что `spec` имеет атрибут `enabled`. Если `spec` не имеет такого атрибута, будет ошибка. Но это зависит от реализации `registry`. Возможно, стоит добавить проверку `hasattr(spec, 'enabled')`.
   - Возвращает `RoutedAction` с `allowed=True` и reason "Инструмент доступен.".

**Проблемы**:
- **MEDIUM**: Нет проверки, что `spec` имеет атрибут `enabled`. Если `registry.get` вернет объект без `enabled`, будет `AttributeError`. Рекомендуется использовать `getattr(spec, 'enabled', False)` или проверять наличие.
- **LOW**: Если `VALID_ACTIONS` содержит больше типов, чем `ROUTES`, то для них будет возвращено "не найден инструмент" вместо "неизвестный тип". Это может быть неочевидно. Лучше сначала проверить, есть ли в `ROUTES`, а потом уже в `VALID_ACTIONS`. Но это не критично.
- **LOW**: Строка 91: `reason="Инструмент доступен."` — можно уточнить, какой инструмент.

**Серьёзность**: MEDIUM для отсутствия проверки `enabled`.

## Файл: identity\action_selector.py

### Находки:

1. **Строка 1**: `import json` — используется.
2. **Строка 2**: `from dataclasses import dataclass` — используется.
3. **Строка 5-8**: `ActionSelection` dataclass — поля: `selected`, `options`, `reason`. ОК.
4. **Строка 10-...**: Класс `ActionSelector` с docstring.
5. **Строка 17**: `EXPLORATION_INTERVAL = 3` — константа.
6. **Строка 19-22**: `__init__` принимает `memory` — предполагается, что у memory есть `connection` (используется в `_history_counts`). Нет проверки.
7. **Строка 24-...**: Метод `select`:
   - `options = list(options)` — преобразует в список.
   - Если пусто — `ValueError`.
   - Если один вариант — возвращает его.
   - `counts = self._history_counts(options)` — получает словарь счетчиков.
   - `total = sum(counts.values())` — сумма всех счетчиков.
   - `biases` — если `behavioral_biases` является dict, иначе пустой dict.
   - `bias_for(option)` — возвращает float из biases по `option.action_type`.
   - Если `total == 0`: выбирает `max(options, key=lambda option: (bias_for(option), -options.index(option)))`. Это странно: `-options.index(option)` — отрицательный индекс, чтобы при равных bias выбрать первый? Но `max` с ключом `(bias, -index)` — при равных bias выберет тот, у которого `-index` больше, т.е. индекс меньше (так как -0 > -1). Это эквивалентно выбору первого с максимальным bias. Затем если `abs(bias) > 0.0` — reason с affective state, иначе `selected = options[0]` (переопределяет выбранный! Это баг: если bias > 0, то selected уже выбран, но потом в else он переопределяется на options[0], игнорируя bias). Смотрим код:
     ```
     selected = max(options, key=lambda option: (b bias_for(option), -options.index(option)))
     bias = bias_for(selected)
     if abs(bias) > 0.0:
         reason = ...
     else:
         selected = options[0]
         reason = ...
     ```
     Если bias > 0, то selected остается как выбранный max, reason корректный. Если bias == 0, то selected переопределяется на options[0], но при этом max уже выбрал бы options[0] (так как bias=0, -index: у options[0] -0=0, у других -1, -2... max выберет 0). Так что переопределение не меняет результат, но код избыточен. Однако если bias > 0, то selected уже выбран, и else не выполняется. Так что бага нет, но код запутан.
   - Если `total != 0`: `exploration = total % EXPLORATION_INTERVAL == 0`. Если exploration, выбирает `min` по `(counts, -bias, action_type)`. Это значит: сначала минимальное количество использований, при равенстве — больший bias (так как -bias), при равенстве — лексикографически по action_type. Это нормально.
   - Иначе (не exploration) — `max` по `(counts + bias, bias, action_type)`. Это значит: сумма counts и bias, при равенстве — больший bias, при равенстве — лексикографически. Это нормально.
   - Возвращает `ActionSelection`.

8. **Метод `_history_counts`**:
   - `option_types = {option.action_type for option in options}` — множество типов.
   - `counts = {option_type: 0 for option_type in option_types}`.
   - Выполняет SQL-запрос к `self.memory.connection.execute(...)`. Предполагается, что `memory.connection` — это sqlite3 connection с поддержкой доступа по ключу (row_factory = sqlite3.Row). Иначе `row["content"]` не сработает. Это потенциальная проблема.
   - Запрос: `SELECT content FROM events WHERE event_type = 'ACTION_CHOICE' AND source_type = 'SELF_ACTION' AND personal_experience = 1 ORDER BY id ASC`. Это предполагает, что таблица `events` имеет такие колонки. Если нет — ошибка.
   - Для каждой строки: `json.loads(row["content"])` — если не JSON, пропускает.
   - Проверяет, что payload — dict.
   - `choice = payload.get("choice")` — должен быть dict.
   - `historical_options = choice.get("options", [])` — список.
   - `selected = choice.get("selected")` — что-то.
   - Проверяет, что `historical_options` — list.
   - `historical_set = {str(value) for value in historical_options}` — множество строк.
   - `current_set = {str(value) for value in option_types}` — множество строк (типы действий).
   - Если `historical_set != current_set` — пропускает (т.е. только если набор опций совпадает с текущими типами).
   - Если `selected in counts` — увеличивает счетчик. Здесь `selected` — это значение, которое должно быть ключом в `counts`. Но `counts` ключи — это `option.action_type` (строки). `selected` может быть строкой или чем-то еще. Если `selected` — это тип действия, то он должен быть строкой. Но в `historical_options` могут быть не только типы, а объекты? В коде `str(value)` для сравнения, но `selected` не преобразуется в строку. Если `selected` — это, например, объект Action, то `selected in counts` не сработает, потому что counts ключи — строки. Но в записи события, вероятно, `selected` хранится как строка (тип действия). Это надо проверить. Если `selected` — строка, то все ок. Но если это объект, то будет ошибка. Судя по коду, `selected` извлекается из JSON, так что это будет строка или число. Но `counts` ключи — строки (типы действий). Если `selected` — строка, то `selected in counts` сработает, если она есть в ключах. Но если `selected` — это, например, "THINK", а counts имеет ключ "THINK", то ок. Но если `selected` — это что-то другое (например, полное имя действия), то не сработает. Это потенциальная проблема.
   - Также `historical_set` и `current_set` сравниваются как множества строк. Если в historical_options есть не только типы, а что-то еще, то сравнение может не совпасть. Но предполагается, что options — это типы действий.

**Проблемы**:
- **HIGH**: В `_history_counts` используется `row["content"]` — предполагается, что `memory.connection` настроен с `sqlite3.Row`. Если нет, будет TypeError. Нужно проверить или использовать `row[0]`.
- **MEDIUM**: Сравнение `historical_set != current_set` — если в historical_options есть дополнительные значения (например, полные имена), то они не совпадут, и событие будет пропущено. Это может привести к тому, что история не учитывается. Но это может быть намеренно.
- **MEDIUM**: `selected in counts` — если `selected` не строка, а, например, число, то не сработает. Но скорее всего это строка.
- **LOW**: В ветке `total == 0` код с `selected = max(...)` и затем переопределение `selected = options[0]` в else — избыточно, но не баг.
- **LOW**: В `select` при `total == 0` и `abs(bias) > 0.0` reason говорит "выбор скорректирован текущим affective state", но на самом деле выбирается вариант с максимальным bias, а не просто первый. Это соответствует.
- **LOW**: В `select` при `total != 0` и exploration, reason говорит "с учётом текущего affective state", но bias используется как tie-breaker, что корректно.

**Серьёзность**: HIGH для row["content"], MEDIUM для сравнения множеств.

## Файл: identity\adaptive_plan_controller.py

### Находки:

1. **Строка 1**: `from identity.goal_planner import VALID_TASK_STATUSES` — импортируется, но не используется в этом файле. Это мёртвый импорт.
2. **Строка 3-...**: Класс `AdaptivePlanController`.
3. **Строка 7**: `MAX_TASKS = 5` — константа.
4. **Строка 9-12**: `__init__` принимает `goal_planner`. Предполагается, что у goal_planner есть методы `tasks`, `get_plan`, `_save`, `_plans`. Это внутренние методы (с подчеркиванием), что может быть нарушением инкапсуляции, но допустимо.
5. **Метод `apply`**:
   - `action = decision.get("decision", "KEEP")`.
   - `new_tasks = self._clean_tasks(
