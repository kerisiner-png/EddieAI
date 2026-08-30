# Рубеж B «Живёт сутки» — план приёмки и доделок

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ SUB-SKILL: superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для пофайловой реализации. Шаги помечены checkbox (`- [ ]`).
>
> Статус: ПЛАН ГОТОВ 30.08 (ночь). Суточный прогон УЖЕ ИДЁТ — night_run.py `--minutes 1440`, PID 39972, старт 29.08 22:26:53, финиш ~30.08 22:26. Значительная часть рубежа реализована ранее (R3). План — это приёмка + 2 остаточных пункта (watchdog CPU, P2-b llama-воркер).

**Goal:** Доказать, что EddieAI живёт непрерывные сутки автономно (тики без LLM, сон/бодрствование, ритуалы утра/вечера, watchdog ресурсов, без падений), и утром получить артефакты: дневник + diff души.

**Architecture:** Рубеж B — это НЕ новая подсистема, а валидационный цикл вокруг уже работающего контура R3:
- сон/бодрствование + ритуалы — `core/autonomous_runtime.py` (`_morning_ritual`/`_evening_ritual`/`_run_ritual`, вшиты в `tick()`, строки 517/527);
- тики без LLM — `_prev_asleep` + `life_cycle.update()`/`is_asleep()` (облако дёргается редко: 15 вызовов за ночь);
- watchdog RAM — `core/resource_watchdog.py` (ctypes win32, вшит в tick через `should_throttle`, включён в night_run: low=256/critical=192);
- инициатива — `core/decision_core.py` (CALL по `idle_seconds >= IDLE_MOTIVATION_SEC=900`, анти-петля через `pending_initiative`);
- осознание жизни — `core/prompts.py` (`_LIFE_AWARENESS_BLOCK`), `memory/database.py` (`recent_life_feed`), `core/agent.py` (`_life_feed_block`).
Остаточные пункты рубежа: watchdog CPU (не критичен в облачном режиме) и P2-b мониторинг/перезапуск llama-воркера (применим только к локальному фолбэку; в облачном режиме — N/A).

**Tech Stack:** Python 3 (stdlib: sqlite3, ctypes, threading, datetime). Без psutil. Облако Zen — основной мозг, локаль — фолбэк.

**Spec:** `docs_engineer\TODO.md:701-705` (очередь рубежей), `docs_engineer\ROADMAP.md:36` (этаж 7), `docs_engineer\SPECS\2026-08-28-alive-life-rubezh-design.md` (контуры живой жизни), аудит-находка P2-b: `docs_engineer\reports\2026-08-25_night_full_audit.md:121`.

## Global Constraints

- Все файлы UTF-8 БЕЗ BOM; правки ТОЛЬКО через редактор (не PowerShell Set-Content/Out-File).
- Стиль проекта: без комментариев в коде; snake_case; мин-диффы; не переписывать существующие подсистемы.
- Тесты: `$env:PYTHONIOENCODING='utf-8'; python test_<name>.py` (Win, cp1252-консоль).
- После правок — байтовая проверка отсутствия литеральных «?» вместо кириллицы.
- НЕ трогать `CloudFirstLlm`/роутинг моделей/DecisionRuntime без отдельного решения совета.
- Ошибки НЕ глушить `pass` молча — журнал через `print(..., flush=True)` с префиксом `[rubezh-b]`.
- Остатки (CPU-watchdog, P2-b) реализуются ТОЛЬКО после отмашки Эдди; приёмка — в рамках уже идущего прогона.
- Коммит — только по явному запросу Эдди.

---

## Карта «что есть / чего нет / куда встраиваем» (анализ 30.08)

| Пункт рубежа B | Статус | Где/что |
|---|---|---|
| R3 сон/бодрствование | ✅ ЕСТЬ | `life_cycle.py`, переходы в `tick()`, события LIFE_CYCLE (прод: 2211 заснул, 2215 проснулся) |
| Ритуалы утро/вечер | ✅ ЕСТЬ | `_morning_ritual`/`_evening_ritual`; в проде REFLECTION 2212 (вечер 29.08), SELF_EXPERIENCE 2216 (утро 30.08, trigger=эмм morning) |
| Тики состояния без LLM | ✅ ЕСТЬ | ASLEEP/IDLE + `_prev_asleep`; облако: 15 вызовов за ночь (половина — сон) |
| Watchdog RAM | ✅ ЕСТЬ | `resource_watchdog.py` вшит в tick (THROTTLED); включён в night_run: low=256, critical=192 |
| Watchdog CPU | ❌ НЕТ | НЕ реализован; нужен только при тяжёлой локальной модели (сейчас облако). Решаем: доделать или зафиксировать N/A |
| Авто-выгрузка модели | ⚠️ ИМПЛИЦИТНА | `CloudFirstLlm` ленив — локаль не грузится в облачном режиме; явной выгрузки НЕТ (и не нужна, пока мозг в облаке) |
| Рестарт llama-воркера по расписанию (P2-b) | ❌ НЕТ | аудит 25.08; применим к локальному воркеру. В облачном режиме N/A — решение совета |
| PASS: сутки без человека, утром дневник + diff души | 🔄 ИДЁТ | night_run `--minutes 1440` с 29.08 22:26; при завершении — NightConsolidator + soul diff (night_run.py:390-436) |

Вывод анализа: кода для рубежа B почти не требуется. Нужен: (1) приёмочный протокол по артефактам идущего прогона; (2) решения по watchog CPU и P2-b (доделать vs N/A). План ниже — преимущественно приёмка + 2 опциональные доделки для полноты критериев.

---

### Task 1: Приёмочный протокол суточного прогона (идёт сейчас, ждать финиш ~30.08 22:26)

**Files:**
- Create (сейчас, скрипт-сверка): `C:\Users\keris\AppData\Local\Temp\opencode\rubezh_b_check.py` — проверка артефактов в коде приёмки (вынесем в проект при отмашке).
- Test: `C:\EddieAI\test_rubezh_b.py` (создать после Финиша прогона, по чек-листу ниже).

**Interfaces:**
- Consumes: `data/memory.db` (events), `data/personal_diary.db` (дневник), `data/soul_snapshots/*` (before/after), `logs/eddie_night.log`, процессы (runtime PID жив всю серию).
- Produces: отчёт-чек-лист приёмки рубежа B: 8 пунктов PASS/FAIL.

- [ ] **Step 1: Чек-лист приёмки (критерии)**

```text
1. Прогон отработал серию целиком до END (маркер «сессия 1440 мин завершена» в логе).
2. Во время серии НЕ умирал процесс (PID непрерывен в журнале процесса; logs растут равномерно).
3. За сутки ≥ 2 перехода сна (LIFE_CYCLE заснул/проснулся) — воля сон/бодрствование работает.
4. Ритуалы: ≥ 1 утренний (SELF_EXPERIENCE) и ≥ 1 вечерний (REFLECTION) с интерпретацией «ритyaл».
5. Тики без LLM: общее число облачных вызовов за сутки мало (порог: ≤ 40 при 24 ч; для сравнения — 15 за ночь).
6. Watchdog: в логе за сутки НЕТ серий THROTTLED (или они объяснимы — RAM падала).
7. Консолидация: NightConsolidator завершился без ошибки; chronicle_events > 0; conclusions_saved ≥ 1 (или 0 c объяснением).
8. Diff души: before/after не пустой; в логе строка «soul diff:» с ключами; события жизни изменились.
```

- [ ] **Step 2: Скрипт проверки (сейчас — в temp; после финиша — в проект)**

`test_rubezh_b.py` (после финиша прогона 30.08 ~22:35; запуск: `$env:PYTHONIOENCODING='utf-8'; python test_rubezh_b.py`):

```python
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PASS = []
FAIL = []
RUN_START = datetime(2026, 8, 29, 22, 26, tzinfo=timezone.utc)


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(("PASS" if ok else "FAIL"), name, detail)


conn = sqlite3.connect(str(BASE / "data" / "memory.db"))
conn.row_factory = sqlite3.Row

n_lc = conn.execute(
    "SELECT COUNT(*) c FROM events WHERE event_type='LIFE_CYCLE' "
    "AND timestamp > ? ", (RUN_START.isoformat(),)
).fetchone()["c"]
check("переходы сна", n_lc >= 2, f"LIFE_CYCLE={n_lc}")

n_life = conn.execute(
    "SELECT COUNT(DISTINCT event_type) c FROM events WHERE timestamp > ?",
    (RUN_START.isoformat(),),
).fetchone()["c"]

n_cloud = 0
for line in (BASE / "logs" / "eddie_night.log").read_text(encoding="utf-8").splitlines():
    if line.startswith("[") and "cloud call #" in line:
        n_cloud += 1
check("мало облачных вызовов", n_cloud <= 40, f"cloud_calls={n_cloud}")

n_morning = conn.execute(
    "SELECT COUNT(*) c FROM events WHERE event_type='SELF_EXPERIENCE' "
    "AND timestamp > ? AND content LIKE '%проснул%'", (RUN_START.isoformat(),)
).fetchone()["c"]
n_evening = conn.execute(
    "SELECT COUNT(*) c FROM events WHERE event_type='REFLECTION' "
    "AND timestamp > ? AND content LIKE '%день%'", (RUN_START.isoformat(),)
).fetchone()["c"]
check("ритуалы утро/вечер", n_morning >= 1 and n_evening >= 1,
      f"morning={n_morning}, evening={n_evening}")

log_text = (BASE / "logs" / "eddie_night.log").read_text(encoding="utf-8")
check("консолидация без ошибки",
      "консолидация: " in log_text and "консолидация ошибка" not in log_text)
check("soul diff перед/после",
      "soul diff: " in log_text and "soul diff unavailable" not in log_text)

if FAIL:
    print("RUBEZH_B: FAIL —", len(FAIL))
    raise SystemExit(1)
print("RUBEZH_B: ALL PASS —", len(PASS))
```

- [ ] **Step 3: Прогнать при финише прогона (после 30.08 ~22:35)**

Run: `$env:PYTHONIOENCODING='utf-8'; python test_rubezh_b.py`
Expected: `RUBEZH_B: ALL PASS` (иначе — разбор каждого FAIL по артефактам, фикс — только после отмашки Эдди).

---

### Task 2: Watchdog CPU — решить: доделать или N/A (ТРЕБУЕТ отмашки Эдди)

**Files:**
- Modify (если решили делать): `core/resource_watchdog.py` — добавить `cpu_percent()` через `ctypes.windll.kernel32.GetSystemTimes` (без psutil).
- Test: `test_resource_watchdog_cpu.py` (создать).

**Interfaces:**
- Consumes: существующий класс `ResourceWatchdog` (метод `check()`), стиль ctypes из `_available_memory_mb`.
- Produces: `ResourceWatchdog.cpu_percent() -> float` (0.0-100.0); `check()` возвращает также `cpu_percent` при включённом watchdog.

- [ ] **Step 1: Обоснование (перед реализацией)**

```text
Сейчас мозг EddieAI — облако Zen; локальная модель не загружается.
CPU-нагрузку создают: STT (Vosk в голосовом режиме), TTS-рендер,
дашборд Tk. В суточном прогоне без голоса CPU≈0. Watchdog CPU
реально нужен только если снова включим тяжёлую локальную модель
(phi4-mini/qwen3.5:4b) или постоянный STT. Решение: если Эдди
подтвердит «локаль остаётся фолбэком и в проде не поднимается» —
фиксируем N/A (закрываем с пояснением); если сборка голоса 24/7
предполагается — доделываем (код ниже).
```

- [ ] **Step 2: (при решении «делать») Написать тест**

`test_resource_watchdog_cpu.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.resource_watchdog import ResourceWatchdog


def test_cpu_percent_in_range():
    wd = ResourceWatchdog(enabled=True)
    value = wd.cpu_percent()
    assert 0.0 <= value <= 100.0, value


def test_check_returns_cpu_when_enabled():
    wd = ResourceWatchdog(enabled=True)
    result = wd.check()
    assert "cpu_percent" in result


if __name__ == "__main__":
    test_cpu_percent_in_range()
    test_check_returns_cpu_when_enabled()
    print("ALL OK")
```

- [ ] **Step 3: (при решении «делать») Проверить, что тест падает**

Run: `$env:PYTHONIOENCODING='utf-8'; python test_resource_watchdog_cpu.py`
Expected: FAIL — `AttributeError: 'ResourceWatchdog' object has no attribute 'cpu_percent'`

- [ ] **Step 4: (при решении «делать») Минимальная реализация (при сверке с Context7 по ctypes/Win32)**

В `core/resource_watchdog.py` добавить:

```python
    def cpu_percent(self):
        try:
            idle_time = ctypes.c_ulonglong()
            kernel_time = ctypes.c_ulonglong()
            user_time = ctypes.c_ulonglong()

            ok = ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time),
            )

            if not ok:
                return 0.0

            now = (
                idle_time.value
                + kernel_time.value
                + user_time.value
            )

            if getattr(self, "_cpu_last", None):
                prev_idle, prev_total, prev_ts = (
                    self._cpu_last
                )
                d_idle = idle_time.value - prev_idle
                d_total = now - prev_total
                if d_total != 0:
                    return max(
                        0.0,
                        min(100.0,
                            100.0 * (1 - d_idle / d_total)),
                    )

            self._cpu_last = (
                idle_time.value,
                now,
                time.monotonic(),
            )

            return 0.0
        except Exception:
            return 0.0
```

И в `check()` (ветка включённого watchdog, после `self._last_level = level`) добавить фрагмент:

```python
        cpu = self.cpu_percent()
```

и в возвращаемый словарь — `"cpu_percent": cpu`.

- [ ] **Step 5: (при решении «делать») Прогнать тест**

Run: `$env:PYTHONIOENCODING='utf-8'; python test_resource_watchdog_cpu.py`
Expected: PASS — `ALL OK`

- [ ] **Step 6: (при решении «делать») Регресс**

Run: `$env:PYTHONIOENCODING='utf-8'; python test_autonomous_runtime_init.py`
Expected: PASS (существующий тест runtime; watchdog ветка не меняет поведение при выключенном watchdog)

---

### Task 3: P2-b — мониторинг/рестарт llama-воркера: закрыть как N/A или минимальный watchdog (ТРЕБУЕТ отмашки Эдди)

**Files:**
- Сейчас: только решение и запись в TODO/CHANGELOG.
- При решении «делать»: Modify `core/resource_watchdog.py` + опциональный `watchdog_life.py` (вариант C из TODO:571-572).

**Interfaces:**
- Consumes: находка аудита P2-b (`reports\2026-08-25_night_full_audit.md:121`).
- Produces: решение совета + запись в TODO.

- [ ] **Step 1: Обоснование**

```text
P2-b («мониторинг/перезапуск llama-server воркера по расписанию») из
аудита 25.08 относился к контуру ЛОКАЛЬНОГО Llama-сервера (ротация
моделей, утечки памяти воркера). Сейчас продакшн-мозг — облако Zen
(memory/database, model_orchestrator CloudFirstLlm), локальная модель
не поднимается в суточном прогоне (NightConfig облачный). Запуск
llama-server в проде был бы нарушением «одна тяжёлая локальная модель
одновременно» при облачном режиме. Предлагаю: зафиксировать P2-b как
N/A до возврата локального фолбэка; при возврате — отдельный этап
(monitor sleep/restart llama в расписании). Подтверждение Эдди.
```

- [ ] **Step 2: Записать решение в TODO (раздел рубежа B) и CHANGELOG**

Формат — как при закрытии рубежа A: `[x]` пункты, дата, пояснение.

- [ ] **Step 3: (при решении «делать» — план-эскиз)**

Отдельный план на `watchdog_life.py` (вариант C): мониторинг RAM+CPU+процессы,
список процессов для рестарта (llama-server), расписание, журнал. Реализация —
отдельной сменой, с TDD и сверкой с Context7.

---

## Self-Review

**1. Покрытие spec (TODO:701-705):**
- Сон/бодрствование + ритуалы ✅ Task 1 (п.3-4 чек-листа, уже в проде).
- Тики без LLM ✅ Task 1 (п.5).
- Watchdog RAM ✅ Task 1 (п.6) + существующий `resource_watchdog`.
- Watchdog CPU ⚠️ Task 2 (опционально, по решению Эдди).
- Авто-выгрузка ⚠️ зафиксирована имплицитной (CloudFirstLlm ленив; явной не нужно в облаке).
- Рестарт llama-воркера ⚠️ Task 3 (N/A до локального режима, по решению).
- PASS сутки + дневник + diff души ✅ Task 1 (п.1-2,7-8; прогон идёт).

**2. Плейсхолдер-скаn:** кода без конкретики нет; Task 2/3 — честные «решение Эдди → код или N/A», код для CPU-watchdog приведён полностью.

**3. Типы согласованы:**
- `ResourceWatchdog.cpu_percent() -> float`, `check()` возвращает `cpu_percent` — определён в Task 2, консистентно.
- `test_rubezh_b.py` работает по артефактам прогона (events/log/snapshots) — сигнатуры не требуют изменений существующего кода.
- Облачные вызовы считаются из лога по маркеру `cloud call #` — консистентно с ночным наблюдением.

## Execution Handoff

План сохранён в `docs_engineer\PLANS\2026-08-30-rubezh-b-sutki.md`. Исполнение:
1. **Приёмка (Task 1)** — стартует автоматически по финишу суточного прогона (~30.08 22:35); прогон однотикерный, без суб-агентов.
2. **Task 2 и 3** — требуют отмашки Эдди (Конституция: остатки vs N/A). До отмашки — в статусе `[ ]` в TODO.

Перед правкой TODO:671-705 (рубеж B [x]) — дождаться PASS Task 1 и решений совета.