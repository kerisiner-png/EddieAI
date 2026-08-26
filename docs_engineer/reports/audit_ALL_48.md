# Аудит ALL — батч 48

Файлы: tool_experience.py, night_run.py, super_system_stress_test.py
Модель: deepseek-v4-flash

Мы провели аудит трёх файлов: memory/tool_experience.py, night_run.py, super_system_stress_test.py. Ниже подробный разбор.

## memory/tool_experience.py

### Общее
Файл небольшой, реализует запись опыта от инструментов в память. Стиль кода: многострочные вызовы с переносами, что несколько необычно, но допустимо. Проблемы:

1. **Несоответствие сигнатуры `record` и использования `action.action_type`**  
   В `record` параметр `action` — объект, у которого ожидается атрибут `action_type` и `target`. Но в `_build_content` используется `action.target`. Если `action` не имеет этих атрибутов, будет ошибка. Это хрупкое место, но предполагается, что action — это объект действия. Однако в `record` параметр `action` не аннотирован, и нет проверки. Это MEDIUM.

2. **Дублирование кода построения content**  
   В `record` и `_build_content` повторяется логика получения `status` и `tool`. Можно вынести в отдельный метод. Это LOW (стиль).

3. **Не обрабатывается случай, когда `result` не dict**  
   В `record` вызывается `result.get(...)`, но если `result` не dict, будет AttributeError. В `_build_content` тоже. Нет проверки типа. Это HIGH, так как может упасть при неверном вызове.

4. **Не используется `knowledge` после создания**  
   В `record` создается объект `Knowledge`, но он не передается в память (memory.remember принимает только event). Возможно, это задумано, но тогда зачем создавать? Может быть, нужно сохранять knowledge отдельно? Это потенциальная логическая ошибка: knowledge создается, но не используется. Это MEDIUM.

5. **Стиль: множественные переносы строк**  
   Например, `confidence=(1.0 if status == "OK" else 0.3)` разбито на несколько строк, что ухудшает читаемость. Это LOW.

6. **Нет обработки ошибок при записи в память**  
   `self.memory.remember(event)` может бросить исключение, но оно не обрабатывается. Это LOW.

7. **Отсутствие docstring для `_build_content`** — LOW.

8. **Потенциальная утечка данных**  
   В `_build_content` при наличии `results` (список) берутся первые 5 элементов и формируются строки с title и url. Если url содержит конфиденциальные данные, они попадут в память. Но это скорее бизнес-логика.

9. **Импорты**  
   `from memory.events import Event` и `from memory.knowledge import Knowledge` — ок.

10. **Несоответствие типов**  
   `personal_experience` передается в Event и Knowledge, но в Knowledge параметр называется `personal_experience`, а в Event тоже. Ок.

11. **Отсутствие проверки, что `action` не None** — LOW.

12. **В `_build_content` при `payload` не dict, а, например, строка, то возвращается общий текст со статусом, но не используется содержимое. Это нормально.

13. **В `record` возвращается словарь с event и knowledge, но knowledge не сохраняется. Возможно, это ошибка: knowledge должен быть передан в memory.remember?**  
   В других частях проекта, вероятно, knowledge сохраняется отдельно. Но здесь только event. Это может быть намеренно, но выглядит подозрительно.

### Конкретные строки:
- Строка 20: `action.action_type` — предполагается, что action имеет этот атрибут.
- Строка 24: `action.target` — аналогично.
- Строка 31: `result.get("status", "UNKNOWN")` — если result не dict, упадет.
- Строка 35: `result.get("tool", action.action_type)` — тоже.
- Строка 44: `Event.create(...)` — ок.
- Строка 61: `Knowledge(...)` — создается, но не используется.
- Строка 76: `return {"event": event, "knowledge": knowledge}` — knowledge возвращается, но не сохраняется.

### Вывод по файлу:
- HIGH: отсутствие проверки типа result.
- MEDIUM: создание Knowledge без использования; хрупкость action.
- LOW: стиль, дублирование.

## night_run.py

### Общее
Скрипт для ночного запуска автономии. Использует абсолютные пути Windows (C:\EddieAI), что делает его непереносимым. Также есть проблемы с безопасностью, утечками, логикой.

1. **Жестко заданные пути**  
   `sys.path.insert(0, r"C:\EddieAI")`, `LOG = r"C:\EddieAI\logs\eddie_night.log"`, `r"file:C:\EddieAI\data\memory.db?mode=ro"` — это делает скрипт неработоспособным на других системах. Это HIGH (переносимость).

2. **Использование `sys.path.insert`**  
   Вставка пути в начало sys.path — это хрупко, лучше использовать относительные пути или переменные окружения. MEDIUM.

3. **Открытие базы данных в режиме read-only через URI**  
   `sqlite3.connect(r"file:C:\EddieAI\data\memory.db?mode=ro", uri=True)` — это нормально, но путь захардкожен.

4. **Потенциальная гонка при записи лога**  
   Функция `log` открывает файл каждый раз в режиме append. Это нормально, но если несколько процессов пишут, возможны конфликты. LOW.

5. **Использование `_cloud_chat` (приватный атрибут)**  
   `agent.model_orchestrator._cloud_chat` — обращение к приватному атрибуту, что хрупко. Если изменится имя, скрипт сломается. MEDIUM.

6. **Модификация глобального `ollama.chat`**  
   `ollama.chat = _cloud_bridge_chat` — это глобальная подмена, которая влияет на весь процесс. После завершения скрипта не восстанавливается. Это может вызвать проблемы, если скрипт используется как модуль. HIGH (побочные эффекты).

7. **Логика `_cloud_bridge_chat`**  
   - Если бюджет исчерпан, возвращает пустой ответ. Это нормально.
   - Собирает system и user из messages, но не учитывает другие роли (например, assistant). Это может потерять контекст.
   - Вызывает `limited_cloud` с `task="deep"` — это может быть неверно для всех случаев.
   - Если `limited_cloud` возвращает None, то `result = ""`, и возвращается пустой контент. Это может привести к пустым ответам.
   - Не передает `model` и другие параметры. Это может нарушить работу.

8. **Проверка разрешения на исследование**  
   Используется `_perm_exists` — запрос `SELECT COUNT(*) FROM events WHERE source='Eddie' AND content LIKE '%выходить за обычные лимиты%'`. Это хрупко: если текст изменится, разрешение не найдется. MEDIUM.

9. **Запись события о разрешении**  
   Создается Event с source="Eddie", но это не проверяется, что Eddie — реальный пользователь. Возможно, это подделка. Но это внутренний скрипт.

10. **Проверка `recent_system`**  
   Аналогично, ищет событие с content LIKE '%до 11:00 утра%'. Хрупко.

11. **Использование `runtime.start_background_loop()`**  
   Возвращает статус, но не проверяется, что статус успешный. LOW.

12. **Цикл ожидания**  
   `time.sleep(min(20.0, max(1.0, remaining)))` — если remaining отрицательный, то max(1.0, remaining) даст 1.0, но потом цикл завершится по условию. Ок.

13. **Обработка finally**  
   В finally вызывается `runtime.stop_background_loop()`, затем консолидация, затем `agent.close()`. Но если `runtime` не был создан (например, ошибка при создании), то `runtime` не определен, и будет NameError. Это HIGH: если `AutonomyRuntimeFactory` бросит исключение, то `runtime` не будет, и finally упадет.

14. **Импорт `sqlite3 as _sq`**  
   Дублируется импорт sqlite3 (уже есть `import sqlite3`). Это не ошибка, но лишнее.

15. **Использование `_start_event_id`**  
   Получает MAX(id) из events до начала, чтобы потом консолидировать только новые события. Но если в базе нет событий, row[0] будет None, и _start_event_id останется 0. Это нормально.

16. **Потенциальная утечка секретов**  
   В скрипте нет секретов, но путь к базе данных и лог-файл могут содержать чувствительные данные. LOW.

17. **Отсутствие обработки ошибок при работе с БД**  
   Если БД недоступна, скрипт упадет. LOW.

18. **Стиль**  
   Многострочные вызовы, но в целом читаемо.

### Конкретные строки:
- Строка 7: `sys.path.insert(0, r"C:\EddieAI")` — хардкод.
- Строка 10: `LOG = r"C:\EddieAI\logs\eddie_night.log"` — хардкод.
- Строка 17: `def log(msg):` — ок.
- Строка 30: `from core.agent import Agent` — зависит от sys.path.
- Строка 34: `runtime = AutonomyRuntimeFactory(...)` — если упадет, то runtime не определен.
- Строка 42: `original_cloud = agent.model_orchestrator._cloud_chat` — приватный атрибут.
- Строка 51: `agent.model_orchestrator._cloud_chat = limited_cloud` — подмена.
- Строка 56: `import ollama` — импорт внутри кода, лучше в начале.
- Строка 58: `_original_ollama_chat = ollama.chat` — сохраняется, но не восстанавливается.
- Строка 61: `def _cloud_bridge_chat(*args, **kwargs):` — функция.
- Строка 90: `ollama.chat = _cloud_bridge_chat` — глобальная подмена.
- Строка 96: `from core.night_consolidation import NightConsolidator` — импорт.
- Строка 100: `import sqlite3 as _sq` — дублирование.
- Строка 103: `_check = _sq.connect(r"file:C:\EddieAI\data\memory.db?mode=ro", uri=True)` — хардкод.
- Строка 110: `row = _check.execute("SELECT MAX(id) FROM events").fetchone()` — ок.
- Строка 116: `_perm_exists = _check.execute(...)` — хрупкий LIKE.
- Строка 123: `if not _perm_exists:` — запись разрешения.
- Строка 143: `conn = sqlite3.connect(r"file:C:\EddieAI\data\memory.db?mode=ro", uri=True)` — снова хардкод.
- Строка 149: `recent_system = conn.execute(...)` — хрупкий LIKE.
- Строка 158: `if recent_system == 0:` — запись события.
- Строка 174: `status = runtime.start_background_loop()` — если runtime не создан, упадет.
- Строка 176: `try: while True:` — цикл.
- Строка 190: `finally: runtime.stop_background_loop()` — если runtime не определен, будет ошибка.
- Строка 196: `consolidator = NightConsolidator(...)` — если agent не создан, тоже проблема.
- Строка 211: `agent.close()` — ок.

### Вывод по файлу:
- HIGH: хардкод путей, глобальная подмена ollama.chat без восстановления, возможный NameError в finally.
- MEDIUM: обращение к приватным атрибутам, хрупкие LIKE-запросы, дублирование импорта.
- LOW: стиль, отсутствие обработки ошибок.

## super_system
