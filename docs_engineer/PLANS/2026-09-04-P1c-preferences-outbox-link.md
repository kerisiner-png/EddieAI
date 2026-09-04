# План П-1c: связка preference-контура с outbox-подсказками

[АКТУАЛЬНО] Создано 04.09.2026. Этаж 5, блок П-1 «Модель предпочтений».

## Проблема (факт кода, не декларация)

Preference-детектор (`ActionPreferenceDetector`) находит устойчивые
предпочтения и `identity_manager` промоутит их в `self_state.preferences`
(П-1b). Но это происходит молча: Эдди не видит ни одного вновь
появившегося «предпочтения» — outbox-канал (файл-почта `reports/outbox.md`)
используется только для «цель завершена» и утреннего ритуала
(`agent_loop.py:606-614, 1256-1264`, `autonomous_runtime.py:345`).

В `agent_loop._process_identity_detectors` (строки 201–330) детектор
«подсказывает», `identity_manager.evaluate` «применяет» (returns
"accepted"/"already_present"/"deferred"), но результат «accepted» никуда
не транслируется наружу.

## Решение (в рамках автономного мандата смены)

Минимальный дифф в `agent_loop.py::_process_identity_detectors`: сразу после
`identity_result = self.identity_manager.evaluate(proposal)` — если
`category == "preference" and identity_result == "accepted" and self.outbox
is not None`, отправить в outbox читаемое сообщение:
`"Заметил своё предпочтение: <label>"`.

Label строится через `identity/preference_label.py::preference_label` из
`item["meta"]` (task → иначе context/method), чтобы сообщение было
осмысленным, а не строкой-сигнатурой.

`outbox=None` — тихо пропускается (автономный режим, где почты нет).

## Изменения
- `core/agent_loop.py`: + импорт `preference_label`; + outbox-хук после
  evaluate (guard: preference && accepted && outbox not None). Больше ничего.

## TDD (`test_pref_outbox_link.py`)
- (новое предпочтение) после `_process_identity_detectors` в outbox есть
  сообщение с читаемым label (содержит task/контекст). Для пересечения
  confidence ≥ 0.75 evidence нужно 9/12 выборов «read».
- (без дубля) повторный detect → preference уже зафиксирована
  (already_present) → outbox не растёт.
- (outbox=None) промоушн проходит, ошибок нет.

## Риски
- Реальный Outbox пишет с timestamp — в тесте используется DummyOutbox
  (прод outbox.md не засоряется).
- Log: только «accepted» даёт сообщение; deferred/already_present — нет.

## Статус (04.09.2026): РЕАЛИЗОВАНО, тесты GREEN
TDD `test_pref_outbox_link.py` (3/3) ALL OK. Регресс: test_orchestrator_local,
test_claim_validator_pref_dict, test_preference_dict_format,
test_preference_detector — PASS. UTF-8 без BOM. Без коммита.
Документация: TODO, ROADMAP_CLOSE_PLAN, CHANGELOG, PROJECT_STATE.
