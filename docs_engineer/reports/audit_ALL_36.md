# Аудит ALL — батч 36

Файлы: personality_reflection.py, promotion.py, proposal.py
Модель: deepseek-v4-flash

Мы провели аудит трех файлов: identity/personality_reflection.py, identity/promotion.py, identity/proposal.py. Нужно найти реальные баги, логические ошибки, утечки, проблемы кодировок, нарушения стиля, дыры в безопасности, мёртвый код, хрупкие места, ошибки конвейеров памяти, зависимости и связи между модулями. Ответ на русском, с указанием файла, строк, типа проблемы, серьёзности, чем грозит, как исправить. В конце сводка.

Начнем с каждого файла.

1. identity/personality_reflection.py (118 строк)

- Импорт json, CloudFirstLlm.
- MODEL_OPTIONS словарь.
- Класс PersonalityReflection, __init__ принимает agent, создает self.llm = CloudFirstLlm(getattr(agent, "model_orchestrator", None)). Если у agent нет атрибута model_orchestrator, то getattr вернет None, и CloudFirstLlm получит None. Это может быть нормально, но нужно проверить, как CloudFirstLlm обрабатывает None. Возможно, это допустимо, но потенциально может вызвать ошибку, если CloudFirstLlm ожидает не None. Но это не точно баг, скорее потенциальная проблема.

- Метод analyze(candidates): если candidates пусто, возвращает []. Далее формирует candidate_data из списка candidates, каждый candidate должен иметь атрибуты field, value, category, strength, weighted_score, evidence_count, source_types. Если candidate не имеет какого-то атрибута, будет AttributeError. Это хрупкое место: предполагается, что все кандидаты имеют эти атрибуты. Но это может быть гарантировано типом, но не проверяется.

- Формирует prompt с json.dumps(candidate_data, ensure_ascii=False, indent=2). Это нормально.

- Затем вызывает self.llm.chat(system=..., user=prompt, options=MODEL_OPTIONS, task="reflection"). Возвращает raw.

- Пытается json.loads(raw). Если ошибка, возвращает []. Это нормально, но если raw содержит markdown или дополнительный текст, то json.loads может упасть, и вернется пустой список. Это может быть приемлемо, но может скрывать ошибки LLM.

- Проверяет, что result - список, иначе возвращает [].

- Возвращает result.

Потенциальные проблемы:
- Нет обработки случая, когда raw не является валидным JSON, но содержит частичный JSON или что-то еще. Возвращается пустой список, что может привести к потере данных.
- Нет проверки, что каждый элемент result имеет нужные ключи (field, value, assessment, reason). Если LLM вернет что-то другое, это может вызвать ошибки в дальнейшем использовании.
- Нет ограничения на количество кандидатов, может быть слишком много, что приведет к большому промпту и превышению контекста.
- Использование getattr(agent, "model_orchestrator", None) - если agent не имеет атрибута, то None, но CloudFirstLlm может ожидать объект. Это потенциальная проблема.
- Нет обработки исключений при вызове llm.chat (сеть, таймаут и т.д.). Если LLM недоступен, будет исключение, которое не перехватывается, и метод упадет. Это может быть критично для стабильности.
- В промпте есть "Текущее состояние личности:" с json.dumps(self.agent.self_state.snapshot()). Если snapshot() вернет что-то не сериализуемое, будет ошибка. Но скорее всего это словарь.
- Нет проверки, что self.agent.self_state существует. Если нет, AttributeError.

2. identity/promotion.py (153 строки)

- Импорт dataclass.
- PromotionDecision dataclass.
- PromotionEngine с константами MIN_STRENGTH, MIN_WEIGHTED_SCORE, MIN_SOURCE_TYPES, MIN_INDEPENDENT_KEYS.
- __init__ принимает evidence=None.
- _independent_count(candidate): если self.evidence is None, возвращает len(candidate.source_types). Иначе вызывает self.evidence.get(candidate.category, candidate.value). Это странно: evidence.get(category, value) - вероятно, evidence - это объект с методом get, который принимает category и value? Но сигнатура get обычно (key, default). Здесь передается два аргумента: category и value. Это может быть ошибкой. Возможно, предполагалось evidence.get(candidate.category, candidate.value) как получение записи по ключу category, а value как default? Но это выглядит подозрительно. Если evidence - это какой-то словарь, то get ожидает один ключ и default. Здесь два аргумента - это вызовет TypeError. Если evidence - это объект с методом get, который принимает два аргумента, то это странно. Скорее всего, это ошибка: должно быть evidence.get(candidate.category) или что-то подобное. Но в коде написано evidence.get(candidate.category, candidate.value). Это может быть намеренно, если evidence - это какой-то контейнер, где get(category, value) возвращает что-то. Но тогда что возвращается? Далее используется record, но record нигде не используется! После try блока, если нет ValueError, то record присваивается, но потом не используется. Это мёртвый код. Затем выполняется SQL запрос к self.evidence.memory.connection. Это предполагает, что evidence имеет атрибут memory, у которого есть connection. Это сильная связь с конкретной реализацией. Если evidence не имеет memory, будет AttributeError. Также SQL запрос использует параметры, что хорошо. Но есть потенциальная проблема: если self.evidence.get() вызовет ValueError, то перехватывается и возвращается len(candidate.source_types). Но если get() вызовет другое исключение (например, TypeError из-за неправильного количества аргументов), оно не перехватывается. Это может быть багом.

- В SQL запросе: SELECT source, independence_key, weight FROM evidence_events WHERE category = ? AND value = ? AND weight > 0. Это предполагает, что таблица evidence_events имеет такие колонки. Если нет, будет ошибка. Также не проверяется, что connection.execute возвращает строки с доступом по ключу (row["independence_key"]). Это предполагает, что row - это sqlite3.Row, что обычно так, если connection.row_factory установлен. Но это не гарантировано.

- Затем keys = { (row["independence_key"] if row["independence_key"] else row["source"]) for row in rows }. Это множество ключей. Если independence_key пустой, используется source. Это нормально.

- Возвращает len(keys).

- evaluate(candidate): проверяет strength < MIN_STRENGTH, weighted_score < MIN_WEIGHTED_SCORE, затем вызывает _independent_count. Если independent_sources < MIN_INDEPENDENT_KEYS, возвращает DEFER. Иначе PROMOTE.

Потенциальные проблемы:
- В _independent_count: вызов evidence.get(candidate.category, candidate.value) - это подозрительно. Если evidence - это объект, который хранит evidence, то вероятно, нужно получить записи по category и value. Но метод get обычно принимает ключ. Здесь передается два аргумента. Это может быть ошибкой. Также record не используется.
- Нет проверки, что candidate.source_types - это список/множество, len() работает.
- Если evidence не None, но не имеет атрибута memory, будет AttributeError.
- Если connection.execute вернет пустой список, то rows пустой, keys пустое, вернется 0. Это может привести к DEFER, что может быть неверно, если есть source_types, но нет записей в evidence_events. Но это может быть нормально.
- В evaluate, если candidate.strength или weighted_score равны None, сравнение с числом вызовет TypeError. Но предполагается, что они числа.
- Нет обработки исключений при SQL запросе.

3. identity/proposal.py (16 строк)

- Импорт dataclass, asdict, Any.
- Dataclass Proposal с полями: proposal_type, value, reason, confidence, evidence (list[str]), evidence_count (int | None = None), origin (str | None = None).
- Метод to_dict() возвращает asdict(self).

Проблемы:
- Нет валидации типов, но это dataclass, так что ок.
- evidence - list[str], но может быть пустым.
- Нет ограничений на confidence (может быть >1 или <0).
- Нет проверки, что evidence_count соответствует len(evidence). Это может привести к рассинхронизации.
- to_dict() использует asdict, который рекурсивно преобразует, но если value содержит несериализуемые объекты, будет ошибка. Но value может быть Any, так что это потенциально.

Теперь общие замечания по конвейеру памяти: evidence→proposal→lifecycle. Здесь мы видим promotion.py, который оценивает кандидатов и возвращает PromotionDecision. personality_reflection.py анализирует кандидатов и возвращает список оценок. proposal.py - это структура для предложения. Связи: promotion использует evidence (объект с memory), personality_reflection использует agent и self_state. Возможные проблемы: в promotion.py evidence.get(candidate.category, candidate.value) - это, вероятно, ошибка, так как get ожидает один аргумент. Также не используется record. Это мёртвый код.

Также в promotion.py есть MIN_SOURCE_TYPES, но он не используется! В evaluate нет проверки на MIN_SOURCE_TYPES. Это мёртвая константа.

В personality_reflection.py нет проверки на то, что candidates - это список объектов с нужными атрибутами. Если candidate не имеет, например, source_types, будет AttributeError.

Также в personality_reflection.py нет обработки ошибок при вызове llm.chat. Это может уронить систему.

Кодировки: файлы, вероятно, в UTF-8 без BOM, но мы не видим содержимое, только текст. В предоставленном тексте нет проблем с кодировкой.

Стиль: используется отступы в 4 пробела, но в некоторых местах есть лишние переносы строк, например, в промпте. Это не критично.

Безопасность: SQL запрос использует параметризацию, что хорошо. Но нет проверки на то, что candidate.category и candidate.value не содержат SQL-инъекций, но параметризация защищает.

Утечки: в personality_reflection.py передается self.agent.self_state.snapshot() в промпт. Это может содержать личные данные, которые отправляются в LLM. Это потенциальная утечка конфиденциальных данных. Нужно быть осторожным.

Также в personality_reflection.py нет ограничения на размер промпта, если кандидатов много, может быть превышен контекст.

Теперь сформулируем находки.

Начнем с personality_reflection.py:

1. Строка 15-17: getattr(agent, "model_orchestrator", None) - если атрибута нет, передается None в CloudFirstLlm. Это может вызвать ошибку, если CloudFirstLlm не поддерживает None. Серьёзность: MEDIUM. Исправить: проверить наличие атрибута и обработать.

2. Строка 25-35: формирование candidate_data без проверки наличия атрибутов. Если candidate не имеет какого-то атрибута, будет AttributeError. Серьёзность: HIGH. Исправить: использовать getattr с дефолтами или проверять.

3. Строка 73-75: вызов llm.chat без обработки исключений. Если LLM недоступен, будет исключение, которое не перехватывается. Серьёзность: HIGH. Исправить: обернуть в try-except, вернуть [] при ошибке.

4. Строка 78-82: json.loads(raw) - если raw не JSON, возвращается []. Это может скрыть ошибки LLM. Серьёзность: LOW. Исправить: логировать ошибку.

5. Строка 88-90: нет проверки, что каждый элемент result имеет нужные ключи. Если LLM вернет что-то другое, это может вызвать ошибки в дальнейшем. Серьёзность: MEDIUM. Исправить: валидировать структуру.

6. Строка 45-47: в промпт включается self.agent.self_state.snapshot(). Это может содержать личные данные, которые уходят в LLM. Серьёзность: HIGH (утечка данных). Исправить: анонимизировать или исключить чувствительные данные.

7. Нет ограничения на количество кандидатов, может быть слишком большой промпт. Серьёзность: MEDIUM. Исправить: ограничить количество
