# Аудит ALL — батч 50

Файлы: test_emotion_dialogue_compact.py, test_emotion_dialogue_full.py, test_emotional_baseline.py
Модель: deepseek-v4-flash

Мы провели глубокий аудит трёх тестовых скриптов: test_emotion_dialogue_compact.py, test_emotion_dialogue_full.py, test_emotional_baseline.py. Все они используют core.agent.Agent и core.autonomy_runtime_factory.AutonomyRuntimeFactory. Найдены следующие проблемы.

## test_emotion_dialogue_compact.py

1. **Строка 1-3**: Импорты не отсортированы, но это не критично. Стиль: используется многострочный формат с разбивкой, но в целом единый стиль не выдержан (например, в одном месте `OUTPUT = Path(r".\diagnostics_emotion_compact")` с сырой строкой, в другом `RAW = OUTPUT / "responses.jsonl"`). Не критично.

2. **Строка 7**: `OUTPUT = Path(r".\diagnostics_emotion_compact")` — используется обратный слэш в raw-строке. На Windows это работает, но на Linux/Unix будет ошибка, так как `.\diagnostics...` интерпретируется как имя файла с точкой и обратным слэшем. Лучше использовать `Path("diagnostics_emotion_compact")` или `Path("./diagnostics_emotion_compact")`. Это потенциальная проблема переносимости. Серьёзность: MEDIUM.

3. **Строка 13-23**: `EMOTIONS` список — дублируется в каждом файле. Это нарушение DRY, но не баг.

4. **Строка 25-49**: `STATES` — список кортежей. В `CURIOSITY__FRUSTRATION` значения `curiosity` и `frustration` установлены в 1.0. Но в `apply_reaction` передаются `changes=state_values`, где значения могут быть не только 0 и 1, но здесь только 1.0. ОК.

5. **Строка 52-63**: `MESSAGES` — список кортежей. ОК.

6. **Функция `text_metrics` (строки 66-118)**:
   - Использует `re.findall(r"\S+", text)` для подсчёта слов — это считает последовательности непробельных символов, включая знаки препинания. Например, "Привет," будет считаться как одно слово "Привет,". Это может быть приемлемо, но неточно. Лучше использовать `\b\w+\b` с учётом Unicode. Но это не критично.
   - `sentences = re.findall(r"[.!?…]+", text)` — считает количество знаков препинания, но не учитывает многоточие как один знак? В регулярном выражении `[.!?…]+` — это один или более символов из набора, так что "..." будет считаться как одно совпадение (так как `+` жадно). Но если текст содержит "?!", то это будет одно совпадение. Это нормально.
   - `first_person` и `second_person` используют регулярные выражения с `\b` и русскими словами. Но `\b` в Python для Unicode работает, но нужно убедиться, что используется флаг `re.UNICODE` (по умолчанию в Python 3 это так). ОК.
   - `help_offer` и `initiative_markers` — проверяют наличие подстрок в `lowered`. ОК.

7. **Функция `run_case` (строки 121-227)**:
   - Создаёт `Agent()` и `AutonomyRuntimeFactory(agent).build()`. Затем `agent.affective_state.reset()`. Если `state_values` не пустой, вызывает `apply_reaction`. Но `apply_reaction` может изменить состояние не так, как ожидается, если `changes` содержит значения, которые не являются допустимыми эмоциями? В `EMOTIONS` перечислены все, но `apply_reaction` может ожидать другие ключи. Это зависит от реализации `AffectiveState`. Не проверено.
   - `before = agent.affective_state.snapshot()` — получает снимок. Затем `behavior = agent.affective_dialogue_policy.profile()`. Это может быть дорого, но не критично.
   - `answer = agent.respond(message)` — вызывает ответ. Если возникает исключение, записывается в `error`. ОК.
   - `after = agent.affective_state.snapshot()` — снимок после.
   - Вычисляется `delta` для каждой эмоции из `EMOTIONS`. Но если в `before` или `after` нет ключа для какой-то эмоции, используется `0.0`. Это нормально.
   - `result` содержит `behavior` — это профиль политики, но не ясно, что это за объект. Если это словарь, то он сериализуется в JSON. Если это объект с несериализуемыми полями, будет ошибка. Но в коде нет проверки. Возможно, `profile()` возвращает словарь.
   - `agent.close()` вызывается в конце. ОК.

8. **Основной цикл (строки 230-350)**:
   - `RAW.open("w", encoding="utf-8")` — файл открывается в текстовом режиме с UTF-8. ОК.
   - В цикле для каждого состояния и сообщения вызывается `run_case`, результат добавляется в `results` и записывается в файл. `file.flush()` после каждой записи — хорошо для немедленной записи.
   - Вывод на печать: `print(f"[{index:02d}/{total}] {message_name:18} {result['elapsed_s']:6.2f}s | {result['answer']}")` — если `answer` содержит непечатные символы или очень длинный, вывод может быть громоздким, но это не баг.
   - В конце печатается "DONE" и путь.

**Потенциальные проблемы**:
- Нет обработки ошибок при создании Agent или build. Если `Agent()` или `AutonomyRuntimeFactory.build()` выбросит исключение, скрипт упадёт. Но это тестовый скрипт, может быть приемлемо.
- `apply_reaction` может изменить состояние не так, как ожидается, если `changes` содержит ключи, не входящие в `EMOTIONS`. Но в `STATES` используются только ключи из `EMOTIONS`.
- В `run_case` не используется `instrument_agent` (в отличие от full-версии), поэтому нет данных о вызовах модели. Это не баг, а отличие.
- В `text_metrics` для `help_offer` используется `any(marker in lowered for marker in (...))` — это возвращает bool, но в `result` это будет bool, что сериализуется в JSON как true/false. ОК.
- В `result` есть `"metrics": text_metrics(answer)`, но если `answer` равно `None` (при ошибке), то `text_metrics(None)` вернёт метрики для пустой строки. Это нормально.

**Серьёзных багов не обнаружено.**

## test_emotion_dialogue_full.py

1. **Строка 1-10**: Импорты, включая `csv`, `json`, `re`, `time`, `datetime`, `Path`. ОК.

2. **Строка 13-30**: Конфигурация путей. Используется `Path(r".\diagnostics_emotion_full")` — та же проблема с обратным слэшем. MEDIUM.

3. **Строка 32-44**: `EMOTIONS` — дублируется.

4. **Строка 46-63**: `CONFLICTS` — список кортежей с именами конфликтов и списком эмоций. ОК.

5. **Строка 65-91**: `MESSAGES` — больше сообщений, включая joke, vulnerability, goal_threat. ОК.

6. **Функция `now_iso()`** (строка 96-98): возвращает ISO строку с UTC. ОК.

7. **Функция `safe_json(value)`** (строки 101-139): рекурсивно преобразует объекты в JSON-совместимые. Обрабатывает dict, list, tuple, set, объекты с `to_dict` или `__dict__`. Но есть потенциальная проблема: если объект имеет `__dict__`, но его атрибуты содержат несериализуемые объекты, рекурсия может зациклиться (если есть циклические ссылки). В тестовом скрипте это вряд ли возникнет, но стоит отметить. Также `safe_json` не обрабатывает `datetime` объекты, но они не используются в результатах. ОК.

8. **Функция `text_metrics`** (строки 142-244): похожа на компактную, но добавлены `emotional_markers`, `distancing_markers`, `help_markers`. ОК.

9. **Функция `zero_state()`** (строки 247-251): возвращает словарь с нулями для всех эмоций. ОК.

10. **Функция `build_states()`** (строки 254-286): создаёт состояния: NEUTRAL, для каждой эмоции MAX, и для каждого конфликта. ОК.

11. **Функция `instrument_agent(agent)`** (строки 289-377):
    - Заменяет `agent._generate` и `agent._generate_structured` на обёртки, которые записывают время и параметры. Это делается для каждого агента. Но есть проблема: если `agent._generate` уже был заменён ранее (например, при повторном вызове), то `original_generate` будет ссылаться на предыдущую обёртку, и произойдёт двойное оборачивание. В данном случае каждый агент создаётся заново, так что это не проблема.
    - В `wrapped_generate` используется `kwargs.get("task")`, `kwargs.get("fast")`, `kwargs.get("system_prompt")`, `kwargs.get("user_prompt")`. Если эти аргументы не передаются, то будет `None`, и `len(str(None))` = 4 (строка "None"). Это не баг, но может исказить статистику. Лучше использовать `kwargs.get("system_prompt", "")`.
    - В `wrapped_structured` аналогично.
    - Возвращает `stats` — словарь с двумя списками.

12. **Функция `run_case`** (строки 380-560):
    - Создаёт агента, инструментирует его.
    - `active = {key: float(value) for key, value in state_values.items() if float(value) != 0.0}` — фильтрует нулевые значения. ОК.
    - `agent.affective_state.apply_reaction(changes=active, ...)` — передаёт только ненулевые. ОК.
    - `before = agent.affective_state.snapshot()`.
    - `behavior = agent.affective_dialogue_policy.profile()`.
    - `route_before = getattr(agent, "previous_route", None)` — получает атрибут, если есть.
    - Вызывает `agent.respond(message)`.
    - После ответа получает `after`.
    - Вычисляет `affective_delta`.
    - Вычисляет `model_time` и `structured_time` из instrumentation.
    - `model_call_count = len(generate_calls) + len(structured_calls)`.
    - Возвращает словарь с множеством полей.
    - В `finally` закрывает агента.

    **Потенциальные проблемы**:
    - `agent.affective_state.reset()` вызывается до `apply_reaction`. Но если `reset()` сбрасывает состояние, то `apply_reaction` добавит изменения. Это нормально.
    - `behavior` может быть несериализуемым объектом, но в `result` он попадает как есть. При записи в JSON через `json.dumps` может возникнуть ошибка, если `behavior` не сериализуем. Но в коде используется `json.dumps(result, ensure_ascii=False)` без `default=safe_json`. Это значит, что если `behavior` — объект, не являющийся стандартным типом, будет ошибка. Однако в `run_case` возвращается `behavior` как есть. В `safe_json` он не оборачивается. Это потенциальная проблема: если `profile()` возвращает словарь, то ок; если возвращает объект с атрибутами, то `json.dumps` упадёт. В компактной версии `behavior` тоже возвращается, но там нет `safe_json`. В full-версии есть `safe_json`, но он не применяется к `behavior` при записи в JSONL. В коде записи: `json.dumps(result, ensure_ascii=False)` — без `default`. Значит, если `behavior` не
