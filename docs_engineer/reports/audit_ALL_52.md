# Аудит ALL — батч 52

Файлы: test_interest_convergence.py, test_live_affective_dialogue.py, test_live_behavior_contract.py
Модель: deepseek-v4-flash

Мы провели аудит трех тестовых файлов. Нужно найти реальные баги, логические ошибки, утечки, проблемы кодировок, нарушения стиля, дыры в безопасности, мёртвый код, хрупкие места, ошибки конвейеров памяти, зависимости и связи между модулями. Для каждой находки: файл, строка(и), тип проблемы, серьёзность, чем грозит, как исправить. В конце — краткая сводка по модулю.

Проанализируем каждый файл.

**Файл test_interest_convergence.py** (105 строк):
- Импорты: из identity.evidence_consolidator, identity.personality_lifecycle, identity.self_state, identity.user_evidence, memory.database, memory.evidence.
- Внутри with TemporaryDirectory() as temp: создаются объекты.
- memory = None, затем в try создаются state, memory, evidence, lifecycle, consolidator, user_evidence.
- Вызываются методы: evidence.add (три раза), user_evidence.record_interest, evidence.get, consolidator.consolidate, lifecycle.all_traits.
- finally: если memory не None, memory.close().

Потенциальные проблемы:
1. Строка 9-10: импорт EvidenceConsolidator из identity.evidence_consolidator. Возможно, модуль называется evidence_consolidator, но это не ошибка.
2. Строка 12-13: импорт PersonalityLifecycle из identity.personality_lifecycle.
3. Строка 15: SelfState из identity.self_state.
4. Строка 17-18: UserEvidenceRecorder из identity.user_evidence.
5. Строка 20-21: Memory из memory.database.
6. Строка 23-24: EvidenceEngine из memory.evidence.
7. Внутри try: создаются объекты. Но порядок: state, memory, evidence, lifecycle, consolidator, user_evidence. Возможно, есть зависимости: EvidenceEngine требует memory, EvidenceConsolidator требует evidence, UserEvidenceRecorder требует evidence, PersonalityLifecycle требует state. Это выглядит логично.
8. Вызов evidence.add с категорией "interest", значением "космос", источником "SELF_ACTION", затем "SELF_OBSERVATION", затем "SHARED_EXPERIENCE". Между ними вызывается user_evidence.record_interest("космос"). Возможно, record_interest добавляет еще одно свидетельство? Но это не видно.
9. После добавления evidence.get("interest", "космос") - получает запись. Затем consolidator.consolidate() - консолидация. Затем lifecycle.all_traits() - вывод всех черт.
10. В finally закрывается memory.

Возможные проблемы:
- Нет обработки исключений, кроме finally. Если что-то упадет, программа завершится с traceback, но memory закроется. Это нормально для теста.
- Нет проверки, что memory создан успешно. Если Memory упадет, memory останется None, и в finally не будет закрыт, но это не страшно.
- Использование TemporaryDirectory: после выхода из with, временная директория удаляется, но memory закрыт в finally. Однако если memory не закрыт, то файл может быть заблокирован? Но закрытие происходит.
- Стиль: используется много скобок и переносов, что может быть стилем проекта. Но есть лишние скобки в некоторых местах, например, в строке 40-42: evidence.add( ... ) - это нормально.
- Возможная проблема: в строке 40-42 evidence.add вызывается с category="interest", value="космос", source="SELF_ACTION". Но потом user_evidence.record_interest("космос") - возможно, этот метод сам добавляет evidence с другим source? Неизвестно.
- В строке 70-73: record = evidence.get("interest", "космос") - возвращает запись. Но если нет записей, может вернуть None? Неизвестно.
- В строке 78-80: result = consolidator.consolidate() - возвращает результат. Возможно, это изменяет состояние.
- В строке 84-86: for trait in lifecycle.all_traits(): print(trait) - выводит все черты.

Проблемы безопасности: нет.
Утечки: память? Возможно, если evidence или другие объекты не закрыты, но они не имеют close. Memory закрыт.
Кодировка: файл в UTF-8? Не видно BOM, но это не проблема.
Мёртвый код: нет.
Хрупкие места: использование временной директории, но это нормально.

Ошибки конвейеров памяти: evidence → proposal → lifecycle? Здесь evidence добавляется, потом консолидация, потом traits. Возможно, порядок неверный: сначала нужно добавить evidence, потом консолидировать, потом получить traits. Но здесь после добавления evidence вызывается get, потом consolidate, потом traits. Это выглядит правильно.

Зависимости: все импорты корректны.

Возможные реальные баги:
- В строке 40-42: evidence.add(...) - но метод add может требовать другие параметры? Неизвестно.
- В строке 47-49: user_evidence.record_interest("космос") - возможно, этот метод ожидает что-то еще? Неизвестно.
- В строке 70-73: evidence.get("interest", "космос") - возможно, метод get возвращает список, а не одну запись? Тогда print(record) выведет список, но это не ошибка.
- В строке 78-80: consolidator.consolidate() - возможно, возвращает что-то, но не используется.
- В строке 84-86: lifecycle.all_traits() - возможно, возвращает генератор, и после итерации он исчерпан, но это нормально.

В целом, файл выглядит как тестовый скрипт, который должен работать, если все модули реализованы правильно. Но есть потенциальная проблема: если evidence.add или record_interest вызовут ошибку, то выполнение прервется, и memory закроется, но остальные объекты не будут очищены. Но это не критично для теста.

**Файл test_live_affective_dialogue.py** (127 строк):
- Импорты: re, time, core.agent.Agent, core.autonomy_runtime_factory.AutonomyRuntimeFactory.
- Определена константа MESSAGE.
- STATES - список кортежей с названием состояния и словарем изменений.
- Функция metrics(text) - считает символы, слова, предложения, вопросы, восклицания.
- Цикл for state_name, changes in STATES: для каждого состояния создается Agent, строится AutonomyRuntimeFactory, сбрасывается affective_state, применяется реакция, получается mode, behavior, выводится, затем вызывается agent.respond(MESSAGE), замеряется время, выводится ответ и метрики, обрабатываются исключения, в finally agent.close().

Потенциальные проблемы:
1. Строка 1: import re - используется.
2. Строка 2: import time - используется.
3. Строка 4-5: from core.agent import Agent - корректно.
4. Строка 6-7: from core.autonomy_runtime_factory import AutonomyRuntimeFactory - корректно.
5. Строка 9: MESSAGE = "Я придумал для тебя кое-что новое." - строка.
6. Строки 11-24: STATES - список кортежей. В одном кортеже "CURIOSITY__FRUSTRATION" с двумя изменениями. Это нормально.
7. Функция metrics: использует re.findall с r"\S+" для слов, r"[.!?…]+" для предложений. Вопросы и восклицания считаются по символам. Возможно, есть проблема: если текст содержит многоточие "…", оно входит в предложения, но не в вопросы/восклицания. Это нормально.
8. В цикле: создается agent = Agent(). Затем AutonomyRuntimeFactory(agent).build(). Это может быть долго, но не ошибка.
9. agent.affective_state.reset() - сброс состояния.
10. agent.affective_state.apply_reaction(changes=changes, trigger="LIVE_DIALOGUE_TEST", reason="Контролируемое состояние.", source="TEST") - применяет изменения.
11. mode = agent.affective_dialogue_policy.dialogue_mode(message=MESSAGE, route="GENERAL_QUERY") - получает режим диалога.
12. behavior = agent.affective_dialogue_policy.profile() - получает профиль поведения.
13. print("MODE:"); print(mode) - выводит.
14. print("BEHAVIOR:"); print(behavior["behavior"]) - выводит поведение. Если в behavior нет ключа "behavior", будет KeyError. Но это предполагается.
15. print("USER:"); print(MESSAGE) - выводит сообщение.
16. started = time.perf_counter() - замер времени.
17. try: answer = agent.respond(MESSAGE) - ответ.
18. elapsed = time.perf_counter() - started.
19. print("EDDIEAI:"); print(answer) - выводит ответ.
20. print("METRICS:"); print(metrics(answer)) - выводит метрики.
21. print("RESPONSE TIME:", round(elapsed, 3), "s") - выводит время.
22. except Exception as exc: print("ERROR:", type(exc).__name__, str(exc)) - обработка исключений.
23. finally: agent.close() - закрытие агента.

Возможные проблемы:
- В строке 54: agent.affective_state.apply_reaction(...) - метод может не существовать? Но предполагается.
- В строке 57-59: mode = agent.affective_dialogue_policy.dialogue_mode(...) - метод может не существовать.
- В строке 61-63: behavior = agent.affective_dialogue_policy.profile() - метод может не существовать.
- В строке 65: print(behavior["behavior"]) - если ключа нет, будет KeyError, который не перехвачен, так как это вне try. Это может привести к падению скрипта. Это потенциальный баг: если profile() не возвращает словарь с ключом "behavior", то скрипт упадет. Но это тестовый скрипт, и предполагается, что метод возвращает такой словарь.
- В строке 70: answer = agent.respond(MESSAGE) - может вернуть None? Тогда metrics(None) обработает через str(text or ""), но ответ может быть None, и print(answer) выведет None. Это не ошибка.
- В строке 82: print(metrics(answer)) - если answer None, metrics вернет нули.
- В строке 86: print("RESPONSE TIME:", round(elapsed, 3), "s") - если elapsed отрицательный? Нет.
- В except: выводится ошибка, но не выводится traceback. Это нормально.
- В finally: agent.close() - если agent не создан (например, ошибка при создании), то agent не определен, и будет NameError. Но в цикле agent создается до try, так что если создание упадет, то цикл прервется, но agent не будет определен. Однако в finally будет попытка agent.close(), что вызовет NameError. Это потенциальная проблема: если Agent() или AutonomyRuntimeFactory().build() выбросят исключение, то agent не будет присвоен, и в finally будет ошибка. Но это вне try, так как try начинается после создания agent. В коде try начинается только на строке 69 (try: answer = agent.respond). Так что если создание agent упадет, то цикл прервется, и finally не выполнится, так как он внутри try. Но в данном коде try находится после создания agent, так что если создание упадет, то исключение выйдет из цикла, и finally не выполнится. Это нормально, но может оставить ресурсы? Но agent не создан, так что нечего закрывать.
- Однако есть еще один момент: если agent.affective_state.reset() или apply_reaction вызовут исключение, то они находятся до try, так что исключение выйдет из цикла, и finally не выполнится. Это может привести к утечке ресурсов, если agent был создан, но не закрыт. В коде try начинается только после всех этих вызовов. Это потенциальная проблема: если что-то до try упадет, agent не будет закрыт. Но это тестовый скрипт, и вероятно, эти методы не должны падать. Но для надежности можно обернуть весь блок в try/finally.

- Также в metrics: используется re.findall(r"\S+", text, flags=re.UNICODE) - это нормально.
- В metrics: предложения считаются по re.findall(r"[.!?…]+", text) - это может считать многоточие
