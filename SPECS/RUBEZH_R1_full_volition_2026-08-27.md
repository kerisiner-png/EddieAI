# R1-расширение: полный волевой канал деятельностей

Дата: 27.08.2026
Статус: РЕАЛИЗАЦИЯ (по утверждённой директиве Эдди 27.08.2026, сон Эдди — работа ведётся автономно, подтверждение по завершении этапов)
Автор: главный инженер EddieAI (opencode, big-pickle)

## Цель

Расширить уже готовый move-канал «воля ядра» (core/agent.py respond_with_action
+ core_selector) на НЕ-перемещение деятельности. Принцип: мир подаёт ядру единое
машиночитаемое «меню возможностей»; ядро через ActionSelector выбирает ОДИН
вариант; мир применяет; ActionObserver сверяет и помечает source="core_selector"
во всех волевых случаях. Это и есть тест «пробы воли» R2 по всей области действий.

## Исходное состояние (по артефактам)

[Подтверждено] Move-канал работает end-to-end:
- core/agent.py:3961 respond_with_action: парсит «Возможности движения» (JSON-лист
  локаций), строит SimpleNamespace(action_type="move:..."), ActionSelector.select,
  пишет ACTION_CHOICE source="core_selector", вербализует через _respond_world_observation
  c decision_note, возвращает {"action":{"type":"move","target":...}}.
- eddie/action_observer.py:223-248,312-316: observe принимает declared_action
  {"type":"move","target":в LOCATION_PATTERNS} -> declared_target -> source="core_selector".
- analyze_volition_night.py: критерий source==core_selector + location_changed.

[Подтверждено] Мир применяет ТОЛЬКО перемещение:
- world/dynamics.py:1027 apply_eddie_action читает только action["location_after"].
- engine/runtime.py:731-771: activity/do_action ставятся в world.eddie_activity по
  строковому распознаванию action_observer (source="action_observer"), но в динамику
  мира не применяются (consequences не вызывается для деятельности).
- Мост (eddie/bridge.py:343-400): печатает move-меню; не-перемещение действия мир
  НЕ печатает как меню (только текст-подсказку при hostage_crisis).

[Подтверждено] Словарь деятельностей (id) уже стандартизирован:
- eddie/action_observer.py ACTIVITY_PATTERNS: doing_nothing, speaking_up, comforting,
  observing, hiding, helping, waiting, thinking.
- Физика DO_VERBS (hit/push/take/grab/open/close/eat/drink/buy/throw/break/
  hide_object/put) — отдельный уровень взаимодействия с объектами мира.

## Граница этапа 1 (осознанное решение)

Волевой канал этапа охватывает: MOVE (5 локаций) + ACTIVITIES (8 деятельностей).
Физические DO_VERBS НЕ переводятся в волевой выбор в этой правке: их полное
применение требует подсистемы объектов и эффектов — отдельный последующий этап
(без выдумывания несуществующих механик мира). do-verbs остаются строковым путём
распознавания и журналирования как сейчас.

## Контракт: меню возможностей (мир -> ядро)

bridge.build_observation печатает (после блока движения) блок действия:

    Возможности движения:
    [<локации, кроме текущей>]

    Возможности действия:
    [<activity ids, из EDDIE_ACTIVITIES>]

    Значения деятельности:
    speaking_up — говорить/позвать на помощь
    comforting — утешать/поддержать
    observing — наблюдать/слушать
    hiding — прятаться/укрыться
    helping — помогать/спасать
    waiting — ждать/пересиживать
    thinking — думать/размышлять
    doing_nothing — ничего не делать/не вмешиваться

EDDIE_ACTIVITIES = список id, совпадающий с ключами ACTIVITY_PATTERNS
(8 элементов). Список задаётся в bridge.py как константа класса;
action_observer импортирует её или использует собственные ключи (структуры
идентичны — выдерживаем источник истины в bridge.py, наблюдатель читает
EDDIE_ACTIVITIES).

## Контракт: возвращаемое действие (ядро -> мир)

- move:       {"type":"move",     "target":"school"}
- деятельность: {"type":"activity", "activity":"helping"}
- ничего (doing_nothing): {"type":"activity","activity":"doing_nothing"}

## Изменения: мир (simulation_framework)

1. eddie/bridge.py:
   - константа EDDIE_ACTIVITIES (8 ids) + EDDIE_ACTIVITY_DESCRIPTIONS (id->фраза);
   - в build_observation: блок «Возможности действия» + «Значения деятельности».

2. engine/runtime.py:
   - в цикле Эдди после observe: если result["action"]["type"]=="activity",
     world.eddie_activity = читаемое имя деятельности; journal.write("eddie_activity").
   - волевые действие НЕ меняют location (activity не двигает Эдди).

3. world/dynamics.py apply_eddie_action — НЕ ТРЕБОВАЛОСЬ изменений:
   runtime.py (строки 735-741) уже применяет распознанную/волевую деятельность
   в world.eddie_activity; волевая деятельность не двигает Эдди (apply_eddie_action
   получает action без location_after -> возвращает None). Это минимальный дифф.

4. eddie/action_observer.py observe:
   - принимает declared_action {"type":"activity","activity":<id>}:
     * если id в ACTIVITY_PATTERNS -> declared_activity
     * результат: activity=id, activity_declared=True
   - source="core_selector" если declared_target ИЛИ declared_activity заданы.

## Найденный и исправленный баг (по результатам проверки)

Добавление блока «Возможности действия» ПОСЛЕ блока движения сломал
_parse_move_menu в core/agent.py: он использовал tail.rfind("]") (последнюю
скобку во всём тексте). Теперь последняя "]" принадлежит activity-меню,
поэтому move-парсинг возвращал []. Исправлено: tail.find("]") — первая
закрывающая скобка после метки (корректный конец move-списка).
_parse_activity_menu сделан симметрично (find).

## Изменения: ядро (EddieAI)

core/agent.py respond_with_action:
   - парсит и move-меню, и activity-меню (JSON-лист после «Возможности действия:»);
   - строит общий список options SimpleNamespace(action_type=...):
       move -> "action:move:school", activity -> "action:activity:helping";
   - единый ActionSelector.select(options);
   - пишет ACTION_CHOICE source="core_selector" (как сейчас);
   - вербализует через _respond_world_observation(decision_note=...); decision_note
     для деятельности формулирует фразу по словарю MOVE/ACTIVITY_DECISION_PHRASES;
   - возвращает {"response","action":{...},"selection_reason"}.
   - если меню деятельностей отсутствует/пусто — поведение как сейчас для move.

        (наличие ВЫБОРА деятельности, выбранной ПРОАКТИВНО, при
        отсутствии явного события — см. примечание о кризисе ниже)

## Примечание о кризисе (важно)

Сейчас при hostage_crisis мост печатает текст-подсказку действий вместо move-меню.
Текст-подсказка остаётся (это часть сценария), НО волевой канал единообразно
подаёт menu деятельности всегда (move-меню при кризисе оставляем как есть —
«покинуть нельзя», но локации в меню не должны приводить к выходу; apply_eddie_action
уже блокирует выход при кризисе). Таким образом деятельность выбирается ядром
даже в кризисе. move-меню при кризисе не печатаем (как сейчас), activity-меню — да.

## Верификация R2 (analyze_volition_night.py)

Критерий «акт воли» расширяется: source==core_selector И (location_changed ИЛИ
activity_declared). Обновить анализатор зеркально. Смоук-тест и минимальные
прогоны — по ограничению Эдди (больших ночных прогонов НЕТ; вечером запуск 24 ч).

## Тесты/проверки этапа

- py_compile: bridge.py, runtime.py, dynamics.py, action_observer.py, agent.py.
- Юнит: action_observer.observe с declared activity -> source="core_selector".
- Юнит: _parse activity-меню в agent.py.
- Смоук: сборка observation bridge.build_observation содержит блок действия;
  respond_with_action на синтетическом тексте возвращает activity-действие.
- байт-проверка UTF-8 без BOM, без «?» вместо кириллицы.

## Риски

- Расширение respond_with_action не должно ломать существующее move-поведение
  (обратная совместимость: если activity-меню нет — move-поток не меняется).
- Runtime уже ставит eddie_activity из строкового распознавания; волевой путь
  должен приоритетно перекрывать его (ид в мир).
- RAM 0.82 ГБ — тяжелые прогоны НЕ выполняем в этой смене; только компиляция и
  минимальные юнит/смоук-проверки.
