# Аудит ALL — батч 47

Файлы: retrieval.py, self_interpretation.py, source_evaluator.py
Модель: deepseek-v4-flash

Мы провели аудит трех файлов: memory/retrieval.py, memory/self_interpretation.py, memory/source_evaluator.py. Найдены следующие проблемы.

## memory/retrieval.py

1. **Строка 5-6**: `class MemoryRetrieval:` — нет docstring? Есть docstring, ок.
2. **Строка 13**: `def user_facts(self, limit: int = 20):` — вызывает `self.memory.get_knowledge(owner="USER", limit=limit)`. Предполагается, что `get_knowledge` возвращает список словарей с ключом 'content'. Это не проверено, но вероятно.
3. **Строка 20-27**: `shared_events` и `interactions` используют `SELECT *` — это может вернуть все колонки, включая потенциально чувствительные (например, `source`, `confidence`). Лучше выбирать только нужные поля. Также `SELECT *` может быть неэффективным.
4. **Строка 24**: `WHERE event_type = 'SHARED_EXPERIENCE'` — вероятно, в таблице events есть поле event_type. Но в `interactions` используется `source_type = 'DIRECT_INTERACTION'`. Возможно, это разные поля, но неясно. Если это разные поля, то запросы корректны. Но если это одно поле, то ошибка. Нужно проверить схему БД.
5. **Строка 35-36**: `build_memory_query_context` использует `reversed(facts)` и `reversed(interactions)` и `reversed(shared)`. Это предполагает, что списки упорядочены по id DESC (как в запросах). Но `user_facts` вызывает `get_knowledge` — неизвестно, в каком порядке возвращаются факты. Если `get_knowledge` возвращает в порядке возрастания id, то `reversed` даст новые сначала. Но если порядок другой, то может быть неверно. Лучше явно сортировать.
6. **Строка 38**: `lines.append("ПОДТВЕРЖДЁННЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ")` — заголовок на русском, но в коде смешанный стиль (английские строки в коде, русские в выводе). Это не баг, но стиль.
7. **Строка 47**: `f"- {fact['content']}"` — если `fact` не имеет ключа 'content', будет KeyError. Но предполагается, что get_knowledge возвращает словари с 'content'.
8. **Строка 61**: `f"- {event['content']}"` — аналогично.
9. **Строка 75**: `f"- {event['content']}"` — аналогично.
10. **Строка 80**: `return "\n".join(lines)` — ок.

Потенциальные проблемы:
- Нет обработки ошибок при обращении к БД.
- Нет проверки, что `self.memory.connection` существует.
- `SELECT *` — избыточность.
- Порядок `reversed` может быть неверным, если `get_knowledge` не сортирует.

## memory/self_interpretation.py

1. **Строка 1**: `import json` — ок.
2. **Строка 3**: `from memory.knowledge import Knowledge` — импорт внутри модуля, ок.
3. **Строка 5**: `MODEL_NAME = "phi4-mini"` — не используется в коде? Возможно, это для другого модуля. Но здесь не используется.
4. **Строка 7-11**: `MODEL_OPTIONS` — используется в `self.llm.chat(options=MODEL_OPTIONS)`. Ок.
5. **Строка 13**: `class SelfInterpretation:` — ок.
6. **Строка 15-20**: `__init__` — импортирует `CloudFirstLlm` внутри метода. Это нормально, но может быть медленно. Лучше импортировать наверху.
7. **Строка 22**: `self.llm = CloudFirstLlm(model_orchestrator)` — если `model_orchestrator` None, то что? Возможно, CloudFirstLlm принимает None? Неизвестно.
8. **Строка 24-31**: `interpret` — метод.
9. **Строка 27**: `sources = self._get_external_sources(query, limit)` — ок.
10. **Строка 29-34**: если нет источников, возвращает статус NO_SOURCES.
11. **Строка 36-48**: формирует `source_text` из источников. Использует `source['content']` и `source['source']`. В `_get_external_sources` возвращаются словари с ключами 'content', 'source', 'confidence', 'verified'. Ок.
12. **Строка 50-84**: формирует prompt. Внутри prompt есть JSON-схема. Ок.
13. **Строка 86-96**: вызывает `self.llm.chat(...)`. Передает `system`, `user`, `options`, `task="deep"`. Неизвестно, поддерживает ли CloudFirstLlm параметр `task`. Возможно, это лишнее.
14. **Строка 98**: `parsed = self._parse(raw)` — ок.
15. **Строка 100-106**: если parsed None, возвращает INVALID_MODEL_OUTPUT.
16. **Строка 108-113**: извлекает conclusion, если пусто — EMPTY_CONCLUSION.
17. **Строка 115-117**: `confidence = self._confidence(parsed.get("confidence", 0.0))` — ок.
18. **Строка 119-129**: извлекает supported_by, contradictions, limitations — списки строк.
19. **Строка 131-145**: формирует content.
20. **Строка 147-158**: создает Knowledge и сохраняет через `self.memory.remember_knowledge(knowledge)`.
21. **Строка 160-170**: возвращает результат.

Проблемы:
- **Строка 22**: `CloudFirstLlm` импортируется внутри `__init__`. Это может вызвать циклический импорт, если `identity.llm_access` импортирует что-то из memory. Лучше импортировать на уровне модуля.
- **Строка 86**: `task="deep"` — возможно, это не поддерживается. Нужно проверить сигнатуру `chat`.
- **Строка 108**: `conclusion = str(parsed.get("conclusion", "")).strip()` — если conclusion не строка, а число, то str() преобразует. Ок.
- **Строка 115**: `confidence = self._confidence(parsed.get("confidence", 0.0))` — если confidence отсутствует, берется 0.0, потом _confidence вернет 0.2 (так как float(0.0) = 0.0, но потом max/min? В _confidence: try float(value) except return 0.2. Если value=0.0, то float(0.0)=0.0, затем max(0.0, min(1.0, 0.0)) = 0.0. Так что вернет 0.0. Но если value не число, вернет 0.2. Это нормально.
- **Строка 119-129**: `supported_by = [str(item) for item in parsed.get("supported_by", [])]` — если supported_by не список, а строка, то будет итерация по символам. Лучше проверить тип.
- **Строка 131**: `content = f"Мой вывод по запросу '{query}': {conclusion}"` — если query содержит кавычки, может быть проблема. Но это не критично.
- **Строка 147**: `Knowledge(...)` — параметры: content, owner="SELF", source_type="SELF_INTERPRETATION", source=... , confidence, verified=False, personal_experience=False. Неизвестно, есть ли обязательные поля. Возможно, нужно передать больше.
- **Строка 151**: `self.memory.remember_knowledge(knowledge)` — метод должен существовать.
- **Строка 160**: возвращает словарь с ключами status, sources, interpretation. Ок.

- **Метод `_get_external_sources`** (строка 174-198): использует `LIKE ?` с `%{query}%`. Это может быть неэффективно и небезопасно (SQL-инъекции? Нет, параметризовано). Но LIKE с подстановочными знаками может вернуть много лишнего. Лучше использовать полнотекстовый поиск или другие методы.
- **Строка 181**: `WHERE owner = 'EXTERNAL' AND source_type = 'WEB_SEARCH'` — предполагается, что такие записи есть.
- **Строка 184**: `ORDER BY id DESC` — ок.
- **Строка 186**: `LIMIT ?` — ок.
- **Строка 188-197**: возвращает список словарей. Ок.

- **Метод `_parse`** (строка 200-240): обрабатывает JSON, обрезает ```json и ```. Ок.
- **Метод `_confidence`** (строка 242-252): ок.

Потенциальные проблемы:
- Нет обработки ошибок при вызове LLM (сеть, таймаут). Если LLM недоступен, будет исключение.
- Нет логирования.
- Нет проверки, что `self.memory.connection` существует.
- `MODEL_NAME` не используется — возможно, лишний.

## memory/source_evaluator.py

1. **Строка 1**: `from dataclasses import dataclass` — ок.
2. **Строка 2**: `from urllib.parse import urlparse` — ок.
3. **Строка 4-10**: `@dataclass class EvaluatedSource` — ок.
4. **Строка 12**: `class SourceEvaluator:` — ок.
5. **Строка 14-19**: docstring — ок.
6. **Строка 21-31**: HIGH_TRUST_DOMAINS — есть дубликат "nasa.gov" (дважды). Это не баг, но лишнее.
7. **Строка 33-38**: MEDIUM_TRUST_DOMAINS — ок.
8. **Строка 40-46**: LOW_TRUST_DOMAINS — ок.
9. **Строка 48-53**: LOW_QUALITY_TERMS — ок.
10. **Строка 55-70**: SCIENCE_TERMS — ок.
11. **Строка 72-82**: `__init__` — ок.
12. **Строка 84-100**: `evaluate` — ок.
13. **Строка 102-109**: `accepted` — ок.
14. **Строка 111-...**: `_evaluate_one` — большая функция.

Проблемы:
- **Строка 21-31**: дубликат "nasa.gov" — не критично, но можно убрать.
- **Строка 111**: `_evaluate_one` — много магических чисел (0.35, 0.15, -0.20, 0.15, -0.15, 0.05, 0.10, -0.55, -0.10). Лучше вынести в константы.
- **Строка 113**: `score = 0.5` — стартовое значение.
- **Строка 116**: `domain = self._domain(url)` — ок.
- **Строка 119**: `title_lower = title.lower()` — ок.
- **Строка 120**: `query_lower = query.lower()` — ок.
- **Строка 122**: `source_class = "unknown"` — ок.
- **Строка 125-139**: проверка доменов. Использует `_matches_domain`. Ок.
- **Строка 141-157**: релевантность. Вычисляет overlap. Использует `_terms`. Ок.
- **Строка 159-166**: научный сигнал. Ок.
- **Строка 168-176**: низкокачественный контент. Ок.
- **Строка 178-187**: видео сигнал. Ок.
- **Строка 189-196**: нормализация score. Ок.
- **Строка 198-204**: accepted. Ок.
- **Строка 206-214**: возврат EvaluatedSource. Ок.

- **Метод `_domain`** (строка 216-232): использует urlparse, убирает www. Ок.
- **Метод `_matches_domain`** (строка 234-240): провер
