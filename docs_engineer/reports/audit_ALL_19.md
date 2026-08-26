# Аудит ALL — батч 19

Файлы: self_concept_policy.py, self_concept_resolver.py, self_conclusion_state.py
Модель: deepseek-v4-flash

Мы провели глубокий построчный аудит трёх файлов: core/self_concept_policy.py, core/self_concept_resolver.py, core/self_conclusion_state.py. Ниже представлены находки с указанием файла, строк, типа проблемы, серьёзности, последствий и рекомендаций по исправлению. В конце — сводка по модулю.

## Аудит файлов

### core/self_concept_policy.py (287 строк)

Файл содержит только функцию `build_self_concept_policy()`, которая возвращает многострочную строку с политикой. Проблемы:

1. **Строка 1**: `from textwrap import dedent` — импорт используется, но в функции `dedent` применяется к строке с тройными кавычками. Всё корректно.

2. **Строка 5-287**: Текст политики. Замечания:
   - **Стиль**: Внутри текста используются русские и английские фразы, но в целом стиль единый. Нет явных нарушений.
   - **Кодировка**: Файл, судя по всему, в UTF-8 без BOM (не видно BOM). Это соответствует требованиям.
   - **Логика**: Политика описывает самоидентификацию EddieAI. Нет явных логических ошибок.
   - **Безопасность**: Нет секретов, утечек.
   - **Мёртвый код**: Нет.
   - **Хрупкость**: Нет.

Потенциальные улучшения:
- **Строка 287**: `.strip()` убирает лишние пробелы в начале и конце, но внутри текста есть отступы, которые `dedent` убирает. Всё ок.
- **Строка 5**: `dedent` применяется к строке, начинающейся с новой строки и пробелов. Это нормально.

Вывод: файл корректен, проблем нет.

### core/self_concept_resolver.py (211 строк)

Класс `SelfConceptResolver` собирает данные из `self_state` агента.

1. **Строка 1**: `from textwrap import dedent` — используется в `render()`. ОК.

2. **Строка 6-8**: `__init__` сохраняет `agent`. ОК.

3. **Метод `snapshot()` (строки 10-63)**:
   - **Строка 12**: `self_state = self.agent.self_state` — предполагается, что у агента есть атрибут `self_state`. Если его нет, будет `AttributeError`. Это хрупкое место: нет проверки наличия атрибута. **Серьёзность: MEDIUM** — может упасть при неправильной инициализации.
   - **Строки 14-20**: `relationships = self_state.get("relationships", {})` — если `self_state` не dict, упадёт. Но предполагается, что это dict.
   - **Строки 22-28**: `eddie_relationship = relationships.get("Eddie", {})` — если `relationships` не dict, упадёт. Но это вероятно.
   - **Строки 30-36**: `roles = eddie_relationship.get("roles", [])` — аналогично.
   - **Строки 38-62**: Возвращает словарь. Использует `list(...)` для копирования списков, что хорошо.
   - **Строка 44**: `"base_model": "phi4-mini:latest"` — захардкожено. Если модель изменится, придётся менять код. **Серьёзность: LOW** — но лучше брать из конфигурации.
   - **Строка 46**: `"user": "Эдди"` — тоже захардкожено. **LOW**.
   - **Строка 48**: `mission_statement` и `primary_mission` — берутся из self_state с дефолтами. ОК.

4. **Метод `get_persistent_conclusion()` (строки 65-76)**:
   - Использует `getattr(self.agent, "self_conclusion_state", None)`. Если атрибут есть, но это не объект с методом `get_conclusion()`, будет ошибка. **MEDIUM** — нет проверки типа.
   - Если `conclusion_state` не None, вызывает `get_conclusion()`. Если метод не существует, упадёт. **MEDIUM**.

5. **Метод `conclusion_render()` (строки 78-119)**:
   - Если `conclusion` None, возвращает строку. ОК.
   - Если есть, обращается к ключам `conclusion["conclusion"]`, `conclusion["confidence"]`, `conclusion["basis"]`, `conclusion["provenance"]`, `conclusion["revision_count"]`. Если в словаре нет какого-то ключа, будет `KeyError`. **HIGH** — так как `get_conclusion()` в `SelfConclusionState` возвращает все ключи, но если состояние повреждено, может не быть. Лучше использовать `.get()`.
   - **Строка 103**: `str(conclusion["conclusion"])` — если значение None, будет "None". Это не ошибка, но может быть нежелательно.

6. **Метод `render()` (строки 121-211)**:
   - Использует `dedent` с f-строкой. Внутри есть `{state["entity"]}` и т.д. Если в `state` нет ключа, будет `KeyError`. Но `snapshot()` гарантирует наличие всех ключей, так что ОК.
   - **Строка 128**: `{state["base_model"]}` — захардкожено, но это из snapshot.
   - **Строка 130**: `{state["user"]}` — тоже.
   - **Строка 132**: `{state["eddie_roles"]}` — список, выводится как Python-представление списка, например `['friend']`. Это может быть некрасиво, но не ошибка.
   - **Строка 134**: `{state["mission"]}` — строка.
   - **Строка 136**: `{state["mission_code"]}`.
   - **Строки 138-146**: списки `values`, `interests`, `preferences`, `beliefs`, `goals` — выводятся как Python-списки. Это может быть нечитаемо, но не ошибка.
   - **Строка 148**: `Canonical interpretation:` — текст.
   - **Строки 150-211**: Текст с правилами. ОК.

**Общие замечания**:
- Нет обработки случаев, когда `self_state` не содержит нужных ключей — но `snapshot()` использует `.get()` с дефолтами, так что это безопасно.
- Хардкод `phi4-mini:latest` и `Эдди` — лучше вынести в конфиг.
- Отсутствие проверки типа `self_state` — если это не dict, упадёт.

**Серьёзность**: В целом файл рабочий, но есть потенциальные `KeyError` в `conclusion_render()` и хрупкость в `get_persistent_conclusion()`.

### core/self_conclusion_state.py (728 строк)

Класс `SelfConclusionState` управляет состоянием вывода о себе.

1. **Строка 1**: `from __future__ import annotations` — для отложенных аннотаций. ОК.
2. **Строка 3**: `from datetime import datetime, timezone` — используется.
3. **Строка 5**: `from typing import Any` — используется.
4. **Строка 7-20**: `DEFAULT_SELF_CONCLUSION_STATE` — словарь с дефолтными значениями. ОК.

5. **Метод `__init__` (строки 22-26)**:
   - Принимает `self_state` и вызывает `_ensure()`. ОК.

6. **Метод `_ensure()` (строки 28-49)**:
   - Проверяет, что `self.self_state` — dict. Если нет, устанавливает дефолт. ОК.
   - Если есть, но не хватает ключей, добавляет их. ОК.
   - **Строка 38**: `current = self.self_state.get(self.KEY)` — если `self.self_state` не dict, упадёт. Но `_ensure` вызывается после проверки? Нет, в `__init__` сразу вызывается `_ensure()`, и если `self_state` не dict, то `self.self_state.get` упадёт. **HIGH** — нет проверки типа `self_state`. В `__init__` нужно проверить, что `self_state` — dict, иначе поднять исключение или использовать дефолт.

7. **Метод `snapshot()` (строки 51-61)**:
   - Возвращает копию словаря. ОК.

8. **Метод `render()` (строки 63-82)**:
   - Использует f-строку с ключами `state["status"]`, `state["current_conclusion"]`, `state["confidence"]`, `state["basis"]`, `state["unresolved_reasons"]`, `state["last_updated"]`. Все ключи есть в дефолтном состоянии, так что ОК.

9. **Метод `set_unresolved()` (строки 84-107)**:
   - Принимает `reasons` и `basis`. Устанавливает статус UNRESOLVED, очищает вывод. ОК.
   - **Строка 95**: `state["basis"] = list(basis or [])` — если `basis` None, будет пустой список. ОК.
   - **Строка 100**: `state["unresolved_reasons"] = list(reasons)` — если `reasons` не список, а строка, то `list("abc")` даст `['a','b','c']`. Это ошибка. **HIGH** — нужно проверить тип или использовать `[reasons]` если строка. Но в документации предполагается список. Всё же лучше добавить проверку.

10. **Метод `set_conclusion()` (строки 109-177)**:
    - Проверяет, что `conclusion` не пустая строка. ОК.
    - Ограничивает `confidence` от 0 до 1. ОК.
    - Если есть предыдущий вывод, добавляет запись в `revision_history`. ОК.
    - **Строка 139**: `state["revision_history"].append({...})` — если `revision_history` не существует, `setdefault` создаст. ОК.
    - **Строка 145**: `state["revision_count"] += 1` — если `revision_count` не существует, `setdefault` создаст. ОК.
    - **Строка 148**: `state["topic"] = str(topic).strip() if topic else state.get("topic")` — если `topic` пустая строка, то `if topic` ложно, и останется старый topic. Это может быть нежелательно, если нужно очистить topic. Но в целом ОК.
    - **Строка 151**: `state["predicates"] = list(predicates if predicates is not None else state.get("predicates", []))` — если `predicates` None, берёт старые. ОК.
    - **Строка 153**: `state["basis"] = list(basis)` — если `basis` не список, а строка, то `list("abc")` даст символы. **HIGH** — аналогично, нужно проверять тип.
    - **Строка 154**: `state["provenance"] = list(provenance or [])` — если `provenance` строка, то `list("abc")` даст символы. **HIGH**.
    - **Строка 156**: `state["unresolved_reasons"] = []` — очищает. ОК.
    - **Строка 157**: `state["last_updated"] = now` — ОК.

11. **Метод `has_conclusion()` (строки 179-190)**:
    - Проверяет статус и непустой вывод. ОК.

12. **Метод `_tokens()` (строки 192-207)**:
    - Статический метод, использует `re`. ОК.

13. **Метод `relevance()` (строки 209-350)**:
    - Сложный метод для определения релевантности запроса.
    - **Строка 213**: `conclusion = self.get_conclusion()` — если нет вывода, возвращает словарь с `relevant: False`. ОК.
    - **Строка 218**: `text = str(query or "").casefold().replace("ё", "е")` —
