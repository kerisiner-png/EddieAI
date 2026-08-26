# Аудит ALL — батч 5

Файлы: claim_audit_schema.py, claim_engine.py, claim_lexical_extractor.py
Модель: deepseek-v4-flash

Мы получили три файла: core/claim_audit_schema.py, core/claim_engine.py, core/claim_lexical_extractor.py. Нужно провести глубокий аудит. Начнем с каждого файла.

1. core/claim_audit_schema.py (92 строки)
- Это просто функция build_claim_audit_schema, возвращающая JSON-схему. Проверим на ошибки.
- В схеме required: ["claims"] - ок.
- properties.claims.items.required: ["subject", "predicate", "value", "polarity"] - но в схеме есть также certainty и temporal_scope, но они не обязательны. Это нормально.
- В properties.predicate.enum - список из 16 предикатов. Проверим, все ли они есть в registry? Но registry не показан. Возможно, есть расхождение. Но это не баг, а потенциальная проблема.
- В properties.value: type ["string", "null"] - ок.
- В properties.polarity.enum: ["POSITIVE", "NEGATIVE", "UNKNOWN"] - ок.
- В properties.certainty.enum: ["HIGH", "MEDIUM", "LOW", "UNKNOWN"] - ок.
- В properties.temporal_scope.enum: ["PAST", "CURRENT", "FUTURE", "DURATIVE", "UNKNOWN"] - ок.
- Схема не имеет additionalProperties: false, так что можно добавлять лишние поля. Это может быть проблемой, но не критично.
- Также нет "additionalProperties": false на уровне items, так что можно добавить любые поля. Это может быть нежелательно.
- В целом схема корректна, но можно улучшить.

2. core/claim_engine.py (279 строк)
- Импорты: from core.predicate_registry import PredicateRegistry - но этот модуль не предоставлен. Предположим, что он существует.
- dataclasses: Claim, ClaimSet, ClaimEvaluation - все frozen, ок.
- ClaimSet.self_claims() - фильтрует по owner == "SELF". Ок.
- ClaimEngine.__init__ принимает self_state_provider, evidence_provider, capability_provider, memory_provider. Создает PredicateRegistry с этими провайдерами. Ок.
- validate_claim: если owner != "SELF", возвращает NOT_SELF_CLAIM. Иначе вызывает predicate_registry.evaluate. Возвращает ClaimEvaluation.
- validate_set: просто вызывает validate_claim для каждого.
- _evaluate_against_self_state: метод, который, судя по всему, должен проверять claim против self_state. Но он не вызывается нигде в классе! Это мертвый код. Он определен, но не используется. Возможно, он должен использоваться в evaluate, но не вызывается. Это потенциальная проблема: либо забыли вызвать, либо он лишний.
- Внутри _evaluate_against_self_state: canonical_fields маппит предикаты на поля self_state. Проверяет claim.polarity. Если POSITIVE и value есть, и _semantic_value_match - возвращает SUPPORTED, иначе UNSUPPORTED. Если NEGATIVE и value есть, и _semantic_value_match - CONTRADICTED, иначе UNKNOWN. Если polarity UNKNOWN - UNKNOWN.
- _semantic_value_match: сравнивает value с known_values. Сначала точное совпадение (casefold). Затем разбивает value на токены длиной >=5, для каждого токена берет stem = token[:max(5, len(token)-2)] и проверяет, есть ли stem в known_values (как подстрока). Это может давать ложные срабатывания, но это задумано как осторожная нормализация.
- Потенциальные проблемы:
  - _evaluate_against_self_state не используется. Возможно, он должен вызываться в evaluate, но не вызывается. Это может быть ошибкой: если PredicateRegistry.evaluate не использует этот метод, то проверка против self_state не происходит. Но мы не видим PredicateRegistry, так что не знаем. Однако метод определен в ClaimEngine, но не вызывается внутри класса. Это подозрительно.
  - В _semantic_value_match: если value пустая строка? Но value может быть None, но здесь value: str, так что если claim.value None, то в _evaluate_against_self_state value = claim.value.casefold() if claim.value else None, так что value может быть None. Но _semantic_value_match ожидает str, так что если value None, будет ошибка. Но в _evaluate_against_self_state перед вызовом _semantic_value_match проверяется if value is None: return None, так что безопасно.
  - В _semantic_value_match: stem = token[:max(5, len(token)-2)] - если len(token) < 5, то max(5, len(token)-2) будет 5, так что stem = token[:5], но token может быть короче 5, тогда stem = token (вся строка). Это нормально.
  - В _semantic_value_match: any(stem in known for known in known_values) - проверяет, является ли stem подстрокой любого known. Это может дать ложные срабатывания, например, value "программирование" -> токен "программирование" (длина >5), stem = "программирован" (len-2=12, max(5,12)=12, берем первые 12 символов). Если known содержит "программист", то stem "программирован" не входит, но "программист" содержит "программист", но stem не подстрока. Так что может не сработать. Но это не баг, а ограничение.
  - В _evaluate_against_self_state: для NEGATIVE, если value None, возвращает None (то есть не определено). Но это может быть неверно: отрицательное утверждение без value (например, "я не имею интересов") - value None, но это должно быть проверено? Сейчас возвращается None, что означает "не знаю". Возможно, это правильно.
  - В _evaluate_against_self_state: для POSITIVE, если value None, возвращает None. Это тоже может быть неверно: утверждение "я имею интересы" без указания конкретного интереса - value None, но это можно проверить, есть ли вообще интересы. Но сейчас возвращается None. Это может быть недоработкой.
  - В _evaluate_against_self_state: для NEGATIVE, если value None, возвращает None, но если value есть и не найдено, возвращает UNKNOWN. Это ок.
  - В _evaluate_against_self_state: для UNKNOWN polarity возвращает UNKNOWN.
  - В целом метод выглядит логичным, но не используется.

- Также в ClaimEngine нет метода evaluate, который бы вызывал _evaluate_against_self_state. Возможно, PredicateRegistry.evaluate использует его? Но PredicateRegistry не виден. Однако метод определен в ClaimEngine, но не вызывается из validate_claim. validate_claim вызывает только predicate_registry.evaluate. Так что _evaluate_against_self_state - мертвый код, если только он не вызывается извне (но это private метод, начинается с _). Скорее всего, это забыли использовать. Это HIGH или MEDIUM проблема.

- Также в ClaimEngine нет проверки на допустимость значений полярности, certainty, temporal_scope. Валидация Claim не проверяет, что полярность входит в VALID_POLARITIES и т.д. Это может привести к ошибкам в PredicateRegistry. Но возможно, PredicateRegistry сам проверяет. Но лучше бы проверить в validate_claim.

- В ClaimSet.self_claims() - фильтрует по owner == "SELF". Ок.

- В целом, ClaimEngine выглядит рабочим, но есть мертвый код и отсутствие валидации.

3. core/claim_lexical_extractor.py (323 строки)
- Класс ClaimLexicalExtractor.
- SELF_MARKERS - кортеж строк.
- __init__ принимает predicate_registry.
- extract(text, implicit_self=False) - нормализует текст, разбивает на предложения, для каждого предложения проверяет, если implicit_self=False, то должно быть явное self-маркер. Затем для каждого spec из registry.all() (предполагается, что registry.all() возвращает список объектов с атрибутами name, surface_patterns, negative_patterns). Для каждого spec ищет negative_pattern, если найден, извлекает value, создает LexicalClaim с polarity NEGATIVE, certainty HIGH, temporal_scope из _infer_temporal_scope. Если negative_pattern не найден, ищет positive_pattern, если найден, создает claim с polarity POSITIVE.
- _is_explicit_self: проверяет наличие маркеров в начале или после пробела. Но маркеры включают "я ", "мне ", "у меня ", "мой ", "моя ", "мои ". Проверка: normalized = " " + sentence, затем проверяет f" {marker}" in normalized или normalized.startswith(marker). Но если маркер "я " и предложение начинается с "я ", то normalized.startswith("я ") сработает, потому что normalized = " " + sentence, так что startswith("я ") не сработает, потому что начинается с пробела. Но потом проверяется f" {marker}" in normalized - это " я " в normalized. Так что если предложение начинается с "я ", то normalized = " я ...", и " я " есть, так что сработает. Ок.
- _first_match: ищет pattern в sentence, проверяет, что перед pattern не буква/цифра (чтобы не было части слова). Возвращает pattern или None.
- _extract_value: находит pattern, берет остаток строки, обрезает пробелы и знаки препинания. Затем ищет границы (", но ", ", но,", " но ", ", однако ", ", однако,", " однако ", ", зато ", " зато ", ";"). Обрезает до первой границы. Затем удаляет префикс "напрямую " и для has_interest удаляет "к ". Возвращает value или None.
- _infer_temporal_scope: проверяет наличие маркеров прошлого, будущего, иначе CURRENT.
- _split_sentences: разбивает по (?<=[.!?])\s+ - это регулярное выражение с lookbehind для точки, восклицательного или вопросительного знака, за которым следует пробел. Это корректно.
- _normalize: приводит к нижнему регистру, заменяет ё на е, разбивает по пробелам и соединяет с одним пробелом.

Потенциальные проблемы:
- В _extract_value: после обрезки границ, value может содержать лишние пробелы? strip удаляет только с краев, но внутри могут быть лишние. Но это не критично.
- В _extract_value: если после pattern сразу идет граница, value может быть пустым, тогда возвращается None. Ок.
- В _extract_value: удаление "напрямую " - это специфично, но может быть не всегда уместно.
- В _extract_value: для has_interest удаляет "к " - но это может быть частью значения, например "к программированию" -> "программированию". Это нормально.
- В _infer_temporal_scope: маркеры "буду " и "будущее " - но "буду" может быть частью слова "будущий"? Но проверяется "буду " с пробелом, так что ок.
- В _is_explicit_self: маркеры включают "мой ", "моя ", "мои " - но они могут быть не только для self, но и для других? Но это extractor для SELF, так что ок.
- В extract: для каждого spec ищет negative_pattern, если найден, создает claim и continue (переходит к следующему spec). Это означает, что если для одного предложения найдено несколько negative_patterns для разных spec, будет создано несколько claims. Это нормально.
- Но есть проблема: если negative_pattern найден, то positive_pattern не проверяется. Это правильно, так как negative имеет приоритет.
- Однако, если negative_pattern найден, но value извлечен, но может быть, что negative_pattern не является полным отрицанием? Например, "я не люблю программирование" - negative_pattern может быть "не люблю". Тогда value = "программирование". Ок.
- Но если negative_pattern найден, но value пустой (например, "я не имею интересов" - pattern "не имею" и value = "интересов"? На самом деле pattern может быть "не имею", тогда value = "интересов"? Но в _extract_value берется остаток после pattern, так что value = "интересов". Это может быть не совсем корректно, но это зависит от паттернов.
- В extract: для каждого spec, если negative_pattern не найден, ищет positive_pattern. Если positive
