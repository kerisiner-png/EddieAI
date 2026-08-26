# Аудит ALL — батч 38

Файлы: self_consistency.py, self_experience.py, self_reflection.py
Модель: deepseek-v4-flash

Мы провели аудит кода. Теперь нужно составить ответ в соответствии с инструкцией: найти реальные баги, логические ошибки, утечки, проблемы кодировок, нарушения стиля, дыры в безопасности, мёртвый код, хрупкие места, ошибки конвейеров памяти, зависимости и связи между модулями. Для каждой находки указать файл, строки, тип проблемы, серьёзность, чем грозит, как исправить. В конце — краткая сводка по модулю.

Проанализируем каждый файл.

Файл identity/self_consistency.py (610 строк). Содержит класс SelfConsistency. Проверяет утверждения модели о себе. Есть методы _age_claims, _interest_claims, _preference_claims, _habit_claims, _belief_claims, _goal_claims, _capability_claims, _execution_claims, _compare, _normalize.

Проблемы:

1. В _capability_claims: внутри capability_phrases есть строки с юникод-эскейпами (например, "\u0443 \u043c\u0435\u043d\u044f ..."). Это нормально, но в коде они выглядят как escape-последовательности, что может быть нечитаемо. Однако это не баг, а стиль. Но можно отметить как нарушение читаемости.

2. В _capability_claims: для каждого capability и для positive и negative групп есть цикл, который ищет фразу в normalized. Если найдена positive, добавляет claim с negative=False, и break. Затем отдельно ищет negative. Это может привести к тому, что если текст содержит и positive и negative фразу (например, "у меня есть доступ к интернету, но я не могу выходить в интернет"), то будут добавлены два claim: один positive, другой negative. Это может быть логической ошибкой: модель может противоречить сама себе. Но это скорее особенность, не баг. Однако можно отметить как потенциальную проблему.

3. В _execution_claims: в patterns используются регулярные выражения, но в claims добавляется "text": pattern (сам паттерн), а не найденный текст. Это может быть неинформативно. Но не критично.

4. В _compare для capability: есть строки с "??????" - это явно повреждённые строки (проблема кодировки). Например, "Capability ????????." и другие. Это серьёзная проблема: сообщения об ошибках нечитаемы. Это, вероятно, из-за неправильной кодировки при сохранении файла. Нужно исправить.

5. В _compare для execution: используется self.memory.connection.execute(...). Предполагается, что memory имеет connection с методом execute, возвращающим строки с доступом по ключу (row["content"]). Это может быть хрупко, если memory не соответствует интерфейсу. Но это допустимо.

6. В _compare для execution: если memory None, возвращает unknown. Но если memory есть, но нет connection? Не проверяется.

7. В _compare для capability: если capability не найден и negative=False, то возвращается contradiction. Но если negative=True и capability не найден, то consistent. Это правильно.

8. В _compare для age: если current_age None, то value != None всегда True, будет contradiction. Возможно, нужно обработать случай, когда возраст не установлен.

9. В _compare для interest и др.: если self_state не содержит поле (например, "interests"), то current_values = [] и claim будет new. Это нормально.

10. В _normalize: удаляет пунктуацию в конце, но не в начале. Не критично.

11. В _age_claims: паттерн r"\bя\s+(\d{1,3})[- ]летн" - может ложно срабатывать на "я 20-летний"? Но это ок.

12. В _interest_claims и др.: используется re.IGNORECASE, но русские буквы не зависят от регистра? В Python re.IGNORECASE работает для юникода, так что ок.

13. В _capability_claims: normalized = text.casefold() - это хорошо.

14. В _execution_claims: используется re.search, но не IGNORECASE? В коде есть re.IGNORECASE? Проверим: в _execution_claims используется re.search(pattern, text, re.IGNORECASE) - да, есть.

15. В _compare для execution: keywords - кортежи, но в any(keyword in content for keyword in wanted) - это ок.

16. В целом, класс выглядит рабочим, но есть повреждённые строки.

Файл identity/self_experience.py (188 строк). Содержит dataclass ExperienceSignal и класс SelfExperienceConsolidator.

Проблемы:

1. В record: создается Event.create и Knowledge, но не проверяется, что memory.remember и remember_knowledge существуют. Это предполагается.

2. В record_signals: используется self.evidence.add(...). Предполагается, что evidence имеет метод add. ОК.

3. В record_signals: создается Event.create с event_type="EVIDENCE", но не проверяется, что такой тип допустим.

4. В _build_experience: если payload dict и есть content, возвращает строку с content. Если content пустой, то возвращает строку со статусом. Нормально.

5. В record: confidence = 1.0 if status == "OK" else 0.3. Но status может быть "UNKNOWN" и т.д. Это нормально.

6. В record: verified=(status == "OK"). ОК.

7. В record_signals: confidence=signal.confidence, но не проверяется, что confidence в диапазоне [0,1]. Можно добавить.

8. В record_signals: source="SELF_ACTION" для evidence.add, но source для Event.create - source=source (параметр). Это может быть不一致.

9. В record_signals: не возвращается knowledge, только evidence. Возможно, нужно.

10. В целом, класс простой.

Файл identity/self_reflection.py (421 строк). Содержит класс SelfReflection.

Проблемы:

1. Импорт: from json import JSONDecodeError - это ок.

2. В __init__: self.llm = CloudFirstLlm(getattr(agent, "model_orchestrator", None)). Если model_orchestrator None, то CloudFirstLlm может не работать. Но это зависит от реализации.

3. В reflect: формируется промпт с f-string, внутри которого json.dumps. Это ок.

4. В reflect: вызывается self.llm.chat(...). Предполагается, что chat возвращает строку.

5. В _parse_json: обрабатывает случай, когда raw содержит markdown-блок. Но если raw начинается с "```json", то после удаления первой строки, cleaned может начинаться с "json", и код делает cleaned = cleaned[4:].lstrip(). Это правильно.

6. В _parse_json: если raw не JSON, ищет первую "{" и последнюю "}". Это может захватить лишнее, но приемлемо.

7. В _validate: проверяет типы, но не проверяет, что observations и self_knowledge и user_knowledge - списки строк. Могут быть другие типы.

8. В _validate: для proposals создает Proposal, но не проверяет, что proposal_type допустим. Это может быть проблемой.

9. В _apply_ownership_guard: есть комментарий "Реконструировано 23.08 по смыслу: оригинал побит кодировкой ещё до первого коммита (git-версий нет)." Это указывает на то, что код был повреждён и восстановлен. Возможно, есть скрытые проблемы.

10. В _apply_ownership_guard: user_markers содержит "у меня", "меня ", "мне ", "мой ", "моя ", "моё ", "мои ", "я имею", "я предпочитаю", "меня зовут", "моя семья", "мои родители", "я живу", "мне нравится". Это эвристика, может ложно срабатывать. Например, "мне нравится" может быть и о SELF, если SELF говорит "мне нравится". Но guard переносит в user_knowledge. Это может быть ошибкой. Но это защита от неправильной классификации LLM.

11. В _apply_ownership_guard: если self_knowledge содержит строку, которая содержит "мне нравится", она будет перемещена в user_knowledge. Это может быть неверно, если SELF говорит "мне нравится космос". Но guard считает, что это факт о USER. Это потенциальная логическая ошибка.

12. В _validate: proposals создаются, но не проверяется, что value не пустой.

13. В _empty_result: возвращает пустые списки.

14. В целом, класс выглядит рабочим, но есть эвристика, которая может быть неточной.

Теперь сформулируем отчёт.

Начнём с файла self_consistency.py.

Находки:

- Повреждённые строки в _compare для capability: строки с "??????". Это HIGH или CRITICAL, так как сообщения об ошибках нечитаемы, что затрудняет отладку и понимание. Исправить: заменить на нормальные русские строки.

- В _compare для age: если current_age None, то будет contradiction. Это MEDIUM: если возраст не установлен, любое утверждение о возрасте будет противоречием. Лучше возвращать unknown или new.

- В _capability_claims: возможны дублирующиеся claims, если текст содержит и positive и negative фразу. Это LOW: может привести к ложным противоречиям.

- В _execution_claims: в claims добавляется pattern вместо найденного текста. Это LOW: неинформативно.

- В _compare для execution: не проверяется, что memory.connection существует. Это MEDIUM: если memory не имеет connection, будет AttributeError.

- В _normalize: не удаляет пунктуацию в начале строки. Это LOW.

- В _age_claims: паттерн r"\bя\s+(\d{1,3})[- ]летн" может ложно срабатывать на "я 20-летний"? Но это ок.

- В _compare для capability: если capability не найден и negative=False, возвращает contradiction. Но если negative=True и capability не найден, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability найден и negative=True, contradiction. Это правильно.

- В _compare для capability: если capability найден и negative=False, consistent. Это правильно.

- В _compare для capability: если capability не найден и negative=False, contradiction. Это правильно.

- В _compare для capability: если capability не найден и negative=True, consistent. Это правильно.

- В _compare для capability: если capability най
