# Аудит ALL — батч 12

Файлы: evidence_provider.py, fast_verbalizer.py, identity_consistency.py
Модель: deepseek-v4-flash

Мы провели аудит трех файлов: evidence_provider.py, fast_verbalizer.py, identity_consistency.py. Найдем проблемы.

Начнем с evidence_provider.py.

Файл: core\evidence_provider.py (73 строки)

Класс EvidenceProvider. Анализируем.

- Строка 1-73. В целом код выглядит аккуратным, но есть потенциальные проблемы.

1. В методе __call__: 
   - category = self.CATEGORY_BY_PREDICATE.get(claim.predicate) - если claim.predicate отсутствует в словаре, вернет None, и функция вернет None. Это нормально.
   - if not claim.value: return None - если value пустое, возвращаем None. ОК.
   - try: record = self.evidence.get(category, claim.value) except ValueError: return None. Здесь предполагается, что evidence_engine.get может бросить ValueError. Но что если get вернет None? Тогда record будет None, и дальше будет ошибка при обращении record.source_types. Это потенциальный баг: если evidence.get возвращает None (например, нет записи), то код упадет с AttributeError. В документации класса сказано: "Отсутствие evidence -> None." Но здесь не обрабатывается случай, когда record = None. Нужно проверить: если record is None, то вернуть None. Это серьезная проблема: HIGH или CRITICAL? Если evidence_engine.get возвращает None при отсутствии, то это упадет. Но возможно, evidence_engine.get всегда возвращает объект записи или бросает ValueError? В коде только ловится ValueError. Если get возвращает None, то это не ValueError. Значит, нужно добавить проверку на None. Это реальный баг.

2. strong_sources = set(record.source_types) & self.STRONG_SOURCES - если record.source_types может быть None? Неизвестно. Но если record не None, то source_types должно быть итерируемым. Если это None, то set(None) упадет. Но вероятно, это не так.

3. if record.confidence < 0.70: return None - если confidence отсутствует? Неизвестно.

4. if claim.polarity == "NEGATIVE": return "CONTRADICTED" - если polarity не "NEGATIVE", то возвращаем "SUPPORTED". Но что если polarity "UNKNOWN"? Тогда тоже вернет "SUPPORTED"? Возможно, это неверно. Но в контексте, вероятно, polarity может быть "POSITIVE" или "NEGATIVE". Если "UNKNOWN", то лучше вернуть None. Но это зависит от дизайна. Можно отметить как MEDIUM.

5. В целом, отсутствие обработки record = None - главная проблема.

6. Также нет проверки, что claim.value не пустой, но это есть.

7. Стиль: используется много скобок, но это нормально.

8. Возможная проблема: если evidence.get возвращает запись, но source_types пустой, то strong_sources будет пустым, и вернется None. Это нормально.

9. Еще: если record.confidence >= 0.70 и strong_sources не пусто, но claim.polarity == "NEGATIVE", то возвращается "CONTRADICTED". Но если polarity == "POSITIVE", то "SUPPORTED". Если polarity == "UNKNOWN", то тоже "SUPPORTED". Возможно, нужно обрабатывать UNKNOWN отдельно.

10. Также нет обработки случая, когда claim.value может быть не строкой? Но это не критично.

Теперь fast_verbalizer.py.

Файл: core\fast_verbalizer.py (85 строк)

Класс FastVerbalizer.

- Метод render принимает conclusion, user_message, language. Возвращает текст или None.

- Если conclusion пустой, возвращает None.

- text = str(conclusion.get("conclusion", "") or "").strip() - если conclusion["conclusion"] не строка, то str() преобразует. ОК.

- stored_language = conclusion.get("language") - может быть None.

- normalize_language: преобразует в нижний регистр, убирает пробелы, сопоставляет алиасы. Если язык неизвестен, возвращает нормализованную строку (например, "unknown" останется "unknown").

- stored_lang = normalize_language(stored_language), current_lang = normalize_language(language).

- Условие: если stored_lang и current_lang не пустые, и не равны "unknown", и не равны друг другу, то возвращаем None (т.е. не используем direct mode). В противном случае возвращаем text.

Потенциальные проблемы:

1. Если stored_language = "unknown", то stored_lang = "unknown". current_lang может быть "ru". Условие: stored_lang and current_lang and stored_lang != "unknown" and current_lang != "unknown" and stored_lang != current_lang. Здесь stored_lang == "unknown", поэтому условие ложно, и возвращается text. Это соответствует комментарию: "Неизвестный язык не блокирует direct mode". ОК.

2. Если stored_language = "ru", current_lang = "ru", то условие ложно, возвращается text. ОК.

3. Если stored_language = "ru", current_lang = "en", то условие истинно, возвращается None. ОК.

4. Если stored_language = None, то stored_lang = "" (пустая строка). current_lang = "ru". Условие: stored_lang and current_lang - stored_lang пустая, поэтому ложно, возвращается text. Это тоже соответствует: неизвестный язык не блокирует.

5. Но есть нюанс: если stored_language = "unknown", а current_lang = "unknown", то условие ложно, возвращается text. Это нормально.

6. Потенциальная проблема: если stored_language = "ru", current_lang = "unknown", то stored_lang = "ru", current_lang = "unknown". Условие: stored_lang and current_lang and stored_lang != "unknown" and current_lang != "unknown" and stored_lang != current_lang. current_lang == "unknown", поэтому current_lang != "unknown" ложно, условие ложно, возвращается text. Это соответствует комментарию: неизвестный язык не блокирует.

7. В целом, логика верна.

8. Но есть потенциальная проблема: если conclusion["language"] отсутствует, то stored_language = None, normalize_language(None) вернет "" (пустую строку). Тогда stored_lang = "". current_lang = "ru". Условие: stored_lang and current_lang - stored_lang пустая, ложно, возвращается text. Это нормально.

9. Однако, если conclusion["language"] = "unknown", то stored_lang = "unknown". current_lang = "ru". Условие: stored_lang and current_lang and stored_lang != "unknown" and current_lang != "unknown" and stored_lang != current_lang. stored_lang != "unknown" ложно, поэтому условие ложно, возвращается text. Это соответствует.

10. Но есть тонкость: если stored_language = "ru", current_lang = "ru", то возвращается text. Если stored_language = "ru", current_lang = "en", возвращается None. Это правильно.

11. Возможная проблема: если stored_language = "ru", current_lang = "RU" (с заглавной), normalize_language сделает casefold, получит "ru". ОК.

12. Еще: если stored_language = "russian", normalize_language вернет "ru". ОК.

13. В целом, код корректен.

14. Но есть потенциальная проблема: если conclusion["conclusion"] содержит только пробелы, то text = "" и возвращается None. Это нормально.

15. Нет обработки случая, когда conclusion["conclusion"] не строка, а например, число. str() преобразует, но это может быть нежелательно. Но это не критично.

16. Стиль: используется много скобок, но это нормально.

Теперь identity_consistency.py.

Файл: core\identity_consistency.py (250 строк)

Класс IdentityConsistencyLayer.

- Импортирует dataclass.

- Определяет IdentityViolation.

- В __init__ принимает agent, извлекает ownership_resolver и self_claim_validator.

- Метод analyze: принимает user_message, answer, возвращает dict.

- В analyze: сначала получает ownership_result = self.ownership.analyze(...). Затем expected_owner = ownership_result.get("expected_owner").

- Затем обрабатывает violations из ownership_result["violations"]. Для каждого item проверяет условие: если expected == "USER" and actual == "SELF" и self._is_user_claim_echo(...), то continue. Иначе добавляет IdentityViolation.

- Затем, если expected_owner == "SELF", то вызывает self.self_claims.validate_text(answer). Если text_claim.property != "unknown", то добавляет в self_claim_results и вызывает _append_claim_violation. Иначе, для каждого claim в ownership_result["answer_claims"], если claim.owner == "SELF" и property не в {"unknown", "identity"}, то вызывает self.self_claims.validate(...) и добавляет.

- Возвращает dict.

- Метод _append_claim_violation: если result.status == "UNSUPPORTED" или "CONTRADICTED", добавляет IdentityViolation.

- Метод _normalize: нормализует текст.

- Метод _is_user_claim_echo: сравнивает нормализованные user_message и answer.

- Метод has_high_severity: проверяет наличие HIGH severity.

Потенциальные проблемы:

1. В analyze: ownership_result["violations"] - предполагается, что этот ключ существует. Если ownership_result не содержит "violations", будет KeyError. Но вероятно, ownership.analyze всегда возвращает этот ключ.

2. expected_owner = ownership_result.get("expected_owner") - может быть None. Если expected_owner None, то блок SELF CLAIMS не выполнится (условие expected_owner == "SELF" ложно). Это нормально.

3. В цикле по violations: item.get("expected_owner") и item.get("actual_owner") - если ключи отсутствуют, вернут None. Тогда условие expected == "USER" and actual == "SELF" может быть ложно, и добавится violation. Но если expected_owner отсутствует, это может быть ошибкой. Но вероятно, item всегда содержит эти ключи.

4. В _is_user_claim_echo: сравнивает user_text и answer_text. Если они равны, то считает, что это эхо. Но это слишком строго: если пользователь сказал "Я люблю кофе", а ответ "Я люблю кофе", то это эхо. Но если ответ содержит больше текста, то не эхо. Это может быть нормально.

5. В блоке SELF CLAIMS: если text_claim.property != "unknown", то добавляется. Но если text_claim.property == "unknown", то fallback на структурные claims. Но что если text_claim.property == "unknown", а в answer_claims есть claim с property "identity"? Он пропускается (continue). Это может быть намеренно.

6. В _append_claim_violation: result.status может быть другим (например, "SUPPORTED"), тогда ничего не добавляется. Это нормально.

7. Потенциальная проблема: если self.self_claims.validate_text(answer) возвращает объект, у которого нет атрибута property? Но предполагается, что есть.

8. В _normalize: используется replace("ё", "е") - это нормально для русского.

9. В _is_user_claim_echo: если user_message или answer пустые, то bool(user_text) будет False, и вернется False. Это нормально.

10. В has_high_severity: result.get("violations", []) - если violations отсутствует, вернет пустой список. ОК.

11. Но есть потенциальная проблема: в analyze, если expected_owner == "SELF", но text_claim.property == "unknown", то мы идем в fallback. Но в fallback мы перебираем ownership_result["answer_claims"]. Однако, ownership_result["answer_claims"] может быть пустым списком. Тогда ничего не добавится. Это нормально.

12. Еще: если expected_owner == "SELF", но text_claim.property != "unknown", мы добавляем text_claim и вызываем _append_claim_violation. Но мы не добавляем остальные claims из answer_claims. Это может пропустить другие нарушения. Но комментарий говорит: "один claim -> один canonical validation result". Так что это намеренно.

13. Возможная проблема: если text_claim.property != "unknown", но text_claim.status == "SUPPORTED", то _append_claim_violation ничего не добавит. Это нормально.

14. Но есть потенциальная проблема: если text_claim.property != "unknown", но text_claim.status == "UNSUPPORTED", то добавится violation. Но если в answer_claims есть другой
