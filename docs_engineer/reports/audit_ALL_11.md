# Аудит ALL — батч 11

Файлы: eddie_server.py, epistemic_engine.py, epistemic_intent_detector.py
Модель: deepseek-v4-flash

Мы провели глубокий аудит двух файлов: core/eddie_server.py и core/epistemic_engine.py, а также core/epistemic_intent_detector.py. Ниже представлены находки по каждому файлу.

## core/eddie_server.py

### 1. Дублирование импортов в конце файла
- Строки 462-463: `import socketserver` и `import threading` повторяются после определения класса. Это не ошибка, но избыточно и нарушает стиль (импорты должны быть в начале). Удалить.

### 2. Потенциальная гонка при работе с `_clients` и `_unregister`
- В методе `broadcast` (строки ~130-150) после получения списка `targets` под блокировкой, затем итерация по `targets` и вызов `_unregister` для dead-клиентов. `_unregister` сам захватывает `_clients_lock`, что может привести к блокировке, если другой поток уже держит lock. Но это не deadlock, так как `_unregister` вызывается после освобождения lock в `broadcast` (lock уже отпущен). Однако есть гонка: между получением `targets` и вызовом `_unregister` другой поток может добавить/удалить клиентов, но это не критично. Но `_unregister` внутри `broadcast` вызывается без lock, что может привести к тому, что `_unregister` попытается удалить writer, который уже удален другим потоком, но это безопасно (проверка `if writer in self._clients`). В целом нормально.

### 3. Потенциальная утечка памяти: `_clients` хранит writer'ы, но не удаляет их при закрытии соединения, если `finish` не вызывается (например, при ошибке). Но `finish` вызывается автоматически при завершении handle, так что ок.

### 4. Обработка ошибок в `handle_user_message` – нет try/except, но вызывающий код в `handle` ловит исключение и отправляет error. Это нормально.

### 5. В `send_initiative` есть `if not self._clients: self.outbox.append(text)`. Но `self._clients` может быть непустым, но broadcast может не доставить (если клиенты мертвы). Тогда сообщение не попадет в outbox. Лучше проверять после broadcast, были ли доставки. Но это не критично.

### 6. В `check_pending_initiative` после фиксации отсутствия, `pending_initiative` устанавливается в None, но `pending["answered"] = True` уже не нужно, так как pending уже не используется. Это не ошибка.

### 7. В `flush_outbox` вызывается `self.push_initiative(text)`, но такого метода нет! Есть `send_initiative`. Ошибка: должно быть `self.send_initiative(text)`. Это критично: при подключении клиента, если есть outbox, вызовется несуществующий метод, что вызовет AttributeError. Это HIGH.

### 8. В `serve_forever` создается класс `Handler` внутри метода, и `server_ref = self` – это нормально. Но `Handler` использует `self._register(writer)` и т.д. В `handle` после чтения строки и обработки, если происходит исключение при записи ответа, то break, но writer не удаляется из _clients до вызова finish. finish вызывается автоматически при выходе из handle, так что ок.

### 9. В `handle` при получении `user_message`, если `text` пустой, continue. Но если payload не содержит "text", то text = "", continue. Ок.

### 10. В `broadcast` параметр `only_connected=True` – если False, то не отправляет? Логика: если `only_connected` False, то после отправки всем, функция просто возвращается, но не отправляет в outbox. Это странно, но не используется.

### 11. В `send_initiative` есть `winsound.Beep` – это Windows-only, на других ОС вызовет исключение, которое ловится. Ок.

### 12. В `note_eddie_arrived` и `note_eddie_left` используется `from memory.events import Event` внутри try, но если модуль не найден, исключение ловится. Ок.

### 13. В `__init__` импортируется datetime внутри, но это не проблема.

### 14. В `_now` используется `datetime.timezone.utc` – ок.

### 15. В `check_pending_initiative` текст формируется с `pending['text'][:120]` – если text короче 120, ок.

### 16. В `flush_outbox` – ошибка с `push_initiative` (см. пункт 7).

### 17. В `serve_forever` создается `Server` с `allow_reuse_address = True` и `daemon_threads = True`. Это ок.

### 18. В `handle` при получении строки, если она не JSON, continue. Ок.

### 19. В `handle` при обработке `user_message`, ответ отправляется writer'у, но если writer уже мертв, исключение ловится и break. Ок.

### 20. В `broadcast` после отправки, если `only_connected` True, то ничего не делает. Но если `only_connected` False, то не отправляет в outbox. Непонятно.

### 21. В `send_initiative` после broadcast, если клиентов нет, добавляет в outbox. Но если клиенты есть, но broadcast не доставил (все мертвы), то outbox не пополнится. Это может привести к потере инициативы. Рекомендуется проверять, были ли доставки.

### 22. В `check_pending_initiative` после фиксации, `pending_initiative` становится None, но `pending["answered"] = True` уже не нужно.

### 23. В `note_eddie_arrived` и `note_eddie_left` не используется `self.agent.memory.remember` если память не инициализирована? Но там try/except.

### 24. В `__init__` `self.outbox = []` – не потокобезопасно, но используется только в `flush_outbox` и `send_initiative`, которые могут вызываться из разных потоков (серверный поток и внешний). Нет блокировки для outbox. Это может привести к гонке. Рекомендуется добавить lock.

### 25. В `flush_outbox` вызывается `self.push_initiative` – это ошибка, как уже сказано.

## core/epistemic_engine.py

### 1. Импорт `from core.text_relevance_matcher import TextRelevanceMatcher` – предполагается, что модуль существует. Ок.

### 2. В `_belief_evidence_count` используется `connection.execute` с параметром `(value,)`, но в SQL запросе `lower(value) = lower(?)` – это сравнение с учетом регистра, но `value` может содержать пробелы, а в БД может быть нормализовано. Возможно, нужно нормализовать. Но это не критично.

### 3. В `analyze` для каждого belief вызывается `_belief_evidence_count`, который делает SQL запрос. Это может быть медленно, если beliefs много. Но это не баг.

### 4. В `relevant_unresolved_claims` используется `TextRelevanceMatcher.relevance`, который может вернуть `relevant` False, если нет совпадений. Ок.

### 5. В `render` формируется текст, но не используется `self.agent` – ок.

### 6. В `_significant_tokens` вызывается `TextRelevanceMatcher.tokens(value)`, но метод `tokens` может быть статическим? Не проверено.

### 7. В `_belief_evidence_count` есть `getattr(self.agent, "evidence", None)` – если у агента нет атрибута evidence, возвращается 0. Ок.

### 8. В `analyze` `beliefs = list(self_state.get("beliefs", []))` – если self_state не имеет ключа "beliefs", вернется пустой список. Ок.

### 9. В `relevant_unresolved_claims` сортировка по `-item["relevance"]` и `-item["priority"]` – приоритет меньше для supported? Но здесь только unresolved, у них priority 0.85, так что сортировка по relevance. Ок.

### 10. В `render` строки с "UNRESOLVED SELF-CLAIMS:" и т.д. – ок.

### 11. В `_normalize` используется `str(value or "").casefold().split()` – если value None, то "" – ок.

### 12. В `_significant_tokens` – `TextRelevanceMatcher.tokens(value)` – если value пустое, вернет пустое множество. Ок.

### 13. В `_belief_evidence_count` SQL запрос использует `lower(value) = lower(?)` – но если value содержит кавычки, это безопасно из-за параметризации. Ок.

### 14. В `analyze` для каждого belief создается EpistemicItem, но не проверяется, что belief – строка. Если belief не строка, `str(belief)` преобразует. Ок.

### 15. В `relevant_unresolved_claims` если `user_message` пустое, `_significant_tokens` вернет пустое множество, и функция вернет []. Ок.

### 16. В `render` не используется `self.agent` – ок.

### 17. В `_belief_evidence_count` используется `connection.execute` без контекстного менеджера, но это ок.

### 18. В `analyze` `items` – список EpistemicItem, но в `relevant_unresolved_claims` используется `item.value` и т.д. – ок.

### 19. В `relevant_unresolved_claims` `result.sort(key=lambda item: (-item["relevance"], -item["priority"]))` – если relevance одинаковые, сортировка по priority (меньше приоритет – выше? Но priority 0.85 для unresolved, так что все одинаковые). Ок.

### 20. В `render` есть строка "This layer describes the epistemic status of EddieAI's existing self-claims." – ок.

### 21. В `_belief_evidence_count` есть `lower(value) = lower(?)` – но если value содержит пробелы в начале/конце, то в БД может быть нормализовано. Возможно, нужно использовать `trim`. Но не критично.

### 22. В `analyze` `evidence_count` может быть 0, тогда статус UNVERIFIED. Но если evidence_count > 0, статус SUPPORTED. Это логично.

### 23. В `relevant_unresolved_claims` `relevance = TextRelevanceMatcher.relevance(user_message, item.value)` – если item.value длинное, может быть медленно. Ок.

### 24. В `render` `lines.extend([...])` – ок.

### 25. В `_significant_tokens` – `TextRelevanceMatcher.tokens` может быть не определен, если модуль не импортирован. Но импорт есть.

## core/epistemic_intent_detector.py

### 1. Импорт `re` – ок.

### 2. В `normalize` используется `re.sub(r"[^\w\sёЁ?!-]", " ", ...)` – это удаляет все символы, кроме букв, цифр, пробелов, ё, Ё, ?, !, -. Это может удалить точки, запятые, что может изменить смысл. Например, "откуда ты это узнал?" – после нормализации станет "откуда ты это узнал" (без ?). Но паттерны не содержат знаков препинания, так что ок.

### 3. В `detect` для каждого паттерна вызывается `cls.normalize(pattern)` – это нормализует паттерн, но паттерны уже нормализованы? Они содержат пробелы, но могут содержать "ё" и "е". normalize заменяет "ё" на "е"? Нет, в regex `\w` включает "ё"? В Python `\w` включает Unicode буквы, включая "ё". Так что ок.

### 4. В `detect` после проверки паттернов, есть generic-список. Условие `len(text.split()) <= 8` – если сообщение длинное, но содержит "почему", то не сработает. Это может быть ограничением, но не баг.

### 5. В `detect` возвращается `pattern` – для generic это None. Ок.

### 6. В `normalize` используется `str(text or "").casefold()` – если text None, то "" – ок.

### 7. В `detect` `normalized
