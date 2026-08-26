# Аудит ALL — батч 23

Файлы: final_regression_suite.py, full_system_stress_test.py, action_choice.py
Модель: deepseek-v4-flash

Мы провели аудит трёх файлов: final_regression_suite.py, full_system_stress_test.py, identity/action_choice.py. Ниже представлены находки.

## final_regression_suite.py

### 1. Строка 1: `from pathlib import Path` — импорт не используется? 
В файле используется `Path` в `ROOT = Path("data") / "final_regression_suite"`, так что импорт нужен.

### 2. Строка 5-10: удаление и создание каталога
```python
if ROOT.exists():
    shutil.rmtree(ROOT, ignore_errors=True)
ROOT.mkdir(parents=True, exist_ok=True)
```
Потенциальная проблема: если `ROOT` существует и является файлом, `shutil.rmtree` вызовет ошибку (не игнорируется). Но `ignore_errors=True` подавляет ошибки, но тогда `mkdir` может не сработать, если путь занят файлом. Это маловероятно, но лучше проверить `is_dir()`. Серьёзность: LOW.

### 3. Строка 14: `passed = 0; failed = 0` — глобальные переменные, используются в `run_test`. Нормально.

### 4. Строка 18-31: `run_test` — перехватывает все исключения, но не выводит traceback в случае успеха. ОК.

### 5. Строка 39-67: `test_evidence_independence` — использует `memory.connection.execute` напрямую. Это может быть хрупко, если схема БД изменится. Но тест проверяет конкретную таблицу. Нормально.

### 6. Строка 52: `assert record.confidence == 0.742` — жёстко заданное значение. Если алгоритм изменится, тест сломается. Это ожидаемо для регрессионного теста.

### 7. Строка 70-133: `test_lifecycle` — использует `getattr(trait.status, "value", trait.status)` для совместимости с Enum или строкой. Нормально.

### 8. Строка 136-226: `test_habit_pipeline` — использует юникод-экранирование для русских строк. Это допустимо, но ухудшает читаемость. Не ошибка.

### 9. Строка 172: `first[0]["observations"] == 10` — предполагается, что детектор вернёт список с хотя бы одним элементом. Если детектор вернёт пустой список, будет IndexError. Но тест ожидает, что детектор найдёт паттерн. Нормально.

### 10. Строка 180: `record_1.confidence == 0.775` — жёсткое значение.

### 11. Строка 186: `second[0]["created_evidence"] == 0` — проверка идемпотентности.

### 12. Строка 228-300: `test_belief_pipeline` — аналогично.

### 13. Строка 302-350: `test_identity_manager` — проверяет, что повторное предложение отклоняется как "already_present". ОК.

### 14. Строка 352-500: `test_unified_agent_loop` — создаёт экземпляр `AgentLoop` через `__new__` и вручную устанавливает атрибуты. Это хрупко: если `AgentLoop` изменит внутреннюю структуру, тест сломается. Лучше использовать реальный конструктор с моками. Серьёзность: MEDIUM.

### 15. Строка 502-540: `test_production_runtime` — запускает подпроцесс `test_production_runtime.py`. Если файл не существует, будет ошибка. Но предполагается, что он есть. ОК.

### 16. Строка 555-580: запуск тестов. В конце `sys.exit(1)` при наличии ошибок. Нормально.

### 17. Общее: тесты используют реальные БД в каталоге `data/final_regression_suite`, который удаляется в начале. Это нормально.

### 18. Строка 1: `from pathlib import Path` — импорт используется.

### 19. Строка 3: `import sys` — используется в `sys.exit` и `sys.executable`.

### 20. Строка 4: `import traceback` — используется.

### 21. Строка 7: `ROOT = Path("data") / "final_regression_suite"` — относительный путь. Если запускать из другого каталога, может быть не туда. Лучше использовать `Path(__file__).parent`. Серьёзность: LOW.

### 22. Строка 14: `passed = 0` — глобальная переменная, но в `run_test` она изменяется через `global`. Нормально.

### 23. Строка 18-31: `run_test` — если функция `fn` возвращает значение, оно игнорируется. Нормально.

### 24. Строка 39: `memory = Memory(db)` — предполагается, что `Memory` принимает путь к файлу БД. ОК.

### 25. Строка 41: `evidence = EvidenceEngine(memory)` — предполагается, что `EvidenceEngine` принимает `Memory`. ОК.

### 26. Строка 44-50: `evidence.add(...)` — параметры: `category`, `value`, `source`, `event_id`, `independence_key`. Возможно, сигнатура `add` другая? Но тест написан под текущий код.

### 27. Строка 52: `record.count == 3` — предполагается, что `record` имеет атрибут `count`. ОК.

### 28. Строка 53: `record.weighted_score == 3.0` — предполагается.

### 29. Строка 54: `record.confidence == 0.742` — жёсткое значение.

### 30. Строка 56: `record.source_types == ["SELF_INTERPRETATION"]` — предполагается, что это список уникальных типов источников.

### 31. Строка 60-67: SQL-запрос к `evidence_events` — проверяет количество записей. ОК.

### 32. Строка 70: `test_lifecycle` — использует `SelfState` с путём к JSON-файлу. ОК.

### 33. Строка 73: `PersonalityHistory(memory)` — предполагается, что принимает `memory`. ОК.

### 34. Строка 76: `lifecycle.promote(...)` — параметры: `field`, `value`, `strength`, `confidence`, `evidence_count`. ОК.

### 35. Строка 82-86: `trait.strength == 0.20` и `trait.confidence == 0.20` — жёсткие значения.

### 36. Строка 88-92: `getattr(trait.status, "value", trait.status) == "DORMANT"` — предполагается, что `status` может быть Enum или строкой.

### 37. Строка 94-98: `lifecycle.reinforce(...)` — параметры: `field`, `value`, `amount`. ОК.

### 38. Строка 100-104: после первого reinforce статус "WEAKENING" — странно, что после усиления статус ослабевает? Возможно, это логика жизненного цикла: сначала ослабление, потом усиление? Но тест ожидает именно такую последовательность. Это может быть ошибкой в логике, но тест фиксирует текущее поведение.

### 39. Строка 106-110: после второго reinforce статус "EMERGING".

### 40. Строка 112-116: после третьего reinforce статус "ACTIVE".

### 41. Строка 118-124: `lifecycle.contradict(...)` — параметры: `field`, `value`, `amount`. После противоречия статус "DORMANT" и `contradictions == 1`. ОК.

### 42. Строка 136: `test_habit_pipeline` — использует `Event.create(...)` с параметрами: `content`, `event_type`, `source_type`, `source`, `personal_experience`, `confidence`, `verified`. ОК.

### 43. Строка 172: `first[0]["observations"] == 10` — предполагается, что `detect()` возвращает список словарей с ключом "observations". ОК.

### 44. Строка 174: `first[0]["distinct_targets"] == 10` — аналогично.

### 45. Строка 176: `first[0]["created_evidence"] == 10` — аналогично.

### 46. Строка 178: `evidence.get("habit", "repeated_action:research")` — предполагается, что `get` возвращает объект с атрибутами `count`, `confidence`, `weighted_score`. ОК.

### 47. Строка 180: `record_1.confidence == 0.775` — жёсткое значение.

### 48. Строка 184: `second[0]["created_evidence"] == 0` — идемпотентность.

### 49. Строка 186: `record_2.count == 10` — после повторного вызова count не изменился.

### 50. Строка 188: `record_2.weighted_score == 10.0` — жёсткое значение.

### 51. Строка 228: `test_belief_pipeline` — использует `Knowledge(...)` с параметрами: `content`, `owner`, `source_type`, `source`, `confidence`, `verified`, `personal_experience`. ОК.

### 52. Строка 252: `first[0]["observations"] == 3` — ожидается 3 наблюдения.

### 53. Строка 254: `first[0]["distinct_sources"] == 3` — ожидается 3 уникальных источника.

### 54. Строка 256: `first[0]["created_evidence"] == 9` — ожидается 9 созданных свидетельств (3 наблюдения × 3 источника?).

### 55. Строка 260: `record_1.count == 9` — ожидается 9.

### 56. Строка 262: `record_1.confidence == 0.965` — жёсткое значение.

### 57. Строка 266: `second[0]["created_evidence"] == 0` — идемпотентность.

### 58. Строка 268: `record_2.count == 9` — не изменилось.

### 59. Строка 270: `record_2.confidence == record_1.confidence` — проверка стабильности.

### 60. Строка 302: `test_identity_manager` — создаёт `Proposal` с параметрами: `proposal_type`, `value`, `reason`, `confidence`, `evidence`, `evidence_count`. ОК.

### 61. Строка 316: `first == "accepted"` — ожидается строка "accepted".

### 62. Строка 320: `second == "already_present"` — ожидается строка "already_present".

### 63. Строка 324: `preferences.count("test:identity") == 1` — проверка, что значение добавлено один раз.

### 64. Строка 352: `test_unified_agent_loop` — создаёт `AgentLoop.__new__(AgentLoop)` и вручную устанавливает атрибуты. Это очень хрупко. Если `AgentLoop` имеет `__init__`, который инициализирует другие атрибуты, они не будут установлены. Лучше использовать `unittest.mock` или создать реальный объект с моками зависимостей. Серьёзность: HIGH.

### 65. Строка 370: `loop.action_preference_detector = None` — устанавливает атрибут в None, но в `_process_identity_detectors` может быть обращение к этому атрибуту. Если код ожидает, что это не None, будет ошибка. Но тест, видимо, предполагает, что этот детектор не используется. ОК.

### 66. Строка 372-378: установка других атрибутов.

### 67. Строка 380: `first = loop._process_identity_detectors()` — вызывает приватный метод. Это допустимо для теста, но хрупко.

### 68. Строка 382-390: проверки, что есть habit и belief с результатом "accepted".

### 69. Строка 392-400: проверки, что при
