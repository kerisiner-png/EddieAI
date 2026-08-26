# Паттерн ↔ Привычка — Implementation Plan

**Goal:** Связать оперативные паттерны решений (`situation_patterns`) с
личностными привычками (habit-черты в self_state) в один цикл обучения.

**Модель (принятая):**
- **Паттерн** — процедурная память «ситуация → действие»
  (`situation_patterns`). Быстрый, локальный, НЕ меняет self_state.
- **Привычка** — декларативная черта личности (category=habit),
  «я обычно так поступаю». Меняется только через lifecycle
  (evidence → proposal → promote).

**Tech Stack:** Python, без новых зависимостей. Используем штатный
конвейер EvidenceEngine → EvidenceConsolidator → PersonalityLifecycle.

## Задачи

### Задача 1: Новый источник evidence
`memory/provenance.py`: добавить source `DECISION_PATTERN` (вес 1.0) в
VALID_SOURCES и SOURCE_WEIGHTS. Паттерн — сильное свидетельство
устойчивого поведения (вес как SELF_EXPERIENCE).

### Задача 2: Консолидация паттерн → привычка
`core/decision_core.py`: DecisionCore получает `evidence` (EvidenceEngine).
Новый метод `consolidate_habits(min_uses=3) -> int`:
- выбрать паттерны с `times_used >= min_uses`;
- для каждого, если нет habit-evidence
  `value="situation_action:{situation_key}"` → `evidence.add(
  category="habit", value=..., source="DECISION_PATTERN",
  independence_key=f"situation:{situation_key}")`;
- идемпотентно (проверка evidence.get); повторный вызов не дублирует.
Дальше привычка проходит штатный evidence→consolidator→lifecycle→ACTIVE.

### Задача 3: Интеграция
- `core/autonomy_runtime_factory.py`: передать `evidence=self.agent.evidence`
  в DecisionCore.
- `core/autonomous_runtime.py`: на консолидации (рядом с learn_from_memory)
  вызвать `decision_core.consolidate_habits()`.

### Задача 4: Тест
`test_pattern_habit.py`:
- паттерн с times_used < порога → привычка НЕ создаётся;
- после bump до порога → consolidate_habits создаёт habit-evidence;
- повторный consolidate_habits → не дублирует (count не растёт);
- источник в evidence = DECISION_PATTERN.

## Критерий приёмки
- Устойчивый паттерн (переиспользован N раз) становится habit-evidence
  и затем чертой личности через штатный lifecycle.
- Паттерн сам по себе НЕ меняет self_state (остаётся процедурным).
- Обратная связь «привычка → паттерн» (черта подсказывает действие)
  — БЭКЛОГ, в этот план не входит.
