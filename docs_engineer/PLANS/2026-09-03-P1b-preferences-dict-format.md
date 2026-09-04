# План П-1b: обогащение формата предпочтений (self_state.preferences)

[АКТУАЛЬНО] Создано 03.09.2026. Этаж 5, блок П-1 «Модель предпочтений».
Решение Эдди (03.09): **словарь-запись с обратной совместимостью**.

## Проблема (факт кода, не декларация)

`self_state.preferences` — список плоских нечитаемых строк-сигнатур,
напр. `"research:action_method:RESEARCH"` (в проде есть такая запись).
Теряются: тип/контекст, метод, сила (share), провенанс, время, человекочитаемый вид.
В промпты/самосознание уходит каша, а не осмысленное предпочтение.

В `agent_loop.py:700-746` ACTION_CHOICE-событие уже содержит в content
читаемый `task.title` (через `ActionChoice.to_dict()`), но детектор
`_load_choice_groups` его игнорирует — читает только context/options/selected.
События из `agent.py` (core_selector, строка 4152) пишутся БЕЗ task.

## Решение (утверждено Эдди)

Формат записи preference — словарь:
```
{ "label": <читаемый текст: task, иначе шаблон>,
  "context": str, "method": str,
  "share": float, "total": int,
  "source": "ACTION_CHOICE", "ts": <iso> }
```
Обратная совместимость: старые строковые записи остаются валидными —
единый хелпер чтения показывает строку как есть.

## Карта точек (grep подтверждён):
- write: `identity_manager._evaluate_list_field` (строка 116 — единственная запись).
- конвейер: `agent_loop._process_identity_detectors` (294 Proposal),
  `action_preference_detector.detect()` (res dict).
- Proposal: `identity/proposal.py` — добавить `meta: dict | None = None`.
- read/показ: `core/prompts.py` (74-77, 145; 370-372, 408),
  `core/self_concept_resolver.py` (58-63, 168),
  `core/current_mind_state.py` (22-27, 158),
  `core/agent.py` self-state wrapper (636-685),
  `core/self_state_interface.py` (131-134 — просто копирует список, ок).
- дедуп/консистентность: `self_consistency.py` (412), `personality.py` (27),
  `claim_engine`/`predicate_registry` сравнивают строки — для preference
  смотреть по методу/сигнатуре (обратная совместимость).

## Изменения по файлам (минимальный дифф, один стиль)

1. `identity/proposal.py`: + `meta: dict | None = None` (после origin).
2. `identity/preference_label.py` (новый, маленький хелпер):
   - `preference_label(item) -> str`: dict→label(или шаблон), иначе→строка как есть.
   - `format_preferences(items) -> str/list[str]: читаемые строки.
3. `identity/action_preference_detector.py`:
   - `_load_choice_groups`: добавить в запись `task` (из choice.get("task"),
     если str; иначе None).
   - `_analyze_group`: в res добавить `"meta"` (context/method/share/total/task).
4. `core/agent_loop.py::_process_identity_detectors`:
   - для category=="preference" передать `proposal.meta = {
     "context","method","share","total","task" }` из item.
5. `identity/identity_manager.py::_evaluate_list_field`:
   - если proposal_type=="preference" и proposal.meta: сформировать dict-запись
     (label из meta.task или шаблона; context/method/share/total; source;
     ts now); дедуп по `method` среди dict и по сигнатуре среди строк;
     записать dict в self_state.preferences. Запись в memory.remember_proposal
     — с читаемым label.
   - иначе (строки/другие категории) — как сейчас.
6. read: подставить `format_preferences(...)`/`preference_label(...)` в
   prompts.py, self_concept_resolver.py, current_mind_state.py, agent.py
   (только в местах показа, без изменения структуры state).

НЕ трогаем: интерests (уже читаемые), habits (численный маппинг), другие детекторы.

## TDD (тест: `test_preference_dict_format.py`)
- (write) детектор+конвейер+identity_manager: после 3/1 выборов в
  self_state.preferences появляется **dict** с ключами label/context/method/
  share/total/source/ts, label непустой и НЕ равен сигнатуре.
- (дедуп) повторный detect не добавляет дубль (тот же method).
- (read) `format_preferences` для dict→label; для строки→как есть.
- (совместимость) память с уже существующей строкой-сигнатурой не ломается
  (format_preferences возвращает строку).

## Шаги
1. 작성 теста (RED).
2. Proposal.meta + preference_label.py (хелпер).
3. Детектор (task + meta) + конвейер (meta в Proposal).
4. identity_manager dict-запись + дедуп.
5. read-точки (промпты, self_concept, current_mind_state, agent).
6. Регресс: test_preference_detector, habit_pattern, belief, self_consistency,
   full промпт-тесты (life_rituals, prompt_blocks).
7. Байт-проверка кодировок (UTF-8 без BOM, FFFD).
8. Документация: CHANGELOG, TODO, ROADMAP_CLOSE_PLAN (П-1b), PROJECT_STATE.

## Статус (04.09.2026): РЕАЛИЗОВАНО, тесты GREEN

Шаги 1–5 реализованы в рабочем дереве; шаг 6 (регресс) и шаг 7 (байт-проверка)
выполнены. Дополнительно (новая под-ветка, найденная при TDD):
- `core/self_claim_validator.py::_extract_compare_text` — dict→label (или context+method, иначе str).
- `core/claim_engine.py::_extract_value_text` — то же для registry-пути evaluate.
- `core/predicate_registry.py::_value_text` — ветки SCALAR/COLLECTION сравнивают по читаемому тексту,
  а не по `str(dict)`-repr (закрыта точка риска из раздела «Риски»).
- `core/agent.py` (core_selector путь) — в choice-словарь добавлен `context_type` (move/activity),
  чтобы детектор получал осмысленный контекст.

Тесты: `test_preference_dict_format.py`, `test_preference_detector.py`,
`test_claim_validator_pref_dict.py` (6 кейсов) — ALL OK / ALL PASS.
Регресс: test_habit_pattern_rebuild, test_pattern_habit, test_life_prompt_blocks,
test_life_rituals, test_semantic_judge, test_user_statement_detector — PASS.

Осталось: шаг 8 (CHANGELOG + PROJECT_STATE) — ведётся в этой сессии.

## Риски
- dict в списке может затронуть код, сравнивающий элементы на str (дедуп/
  консистентность) — проверить self_consistency/predicate_registry для
  preference, добавить ветку по методу.
- Прод-строка остаётся строкой (не мигрируем) — приемлемо, читается через хелпер.
- TDD на identity_manager требует FakeMemory с remember_proposal.
