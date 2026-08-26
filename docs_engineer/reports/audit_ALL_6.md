# Аудит ALL — батч 6

Файлы: claim_policy.py, claim_router.py, claim_schema.py
Модель: deepseek-v4-flash

Мы провели аудит трех файлов: claim_policy.py, claim_router.py, claim_schema.py. Найдем проблемы.

Начнем с claim_policy.py.

1. В методе evaluate: 
   - relevant = [item for item in evaluations if item.status != "NOT_SELF_CLAIM"] - это фильтрация. Но если evaluations пуст, то relevant пуст, и вернется ACCEPT/NONE. Это нормально.
   - highest = max(relevant, key=lambda item: self.STATUS_PRIORITY.get(item.status, 1)). Здесь используется STATUS_PRIORITY, где UNKNOWN имеет приоритет 1, а SUPPORTED и NOT_SELF_CLAIM - 0. Но NOT_SELF_CLAIM уже отфильтрован. Однако если есть статус, которого нет в словаре, то приоритет 1 (как UNKNOWN). Это может быть проблемой, если появятся новые статусы. Но вроде бы все статусы перечислены.
   - reasons собираются только для CONTRADICTED и UNSUPPORTED. Это нормально.
   - Логика: если highest.status == "CONTRADICTED" -> REPAIR_REQUIRED HIGH; если UNSUPPORTED -> REPAIR_REQUIRED MEDIUM; иначе ACCEPT. Но что если highest.status == "UNKNOWN"? Тогда вернется ACCEPT, но severity NONE. Возможно, это правильно? Но если есть UNKNOWN, может быть стоит что-то другое? Но по логике, если нет противоречий и нет неподтвержденных, то принимаем. Однако если есть UNKNOWN, это может означать, что есть неопределенность, но политика говорит ACCEPT. Возможно, это допустимо.
   - Нет обработки случая, когда evaluations содержит элементы с None или другими типами? Предполагается, что evaluations - список объектов с атрибутами status, reason. Но не проверяется.
   - В reasons: tuple(item.reason for item in relevant if item.status in {"CONTRADICTED", "UNSUPPORTED"}) - если reason может быть None, то в кортеже будет None. Это может быть проблемой, но не критично.
   - В целом, код простой, но есть потенциальная проблема: если evaluations содержит элемент со статусом, отсутствующим в STATUS_PRIORITY, то приоритет будет 1 (как UNKNOWN). Это может привести к тому, что такой элемент станет highest, и если его статус не CONTRADICTED/UNSUPPORTED, то вернется ACCEPT. Это может быть нежелательно, если статус, например, "ERROR". Но в текущей системе, вероятно, статусы ограничены.

2. claim_router.py:
   - В методе extract: 
     - triage_result = self.triage.analyze(answer) - предполагается, что triage имеет метод analyze.
     - lexical_claims = self.lexical_extractor.extract(answer, implicit_self=(route == "SELF_QUERY")) - передается implicit_self.
     - Если lexical_claims не пуст, то claims = self.lexical_adapter.to_claims(lexical_claims). Затем claim_names = {claim.predicate for claim in claims}. 
     - self_concept_predicates = {"subjective_consciousness", "subjective_feelings", "autonomous_agency"} - это жестко заданные предикаты. Но в claim_schema.py перечислены другие предикаты (has_interest, has_preference и т.д.). Здесь нет этих self-concept предикатов. Возможно, они определены в другом месте? Но в schema их нет. Это может быть рассинхронизация. Если lexical extractor может извлекать только предикаты из schema, то эти self_concept_predicates никогда не встретятся, и условие needs_semantic_self_audit всегда будет истинным для SELF_QUERY, если triage_result.potential_self_claim истинно. Это может привести к лишним аудитам. Но возможно, lexical extractor имеет свои предикаты, не входящие в schema? Но claim_adapter.from_response ожидает claims с predicate из schema? В schema enum содержит только перечисленные. Если lexical extractor извлекает другие предикаты, то они не пройдут валидацию? Но claim_adapter может создавать claim с любым predicate? Непонятно.
     - Далее, если needs_semantic_self_audit ложно, возвращается LEXICAL. Если истинно, выполняется аудит и объединение.
     - Ветка, когда lexical_claims пуст: если triage_result.potential_self_claim ложно, возвращается NONE. Иначе аудит.
     - В _audit_claim_is_text_supported: 
       - spec = self.lexical_extractor.registry.get(predicate) - предполагается, что у lexical_extractor есть registry (словарь). Если spec None, возвращается False.
       - text = str(answer).casefold().replace("ё", "е") - нормализация.
       - patterns = tuple(spec.surface_patterns) + tuple(spec.negative_patterns) - предполагается, что spec имеет surface_patterns и negative_patterns. 
       - return any(pattern in text for pattern in patterns) - проверяет, есть ли хотя бы один паттерн в тексте. Но это проверка на наличие паттерна, а не на то, что claim подтверждается. Например, если claim.predicate = "has_interest", а в тексте есть "интересуется", то паттерн может быть "интересуется". Но если claim.predicate = "has_interest", а в тексте есть "не интересуется", то negative_patterns должны быть проверены? Здесь просто проверяется наличие любого паттерна (и положительного, и отрицательного). Это может привести к ложным срабатываниям: если в тексте есть "не интересуется", то паттерн "интересуется" может быть найден, и claim будет считаться поддержанным, хотя на самом деле отрицание. Но negative_patterns, вероятно, содержат паттерны с отрицанием, и они тоже проверяются. Но если есть и положительный, и отрицательный паттерн, то any вернет True, даже если отрицание перекрывает. Это может быть проблемой. Лучше было бы проверять, что положительный паттерн есть, а отрицательного нет. Но здесь просто any. Это потенциальный баг.
       - Также, если spec.surface_patterns или negative_patterns пусты, то patterns может быть пустым, и any вернет False, что приведет к отбрасыванию claim. Это может быть нормально.
     - _deduplicate: использует ключ (owner, predicate, value, polarity). value приводится к строке и нормализуется. Но если value None, то ключ содержит None. Это нормально. Но если два claim имеют одинаковый owner, predicate, value, polarity, но разную certainty или temporal_scope, они будут считаться дубликатами и один будет отброшен. Возможно, это нежелательно, но может быть приемлемо.
   - В целом, есть потенциальные проблемы с проверкой поддержки текстом (не учитывает отрицание), и с жестко заданными self_concept_predicates, которые могут не соответствовать схеме.

3. claim_schema.py:
   - build_claim_response_schema возвращает словарь с required: ["answer", "claims"]. В claims items required: ["subject", "predicate", "value", "polarity", "certainty", "temporal_scope"]. В properties есть все эти поля. Но в enum для predicate перечислены: has_interest, has_preference, has_habit, has_belief, has_goal, has_value, identity_is, watched, used, experienced, has_capability, has_access, relationship_with. Это 13 предикатов. Но в claim_router.py есть self_concept_predicates: subjective_consciousness, subjective_feelings, autonomous_agency. Этих предикатов нет в схеме. Значит, если lexical extractor или claim_adapter создадут claim с такими предикатами, они не пройдут валидацию по схеме (если она используется для валидации). Но claim_adapter.from_response, вероятно, создает claims на основе ответа LLM, который должен соответствовать схеме. Если LLM вернет claim с predicate "subjective_consciousness", это будет невалидно. Но возможно, эти предикаты не используются в схеме, а только для внутренней логики. Однако в _audit_claim_is_text_supported проверяется registry.get(predicate), и если predicate не в registry, то claim отбрасывается. Значит, если lexical extractor извлекает только предикаты из registry, а registry содержит только те, что в схеме? Тогда self_concept_predicates никогда не будут в claim_names, и условие needs_semantic_self_audit всегда будет истинным для SELF_QUERY, если potential_self_claim. Это может быть неэффективно, но не баг.
   - Также в схеме нет поля "reason", но в claim_policy.py используется item.reason. Это может быть атрибут объекта Claim, который не входит в схему. Это нормально, схема для ответа LLM, а не для внутренних объектов.

Другие замечания:
- В claim_router.py, в методе extract, есть дублирование кода для аудита и фильтрации. Можно вынести в отдельный метод, но это не баг.
- В claim_router.py, в _audit_claim_is_text_supported, используется self.lexical_extractor.registry. Но если lexical_extractor не имеет registry, будет ошибка. Предполагается, что он есть.
- В claim_policy.py, STATUS_PRIORITY включает "UNKNOWN": 1, но "SUPPORTED": 0 и "NOT_SELF_CLAIM": 0. Если есть и SUPPORTED и UNKNOWN, highest будет UNKNOWN (приоритет 1), и вернется ACCEPT. Но если есть UNKNOWN, возможно, стоит вернуть что-то вроде "NEEDS_REVIEW"? Но политика говорит ACCEPT. Это может быть намеренно.

Теперь сформулируем отчет.

Найдем конкретные строки.

claim_policy.py:
- Строка 18: STATUS_PRIORITY - нет проблем.
- Строка 28: relevant = [item for item in evaluations if item.status != "NOT_SELF_CLAIM"] - если evaluations содержит элементы без атрибута status, будет ошибка. Но предполагается, что все имеют.
- Строка 35: highest = max(...) - если relevant пуст, max вызовет ValueError. Но выше есть проверка if not relevant, так что ок.
- Строка 47: reasons = tuple(item.reason for item in relevant if item.status in {...}) - если reason None, то в кортеже будет None. Это может быть нежелательно, но не критично.
- Строка 53-60: логика возврата. Ветка для UNKNOWN не обработана отдельно, но возвращается ACCEPT. Возможно, стоит добавить severity "UNKNOWN"? Но не обязательно.

claim_router.py:
- Строка 46: self_concept_predicates = {"subjective_consciousness", ...} - эти предикаты не входят в schema. Если lexical extractor не может их извлечь, то условие needs_semantic_self_audit всегда истинно для SELF_QUERY при potential_self_claim. Это может привести к лишним вызовам аудита. Но это не баг, а потенциальная неэффективность.
- Строка 61: audit_result = self.auditor.audit(answer) - предполагается, что auditor имеет метод audit.
- Строка 66: self.claim_adapter.from_response({...}, speaker="SELF", user_name=user_name) - предполагается, что claim_adapter имеет метод from_response.
- Строка 74: self._audit_claim_is_text_supported(answer, claim.predicate) - метод проверяет поддержку текстом. Как уже отметили, он не учитывает отрицание. Это может привести к ложным срабатываниям. Например, если claim.predicate = "has_interest", а в тексте "не интересуется", то surface_patterns может содержать "интересуется", и any вернет True, хотя claim должен быть отклонен. Но negative_patterns могут содержать "не интересуется", и тогда any вернет True, потому что negative_patterns тоже в patterns. Но если есть и положительный, и отрицательный, то any вернет True, и claim будет принят. Это неправильно. Нужно проверять, что есть положительный паттерн и нет отрицательного. Это серьезная логическая ошибка.
- Строка 88: _deduplicate - использует ключ с value, но не учитывает certainty и temporal_scope. Это может привести к потере информации, но не критично.
- Строка 108: в ветке, когда lexical_claims пуст, и triage_result.potential_self_claim истинно, выполняется аудит. Но перед этим нет проверки, что triage_result имеет атрибут potential_self_claim. Пред
