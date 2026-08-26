# Аудит ALL — батч 44

Файлы: evidence.py, external_knowledge.py, knowledge.py
Модель: deepseek-v4-flash

Мы провели глубокий аудит трех файлов: memory/evidence.py, memory/external_knowledge.py, memory/knowledge.py. Ниже представлены находки по каждому файлу.

## memory/evidence.py

### Найденные проблемы:

1. **Строка 1-2**: Импорт `from dataclasses import dataclass` и `from datetime import datetime, timezone` — ок. Но `import math` используется в `get()` для `math.exp` — ок.

2. **Строка 8-9**: Импорт `from memory.provenance import source_weight, validate_source` — предполагается, что эти функции существуют. Не проверено, но это внешняя зависимость.

3. **Строка 12-20**: `@dataclass EvidenceRecord` — поля: category, value, count, weighted_score, confidence, source_types, first_seen, last_seen. Все типы корректны.

4. **Строка 22-27**: Докстринг класса EvidenceEngine — ок.

5. **Строка 29-31**: `__init__` вызывает `_ensure_table()`. ОК.

6. **Строка 33-55**: `_ensure_table()`:
   - Создает таблицу `evidence_events` с полями: id, category, value, source, weight, event_id, independence_key, created_at.
   - Затем проверяет наличие колонки `independence_key` через PRAGMA table_info. Если нет — ALTER TABLE ADD COLUMN. Это нормально для миграции.
   - Но есть потенциальная проблема: если таблица уже существует, но в ней нет колонки `independence_key`, ALTER TABLE добавит её. Однако если таблица существует и колонка есть, то ничего не делается. В целом ок.
   - **Проблема**: `self.memory.connection.execute(""" CREATE TABLE IF NOT EXISTS ... """)` — не указаны типы для `event_id` и `independence_key`? В SQLite типы необязательны, но лучше указать. Не критично.
   - **Проблема**: `self.memory.connection.commit()` вызывается после ALTER TABLE, но не после CREATE TABLE IF NOT EXISTS? На самом деле CREATE TABLE IF NOT EXISTS не требует коммита, но commit вызывается в конце — ок.

7. **Строка 57-91**: `add()`:
   - `validate_source(source)` — предполагается, что эта функция проверяет допустимость источника. ОК.
   - `now = datetime.now(timezone.utc).isoformat()` — корректно.
   - `weight = source_weight(source)` — получаем вес.
   - INSERT с параметрами — ок.
   - `self.memory.connection.commit()` — ок.
   - Возвращает `self.get(category, value)` — это вызовет повторный SELECT и создаст EvidenceRecord. Это нормально, но неэффективно: можно было бы сразу сформировать запись, но это не баг.
   - **Потенциальная проблема**: если `get()` вызовет ошибку (например, если запись не найдена), то после INSERT и commit запись должна быть, так что ошибки не будет. Но если `get()` упадет по другой причине, то запись уже вставлена, а метод вернет ошибку. Это не страшно.

8. **Строка 93-151**: `get()`:
   - Выполняет SELECT * WHERE category = ? AND value = ? ORDER BY id ASC.
   - Если rows пусто — raise ValueError.
   - `count = len(rows)` — количество записей.
   - `weighted_score = sum(row["weight"] for row in rows)` — сумма весов.
   - `source_types = sorted({row["source"] for row in rows if row["weight"] > 0})` — уникальные источники с положительным весом.
   - `independence_keys = { (row["independence_key"] if row["independence_key"] else row["source"]) for row in rows if row["weight"] > 0 }` — множество ключей независимости. Если independence_key пустой, используется source.
   - `diversity_bonus = min(1.0, len(independence_keys) / 3.0)` — бонус за разнообразие.
   - `repetition_signal = 1.0 - math.exp(-weighted_score / 3.0)` — сигнал повторения.
   - `confidence = round(repetition_signal * 0.7 + diversity_bonus * 0.3, 3)` — итоговая уверенность.
   - Возвращает EvidenceRecord.
   - **Проблема**: `first_seen=rows[0]["created_at"]`, `last_seen=rows[-1]["created_at"]` — так как rows отсортированы по id ASC, то first_seen — самая ранняя, last_seen — самая поздняя. Но если created_at не монотонно с id? В целом id автоинкремент, created_at ставится в момент вставки, так что порядок совпадает. Но если вставляли с явным id? Не предусмотрено. ОК.
   - **Проблема**: `source_types` — это множество источников, но в EvidenceRecord поле называется `source_types` (множественное число). ОК.
   - **Потенциальная проблема**: `independence_keys` — множество, но если в разных записях independence_key одинаковый, то они считаются одним независимым источником. Это логично.
   - **Проблема**: `diversity_bonus` вычисляется на основе количества уникальных independence_keys, но если independence_key не задан, то используется source. Это может привести к тому, что разные источники с одинаковым source (например, "SELF_OBSERVATION") будут считаться одним независимым ключом, что снижает diversity_bonus. Возможно, это задумано, но стоит проверить.
   - **Проблема**: `repetition_signal` использует `weighted_score / 3.0` — магическое число 3.0. Не объяснено, почему именно 3.0. Это может быть эвристика, но лучше вынести в константу.
   - **Проблема**: `confidence` может быть >1? repetition_signal от 0 до 1 (так как exp(-x) от 0 до 1, значит 1 - exp(-x) от 0 до 1). diversity_bonus от 0 до 1. Сумма с весами 0.7 и 0.3 даст от 0 до 1. ОК.

9. **Строка 153-166**: `all_records()`:
   - SELECT DISTINCT category, value FROM evidence_events WHERE weight > 0.
   - Для каждой пары вызывает `self.get(category, value)`.
   - **Проблема**: если есть записи с weight = 0, они не попадут в выборку. Это может быть намеренно (игнорировать нулевые веса). Но если weight = 0, то запись не должна учитываться? Возможно, это фильтр для исключения невалидных. ОК.
   - **Проблема**: `self.get()` внутри цикла — это N+1 запросов. Для большого количества записей может быть медленно. Но это не баг, а неэффективность.

10. **Строка 168-180**: `strong_candidates()`:
    - Фильтрует all_records по confidence >= minimum_confidence и weighted_score >= minimum_weighted_score.
    - ОК.

### Дополнительные замечания:
- **Стиль**: В целом соблюден PEP8, но есть длинные строки (например, строка 133-134). Не критично.
- **Комментарии**: В строках 108-111 комментарий на русском, но с искаженными символами (вопросы). Видимо, проблема кодировки при копировании. В реальном коде, вероятно, нормальный текст.
- **Безопасность**: SQL-запросы используют параметризацию, что защищает от инъекций. ОК.
- **Утечки**: Нет утечек памяти или секретов.
- **Мертвый код**: Нет.

### Итог по evidence.py:
Проблемы в основном низкой серьезности: магические числа, неэффективность, потенциальная неоднозначность с independence_key. Критических багов не обнаружено.

## memory/external_knowledge.py

### Найденные проблемы:

1. **Строка 1-2**: Импорты — ок.
2. **Строка 4**: `from memory.knowledge import Knowledge` — ок.
3. **Строка 6-11**: `@dataclass ExternalKnowledgeRecord` — поля: query, title, url, source, verified. ОК.
4. **Строка 13-18**: Класс ExternalKnowledgeRecorder, докстринг — ок.
5. **Строка 20-22**: `__init__` — ок.
6. **Строка 24-107**: `record()`:
   - Проверяет `result.get("status") != "OK"` — если не OK, возвращает [].
   - Получает query, items.
   - Для каждого item:
     - title = str(item.get("title", "")).strip()
     - url = str(item.get("url", "")).strip()
     - if not url: continue — пропускает без url.
     - snippet = str(item.get("text", "")).strip()
     - Формирует content: если snippet есть, то добавляет "Содержание: {snippet[:600]}", иначе просто заголовок и url.
     - Создает Knowledge с owner="EXTERNAL", source_type="WEB_SEARCH", source=url, confidence=0.5, verified=False, personal_experience=False.
     - Вызывает `self.memory.remember_knowledge(knowledge)`.
     - Добавляет ExternalKnowledgeRecord в records.
   - Возвращает records.

**Проблемы**:
- **Строка 35**: `query = result.get("query", "")` — если query пустой, то в content будет "Внешний источник по запросу '': ...". Это некрасиво, но не баг.
- **Строка 47**: `snippet[:600]` — обрезает до 600 символов. ОК.
- **Строка 52-58**: Формирование content. Если snippet пустой, то content без содержания. ОК.
- **Строка 60-67**: Создание Knowledge. Параметр `source=url` — источником является URL. Это логично.
- **Строка 69**: `self.memory.remember_knowledge(knowledge)` — предполагается, что метод существует. Не проверено.
- **Строка 72-81**: Создание ExternalKnowledgeRecord. Поле `source=url` — дублирует url. ОК.
- **Потенциальная проблема**: `result.get("results", [])` — если results не список, а что-то другое, то итерация может упасть. Но предполагается, что это список.
- **Проблема**: `self.memory.remember_knowledge(knowledge)` может вернуть что-то, но результат не используется. ОК.
- **Проблема**: Если `remember_knowledge` выбросит исключение, то запись не будет добавлена в records, и метод прервется. Это может быть нежелательно, но не баг.
- **Проблема**: Нет обработки дубликатов. Если один и тот же URL уже сохранен, будет создана новая запись Knowledge. Возможно, стоит проверять.
- **Проблема**: `confidence=0.5` — фиксированное значение. Может быть, стоит вычислять на основе чего-то.
- **Проблема**: `verified=False` — всегда false. ОК.

### Итог по external_knowledge.py:
Проблемы низкой серьезности: отсутствие обработки дубликатов, фиксированная confidence, потенциальные проблемы с типами. Критических нет.

## memory/knowledge.py

### Найденные проблемы:

1. **Строка 1-2**: Импорты — ок.
2. **Строка 4-15**: `@dataclass Knowledge`:
   - Поля: content, owner, source_type, source (default None), confidence (default 1.0), verified (default False), personal_experience (default False).
   - Метод `to_dict()` возвращает asdict(self).
   - **Проблема**: Нет валидации полей. Например, confidence может быть >1 или <0. Но это не баг, а отсутствие проверок.
   - **Проблема**: `source` может быть None, но в некоторых местах ожидается строка. ОК.
   - **Проблема**: `to_dict()` использует `asdict` — это стандартно.

### Итог по knowledge.py:
Проблем нет, кроме отсутствия валидации.

## Общие
