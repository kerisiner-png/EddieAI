# П-1a: Смягчение порогов детектора предпочтений и закрытие контура (этаж 5, блок 1/2)

> **Для агентов-исполнителей:** реализовывать по шагам с TDD. Чекбоксы
> `- [ ]` для отслеживания. Коммиты НЕ делать (правило AGENTS.md: коммит
> только по явному запросу Эдди) — вместо коммита фиксировать diff + тесты.

**Цель:** сделать контур предпочтений реально работающим в проде: смягчить
сверхстрогие пороги `ActionPreferenceDetector`, не меняя формат
`self_state.preferences` (плоский список строк сохраняется — обратная
совместимость, минимальный дифф, без миграции). Это первый под-шаг П-1
этажа 5. Обогащение формата (сила/провенанс) — отдельный под-шаг П-1b.

**Архитектура:** детектор (`identity/action_preference_detector.py`) — единственная
точка, где решается, считать ли устойчивое повторение выбора «предпочтением».
Смягчаем пороги MIN_CHOICES=6→3 и MIN_SHARE=0.75→0.6. Значение preference
остаётся строкой `"{context_type}:action_method:{winner}"` — конвейер
детектор→evidence→proposal→`IdentityManager`→`self_state.preferences`
не меняется. Плюс добавляется отсутствующий TDD-покрытие детектора
(отдельного теста на него нет).

**Tech Stack:** Python 3, sqlite3 (memory/evidence), существующий код проекта.
Context7 сверяется при необходимости (datetime/json/sqlite — стандартная
библиотека, доп. внешних зависимостей нет).

**Spec:** `docs_engineer\ROADMAP_CLOSE_PLAN.md`, блок П-1 «Модель предпочтений».

## Глобальные ограничения (из AGENTS.md)

- UTF-8 строго без BOM; не править файлы через Set-Content/Out-File/Add-Content.
- Минимальные диффы; не переписывать подсистемы; обратная совместимость.
- TDD: тест как можно раньше.
- Документация после задачи: CHANGELOG, TODO, ROADMAP, PROJECT_STATE.
- Один пишущий исполнитель за раз.
- Данные личности (`data/*`) не трогать; работа идёт в тестовых БД.

---

### Task 1: Смягчить пороги детектора предпочтений

**Файлы:**
- Modify: `identity\action_preference_detector.py:16-17` (константы порогов)
- Test: `test_preference_detector.py` (новый)

**Интерфейсы:**
- Consumes: `ActionPreferenceDetector(memory, evidence)` — существующий
  контракт; метод `detect()` возвращает список dict с ключами
  `status/category/value/selected/counts/total_choices/share/created_evidence`.
- Produces: те же; только пороги мягче.

- [ ] **Шаг 1: Написать падающий тест** (`test_preference_detector.py`)

Паттерн взят из `final_regression_suite.py` (habit-детектор): строим отдельную
тест-БД, кладём ACTION_CHOICE-события с 3 повторами выбора одного варианта
из двух в одном контексте — при старых порогах (6/0.75) это НЕ предпочтение,
при новых (3/0.6) — должно стать. Тест файлом (не inline, правило кодировок):
кириллица в строках безопасна в utf-8 файле.

```python
import json
import tempfile
from pathlib import Path


def _action_payload(context, options, selected):
    return json.dumps(
        {"choice": {"context_type": context,
                    "options": options,
                    "selected": selected}},
        ensure_ascii=False,
    )


def test_preference_detector_lower_threshold(tmpdir):
    from memory.database import Memory
    from memory.events import Event
    from memory.evidence import EvidenceEngine
    from identity.action_preference_detector import (
        ActionPreferenceDetector,
    )

    db = Path(tmpdir) / "pref_test.db"
    memory = Memory(db)
    try:
        evidence = EvidenceEngine(memory)
        detector = ActionPreferenceDetector(memory, evidence)

        # 3 повтора выбора "read" из двух в одном контексте.
        for _ in range(3):
            memory.remember(Event.create(
                content=_action_payload("break", ["read", "walk"], "read"),
                event_type="ACTION_CHOICE",
                source_type="SELF_ACTION",
                personal_experience=True,
            ))

        results = detector.detect()

        assert results, "при смягчённом MIN_CHOICES ожидается предпочтение"
        assert results[0]["category"] == "preference"
        assert results[0]["value"] == "break:action_method:read"
        assert results[0]["selected"] == "read"
        assert results[0]["total_choices"] == 3
        assert results[0]["created_evidence"] == 3
    finally:
        memory.close()


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="pref_test_")
    test_preference_detector_lower_threshold(tmpdir)
    print("ALL OK")
```

Контракт события: `Event.create(content, event_type="ACTION_CHOICE",
source_type="SELF_ACTION", personal_experience=True)` — поля соответствуют
фильтру детектора (`_load_choice_groups`: event_type ACTION_CHOICE,
source_type SELF_ACTION, personal_experience=1). `timestamp` заполняет
`Event.create` автоматически. Детектор читает `content` как JSON с ключами
`choice.context_type/options/selected`.

Запуск — напрямую, как в остальных `test_*.py` проекта (pytest НЕ
установлен): `python test_preference_detector.py` → ожидается `ALL OK`.
Временная папка — через `tempfile.mkdtemp`, не `tmp_path` (pytest-fixture).

- [ ] **Шаг 2: Запустить тест — убедиться, что падает**

Run: `python -m pytest test_preference_detector.py -v` (или `python -c` через
файл, если pytest с кириллицей в консоли капризничает).
Expected: FAIL — детектор не находит предпочтение (3 < MIN_CHOICES 6).

- [ ] **Шаг 3: Реализовать смягчение порогов**

Финальные значения (уточнены разведкой при RED):
- `MIN_CHOICES 6 → 4` (смягчение количества повторений);
- `MIN_SHARE` держим 0.75 (явное большинство);
- `loser_count > 0` НЕ трогаем — детектор осознанно требует, чтобы
  альтернатива хотя бы раз выбиралась (реальное сравнение, не «всегда так
  делает»). Поэтому минимальный рабочий кейс — 4 выбора: 3/1 (share 0.75).

```python
# identity/action_preference_detector.py
# (ДО) MIN_CHOICES = 6
# (после)
MIN_CHOICES = 4
# MIN_SHARE = 0.75 и проверка loser_count>0 — БЕЗ изменений
```

Больше ничего в детекторе не менять (минимальный дифф).

- [ ] **Шаг 4: Запустить тест — убедиться, что проходит**

Run: `python -m pytest test_preference_detector.py -v`
Expected: PASS, `created_evidence == 3`.

- [ ] **Шаг 5: Негативный кейс — низкая доля не становится предпочтением**

Добавить в тот же файл второй тест: 3 выбора с разбросом 2/1 (share 0.67 <
0.75 старый, но нужен кейс против случайных шумов) — проверить, что при
смешанных выборах предпочтение НЕ создаётся, если нет стабильного лидера.

```python
def test_preference_requires_clear_majority(tmpdir):
    from memory.database import Memory
    from memory.events import Event
    from memory.evidence import EvidenceEngine
    from identity.action_preference_detector import (
        ActionPreferenceDetector,
    )

    db = Path(tmpdir) / "pref_majority.db"
    memory = Memory(db)
    try:
        evidence = EvidenceEngine(memory)
        detector = ActionPreferenceDetector(memory, evidence)

        for sel in ["read", "read", "walk"]:
            memory.remember(Event.create(
                content=_action_payload("break", ["read", "walk"], sel),
                event_type="ACTION_CHOICE",
                source_type="SELF_ACTION",
                personal_experience=True,
            ))

        results = detector.detect()
        assert results == []
    finally:
        memory.close()
```

(в блоке `__main__` добавить вызов
`test_preference_requires_clear_majority(tmpdir)` перед `print("ALL OK")`)

- [ ] **Шаг 6: Зафиксировать финальный порог MIN_CHOICES**

Разведка при RED выявила: детектор также требует `loser_count > 0`
(альтернатива выбиралась хоть раз — реальное сравнение). Значит, даже при
MIN_CHOICES=3 кейс 3/0 не срабатывает. Биологически осмысленное смягчение:
`MIN_CHOICES = 4` (кейс 3/1, share 0.75, сравнение есть). MIN_SHARE и
проверку loser_count НЕ трогаем. Итог в коде: MIN_CHOICES=4.

- [ ] **Шаг 7: Регресс**

Run: `python -m pytest test_preference_detector.py test_emotional_baseline.py test_life_prompt_blocks.py -v`
Expected: все PASS. Детектор не вызывается нигде, кроме agent_loop, формат
self_state.preferences не меняется — регресс ограничен.

- [ ] **Шаг 8: Байт-проверка кодировок**

Файлы `identity\action_preference_detector.py` и `test_preference_detector.py`:
UTF-8 без BOM, нет литеральных «?» и последовательностей «Ð»/«Ñ‚» в местах
русского текста.

- [ ] **Шаг 9: Документация**

CHANGELOG (03.09), TODO (П-1a закрыт, П-1b остался), ROADMAP (колонка
этажа 5 — П-1 частично), PROJECT_STATE (свежий блок). Коммит НЕ делать.
