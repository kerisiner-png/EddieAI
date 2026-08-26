# Аудит ALL — батч 7

Файлы: claim_shadow.py, cognition_worker.py, cognitive_decision_engine.py
Модель: deepseek-v4-flash

Мы провели аудит трех файлов: claim_shadow.py, cognition_worker.py, cognitive_decision_engine.py. Найдены следующие проблемы.

## Файл: core/claim_shadow.py

### Проблемы:

1. **Строка 1**: `from dataclasses import dataclass` — импорт корректен, но нет импорта `typing` для аннотаций `tuple` и `str | None` (используется `str | None` в сигнатуре метода `analyze`). В Python 3.10+ это допустимо, но если проект поддерживает более старые версии, это вызовет ошибку. Проверить версию Python.

2. **Строка 17-19**: `ShadowComparison` — замороженный dataclass, все поля корректны.

3. **Строка 28-31**: `__init__` принимает `claim_engine`, `claim_policy`, `claim_adapter` — нет проверки на `None`, но это не критично.

4. **Строка 42-43**: `claims = self.claim_adapter.from_response(...)` — предполагается, что `from_response` возвращает список/итератор. Если вернет `None`, то `tuple(... for claim in claims)` вызовет ошибку. Нет проверки.

5. **Строка 46-49**: `evaluations = tuple(self.claim_engine.validate_claim(claim) for claim in claims)` — если `validate_claim` вернет `None` или не имеет атрибутов, то `decision` может быть некорректным. Нет обработки ошибок.

6. **Строка 51-54**: `decision = self.claim_policy.evaluate(evaluations)` — предполагается, что `evaluate` возвращает объект с атрибутами `action` и `severity`. Если вернет `None`, то `decision.action` вызовет `AttributeError`. Нет проверки.

7. **Строка 56-58**: `new_problem = (decision.action == "REPAIR_REQUIRED")` — сравнение строк, но если `decision.action` не строка, может быть ошибка.

8. **Строка 60-62**: `mismatch = old_ok != (not new_problem)` — логика: если `old_ok` истинно, а `new_problem` истинно, то `mismatch` будет `True` (так как `not new_problem` = False, `old_ok != False` = True). Это правильно.

9. **Строка 64-70**: возврат `ShadowComparison` — все поля заполнены.

10. **Общее**: нет обработки исключений, если `claim_adapter.from_response` или `claim_engine.validate_claim` выбросят исключение, оно пробросится выше. Возможно, это ожидаемо.

11. **Стиль**: используется `tuple` без импорта из `typing`, но это не ошибка.

12. **Потенциальная утечка**: `structured_response` может содержать чувствительные данные, но они не логируются.

### Серьезность: MEDIUM (отсутствие проверок на None, возможные исключения).

## Файл: core/cognition_worker.py

### Проблемы:

1. **Строка 1-2**: импорты `threading` и `time` — корректно.

2. **Строка 8-10**: docstring корректен.

3. **Строка 13-15**: `__init__` — `poll_interval` преобразуется в float и ограничивается минимумом 0.1. Хорошо.

4. **Строка 17-19**: `self._thread = None`, `self._stop_event = threading.Event()`, `self._wake_event = threading.Event()` — корректно.

5. **Строка 21-23**: `self.state = "STOPPED"`, `self.last_result = None`, `self.last_error = None`, `self.processed_count = 0` — корректно.

6. **Строка 25-35**: `start()` — проверяет, жив ли поток, если да, возвращает `ALREADY_RUNNING`. Затем очищает события, устанавливает состояние `RUNNING`, создает поток и запускает. Возвращает `STARTED`. Поток демонический — хорошо.

7. **Строка 37-55**: `stop(timeout=2.0)` — устанавливает `_stop_event`, `_wake_event`, затем ждет завершения потока с таймаутом. Если поток не завершился, состояние `STOPPING`, иначе `STOPPED`. Возвращает статус. Потенциальная проблема: если поток завис в `processor.analyse_next()`, то `join` с таймаутом вернет управление, но поток останется висеть. Это может быть проблемой, но не критично.

8. **Строка 57-59**: `wake()` — просто устанавливает событие.

9. **Строка 61-68**: `snapshot()` — возвращает словарь с состоянием, счетчиком, последним результатом и ошибкой. Корректно.

10. **Строка 70-87**: `_run()` — цикл while, пока не установлен `_stop_event`. Внутри вызывает `self.processor.analyse_next()`. Если результат не `EMPTY`, увеличивает счетчик. Затем очищает `_wake_event` и ждет `_wake_event` с таймаутом `poll_interval`. Если возникает исключение, записывает ошибку, устанавливает состояние `ERROR` и завершает поток. После цикла устанавливает состояние `STOPPED`.

11. **Проблема**: В `_run()` после `self._wake_event.clear()` и `self._wake_event.wait(self.poll_interval)` — если `wake()` вызывается во время ожидания, поток просыпается немедленно, но затем снова вызывает `analyse_next()`. Это нормально. Однако если `analyse_next()` выбрасывает исключение, поток завершается, но `_stop_event` не устанавливается, и состояние `ERROR`. При следующем `start()` поток будет перезапущен, но `_stop_event` будет очищен. Это нормально.

12. **Потенциальная гонка**: `self.state` и `self.last_result` изменяются из потока и читаются из других потоков без синхронизации. В Python GIL обеспечивает атомарность отдельных операций, но составные операции (например, `self.processed_count += 1`) не атомарны. Однако это не критично, так как счетчик не критичен.

13. **Утечка**: если `processor.analyse_next()` возвращает объект, который содержит большие данные, `self.last_result` хранит его до следующего вызова. Это может привести к удержанию памяти, но это ожидаемо.

14. **Стиль**: используется `max(0.1, float(poll_interval))` — хорошо.

15. **Отсутствие обработки исключений в `stop()`**: если `thread.join()` вызовет исключение (например, `RuntimeError`), оно пробросится. Но это маловероятно.

### Серьезность: LOW (некритичные гонки, возможное зависание при долгой обработке).

## Файл: core/cognitive_decision_engine.py

### Проблемы:

1. **Строка 1**: `import json` — корректно.

2. **Строка 2**: `from identity.proposal import Proposal` — предполагается, что модуль `identity.proposal` существует и содержит класс `Proposal`. Если нет, будет ImportError.

3. **Строка 3**: `from memory.events import Event` — аналогично.

4. **Строка 5-7**: класс `CognitiveDecisionEngine` — docstring корректен.

5. **Строка 9-13**: `VALID_ACTIONS` — множество строк, корректно.

6. **Строка 15-21**: `IDENTITY_FIELDS` — словарь, сопоставляет типы с полями. Корректно.

7. **Строка 23-29**: `__init__` — принимает `agent`, извлекает `memory`, `identity_manager`, `evidence`. Если `agent` не имеет этих атрибутов, будет AttributeError. Нет проверки.

8. **Строка 31-45**: `decide()` — получает `item` и `analysis`. Извлекает `action` из `analysis`, приводит к верхнему регистру, проверяет на валидность, если нет — `RETAIN`. Вычисляет `importance` через `_importance`. Создает `decision` словарь. Далее ветвление по действиям.

9. **Строка 47-55**: `IGNORE` — устанавливает `applied=True`, reason, вызывает `_record` и возвращает.

10. **Строка 57-65**: `RETAIN` — аналогично.

11. **Строка 67-75**: `MORE_EVIDENCE` — аналогично.

12. **Строка 77-85**: `UPDATE_SELF` — вызывает `_update_self`, обновляет `decision` результатом, затем `_record`.

13. **Строка 87-95**: `CREATE_GOAL` — вызывает `_create_goal`, обновляет `decision`, затем `_record`.

14. **Строка 97-100**: если действие не распознано (но оно уже нормализовано), возвращает `_record` с `applied=False` (так как `decision` не изменен). Это корректно.

15. **Строка 102-125**: `_update_self` — проверяет `analysis.get("self_update", False)`, если False, возвращает `applied=False`. Проверяет `importance < 0.75`, если да, возвращает `applied=False`. Проверяет `_is_user_owned`, если да, возвращает `applied=False`. Затем получает `proposal_type` из `IDENTITY_FIELDS` по `analysis.get("type")` (приводится к верхнему регистру). Если `proposal_type` None, возвращает `applied=False`. Проверяет `value` — должно быть непустой строкой. Создает `Proposal` с `evidence` списком, содержащим `f"cognitive:{item.id}"`, `evidence_count=1`. Вызывает `identity_manager.evaluate(proposal)`. Возвращает `applied` равным `result == "accepted"`, `identity_result`, reason.

16. **Строка 127-170**: `_create_goal` — проверяет `_is_user_owned`, если да, возвращает `applied=False`. Проверяет `importance < 0.70`, если да, возвращает `applied=False`. Проверяет `value` — непустая строка. Проверяет существование цели через `agent.goal_manager.get(goal_value)`, если есть, возвращает `applied=False` с `goal_status`. Если `goal_manager` отсутствует, возвращает `applied=False`. Иначе вызывает `add_candidate` и возвращает `applied=True` с `goal.to_dict()`.

17. **Строка 172-183**: `_is_user_owned` — проверяет `analysis.get("type")` начинается с `"USER_"` или `item.route == "USER_QUERY"`. Корректно.

18. **Строка 185-195**: `_importance` — преобразует `analysis.get("importance", 0.0)` в float, обрабатывает исключения, ограничивает от 0 до 1.

19. **Строка 197-220**: `_record` — создает `Event.create` с JSON-сериализацией `analysis` и `decision`, сохраняет в память через `self.memory.remember`. Возвращает словарь с `status`, `item_id`, `analysis`, `decision`.

### Проблемы:

1. **Строка 2-3**: Импорты `Proposal` и `Event` — если эти модули не существуют или имеют другие пути, будет ошибка импорта. Но это зависит от структуры проекта.

2. **Строка 23-29**: `__init__` — если `agent` не имеет атрибута `evidence`, будет AttributeError. Но `evidence` не используется в классе (только сохраняется в `self.evidence`). Это мертвый код? Проверим: в классе `self.evidence` нигде не используется. Это потенциально мертвый код.

3. **Строка 31-45**: `decide()` — если `analysis` не содержит ключа `"action"`, используется `"RETAIN"` — это нормально. Но если `analysis` не является словарем, будет ошибка. Нет проверки типа.

4. **Строка 47-55**: `IGNORE` — `_record` вызывается с `decision`, который имеет `applied=True`. Но `
