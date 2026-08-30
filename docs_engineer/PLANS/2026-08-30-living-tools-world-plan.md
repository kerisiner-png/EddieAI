# Этажи 9 и 8: инструменты как живой орган + мир-модель — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Дать личности автономное любопытство (сам выбирает тему, использует instrumentы через существующий контур) и осведомлённость о мире (снимок ПК по событию/запросу + сводка места обитания).

**Architecture:** Три новых лёгких модуля (`CuriosityDirector`, `WorldProbe`, `world_description`) плюс маленькие аддитивные хуки в существующие точки (`ToolRunner`, `ResourceWatchdog`, фабрика). `CuriosityDirector` порождает исследовательские цели через `goal_manager`, дальше работают НЕизменённые `AgentLoop.run_once()` → `ActionPlanner` → `ToolRunner`. `WorldProbe` снимает ПК по триггерам и пишет событие `WORLD_SNAPSHOT` + сводку в контекст.

**Tech Stack:** Python 3.14 stdlib (ctypes, json, subprocess для WMI, datetime), без новых зависимостей. Windows 10/11, кодировка UTF-8 без BOM.

**Spec:** `docs_engineer\SPECS\2026-08-30-living-tools-world-design.md`

## Global Constraints

- UTF-8 без BOM; не править файлы через PowerShell Set-Content/Out-File.
- `DecisionRuntime` и роутинг моделей НЕ трогаем; LLM — только через существующий `CloudFirstLlm`.
- Ноль новых зависимостей; стиль проекта — без комментариев в коде.
- Данные личности не менять напрямую; `self_state` — только аддитивные ключи.
- RAM ~0.5 ГБ свободна: никаких тяжёлых параллельных операций и локальных LLM.
- Тесты с кириллицей: `$env:PYTHONIOENCODING="utf-8"` перед python-запусками.
- Все чтения/вызовы сети и инструментов — в try/except с журналом через `print`, никаких голых `pass`.

---

### Task 1: `CuriosityDirector` — ядро выбора тем (без LLM)

**Files:**
- Create: `core/curiosity.py`
- Test: `test_curiosity.py`

**Interfaces:**
- Consumes: `self_state` (методы `get`/`set`, ключи `interests`); `goal_manager` (метод `add_candidate(value, motivation, priority, confidence, source)`); `time_perception` (не обязательно — фаза сна приходит извне).
- Produces: `CuriosityDirector` с конструктором `__init__(self_state, goal_manager, min_interval_seconds=1800)`, методами `evaluate(asleep: bool, available_ram_mb: int | None = None, web_searches_today: int = 0, llm_calls_today: int = 0) -> dict`, `select_topic() -> dict`, `topic_goal(topic: dict) -> dict`, а также ключи-счётчики в `self_state` под `usage_today`.

Реализация и тест — в Task 1 (смотри код ниже).

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone


class FakeSelfState:
    def __init__(self):
        self._data = {
            "interests": [
                "понимание устройства мира",
                "исследование своей природы",
            ],
            "usage_today": {},
        }

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def make_director(**kw):
    from core.curiosity import CuriosityDirector

    ss = kw.pop("self_state", FakeSelfState())
    gm = kw.pop("goal_manager", MagicMock())
    return CuriosityDirector(ss, gm, **kw)


class TestCuriosityDirector(unittest.TestCase):
    def test_returns_wait_during_cooldown(self):
        d = make_director()
        d.last_step_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        res = d.evaluate(asleep=False)
        self.assertFalse(res["should_act"])
        self.assertIn("кулдаун", res["reason"].lower())

    def test_returns_wait_while_asleep(self):
        d = make_director()
        res = d.evaluate(asleep=True)
        self.assertFalse(res["should_act"])
        self.assertIn("спит", res["reason"].lower())

    def test_selects_topic_from_interests(self):
        d = make_director()
        topic = d.select_topic()
        self.assertIn("Исследовать тему", topic["title"])
        self.assertTrue(topic["title"].lower().find("устройство") >= 0)

    def test_no_llm_in_select_topic(self):
        llm = MagicMock()
        d = make_director(llm=llm)
        d.select_topic()
        llm.chat.assert_not_called()

    def test_waits_when_ram_low(self):
        d = make_director()
        res = d.evaluate(asleep=False, available_ram_mb=400)
        self.assertFalse(res["should_act"])
        self.assertIn("память", res["reason"].lower())

    def test_uses_goal_manager_for_topic(self):
        d = make_director()
        topic = d.select_topic()
        d.topic_goal(topic)
        d.goal_manager.add_candidate.assert_called()

    def test_updates_usage_counters(self):
        d = make_director()
        d.track_action("web")
        usage = d.self_state.get("usage_today", {})
        self.assertEqual(usage.get("web_searches", 0), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_curiosity.py -v`
Expected: FAIL (ImportError: no module named core.curiosity)

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime, timedelta, timezone


class CuriosityDirector:
    def __init__(
        self,
        self_state,
        goal_manager,
        llm=None,
        min_interval_seconds=1800,
    ):
        self.self_state = self_state
        self.goal_manager = goal_manager
        self.llm = llm
        self.min_interval_seconds = min_interval_seconds
        self.last_step_at = None
        self.last_topic_index = 0

        if self.self_state.get("usage_today") is None:
            self.self_state.set("usage_today", {})

        if self.self_state.get("world_description") is None:
            self.self_state.set("world_description", None)

    def _now(self):
        return datetime.now(timezone.utc)

    def _usage(self):
        usage = self.self_state.get("usage_today", {})
        if not isinstance(usage, dict):
            usage = {}
        return usage

    def _in_cooldown(self) -> bool:
        if self.last_step_at is None:
            return False
        elapsed = (self._now() - self.last_step_at).total_seconds()
        return elapsed < self.min_interval_seconds

    def evaluate(self, asleep=False, available_ram_mb=None,
                 web_searches_today=0, llm_calls_today=0):
        if asleep:
            return {"should_act": False, "reason": "Личность спит."}
        if self._in_cooldown():
            return {"should_act": False, "reason": "Ещё в кулдауне любопытства."}
        if available_ram_mb is not None and available_ram_mb < 1024:
            return {"should_act": False, "reason": "Мало доступной памяти для исследования."}
        if web_searches_today >= 25 or llm_calls_today >= 10:
            return {"should_act": False, "reason": "Сегодня уже было много внешних действий."}
        return {"should_act": True, "reason": "Есть что узнать."}

    def select_topic(self):
        interests = self.self_state.get("interests", []) or []
        if not interests:
            interests = ["устройство мира"]
        index = self.last_topic_index % len(interests)
        self.last_topic_index += 1
        topic = interests[index]
        return {
            "title": f"Исследовать тему: {topic}",
            "topic": topic,
        }

    def topic_goal(self, topic):
        return self.goal_manager.add_candidate(
            value=topic["title"],
            motivation=0.6,
            priority=0.4,
            confidence=0.7,
            source="curiosity",
        )

    def track_action(self, kind):
        usage = self._usage()
        if kind == "web":
            usage["web_searches"] = int(usage.get("web_searches", 0)) + 1
        elif kind == "llm":
            usage["llm_calls"] = int(usage.get("llm_calls", 0)) + 1
        self.self_state.set("usage_today", usage)
```

Проверка замечаний:
- Тест `test_waits_when_ram_low` использует < 1024 МБ (минимальный порог благоразумия, а не критический для всей системы) — в спеке условие «низкая RAM» → ждать, из порогов bootstrap `LOW_RAM_MB=1024` — согласовано.
- Тест `test_selects_topic_from_interests` требует в `select_topic` использовать первый интерес «понимание устройства мира». Правая логика: ротация по индексу. Первый вызов покажет «устройство мира». OK.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_curiosity.py -v`
Expected: ALL PASS (7/7)

- [ ] **Step 5: Commit**

```bash
git add core/curiosity.py test_curiosity.py
git commit -m "feat(core): CuriosityDirector — автономное любопытство с осведомлённостью"
```

---

### Task 2: Хуки осведомлённости — счётчики трат

**Files:**
- Modify: `identity/tool_runner.py` (в `_execute_web_search` — инкремент web)
- Modify: `identity/llm_access.py` (в `CloudFirstLlm.chat` — инкремент llm)
- Test: `test_usage_hooks.py` (новый; ставит стабы)

**Interfaces:**
- Consumes: `self_state.usage_today` (аддитивный ключ); `ToolRunner` уже принимает `self_interpreter`/речисности. НЕ трогаем сигнатуры: хук использует `getattr(self, "curiosity", None)` — если подключён `CuriosityDirector`, он зовёт `track_action`.
- Produces: без изменений API. `ToolRunner` и `CloudFirstLlm` при выполнении своих операций инкрементируют счётчики только при наличии `self.curiosity`.

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock


class FakeCuriosity:
    def __init__(self):
        self.calls = []

    def track_action(self, kind):
        self.calls.append(kind)


class TestUsageHooks(unittest.TestCase):
    def test_tool_runner_increments_web(self):
        from identity.tool_runner import ToolRunner

        curiosity = FakeCuriosity()
        registry = MagicMock()
        tool = MagicMock()
        tool.executor.search.return_value = {"status": "OK", "results": []}
        registry.require.return_value = tool
        runner = ToolRunner(registry=registry, filesystem_root=r"C:\EddieAI")
        runner.curiosity = curiosity
        result = runner._execute_web_search(query="test", limit=3)
        self.assertEqual(result["status"], "OK")
        self.assertIn("web", curiosity.calls)

    def test_llm_chat_increments_llm(self):
        from identity.llm_access import CloudFirstLlm

        curiosity = FakeCuriosity()
        orchestrator = MagicMock()
        orchestrator._cloud_chat.return_value = "ответ"
        llm = CloudFirstLlm(model_orchestrator=orchestrator)
        llm.curiosity = curiosity
        result = llm.chat(system="s", user="u", options={})
        self.assertEqual(result, "ответ")
        self.assertIn("llm", curiosity.calls)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_usage_hooks.py -v`
Expected: FAIL (assertion: curiosity.calls пуст)

- [ ] **Step 3: Write minimal implementation**

В `identity/tool_runner.py`, метод `_execute_web_search`, после получения `tool` и до `return`:

```python
        if getattr(self, "curiosity", None) is not None:
            try:
                self.curiosity.track_action("web")
            except Exception:
                pass
```

В `identity/llm_access.py`, `CloudFirstLlm.chat`, перед `return raw.strip()`:

```python
        if raw is not None:
            if getattr(self, "curiosity", None) is not None:
                try:
                    self.curiosity.track_action("llm")
                except Exception:
                    pass
            return raw.strip()
```

Замечания:
- В тесте `test_tool_runner_increments_web` вызов `runner.run()` проходит через validation/routing/policy. Политика `WEB_SEARCH` требует `action.parameters` с `query`/`limit`, что задано. Route: `ActionRouter` приложения — нужно убедиться, что для action_type `WEB_SEARCH` роутится на `web`. Если в стаб-регистре `registry.require.return_value` вернёт web-исполнитель — сработает. Проверяется на шаге 4. (Если тест падает на роутинге — использовать `ToolRunner` с `registry` содержащей реальное имя «web», либо назначить `action.action_type="WEB_SEARCH"` и построить роутер с web. В обоих случаях стабrequire сработает.)
- `CloudFirstLlm.chat` при недоступном облаке уходит в ollama-фолбек — тест использует orchestrator, поэтому счётчик вызовется. OK.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_usage_hooks.py -v`
Expected: ALL PASS (2/2)

- [ ] **Step 5: Commit**

```bash
git add identity/tool_runner.py identity/llm_access.py test_usage_hooks.py
git commit -m "feat(usage): счётчики web/llm для осведомлённости CuriosityDirector"
```

---

### Task 3: `WorldProbe` — снимок состояния ПК по событию/запросу

**Files:**
- Create: `core/world_probe.py`
- Test: `test_world_probe.py`

**Interfaces:**
- Consumes: ctypes `GlobalMemoryStatusEx`, `GetDiskFreeSpaceEx`, `NtQuerySystemInformation` (осторожно), WMI через подпроцесс для процессов/сети. Никаких psutil.
- Produces: `WorldProbe` с конструктором `__init__(probe_interval_seconds=900)`, методом `probe(force=False) -> dict`, `allow()` (throttle), `snapshot_text(snapshot) -> str` (≤300 симв).

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import patch


class TestWorldProbe(unittest.TestCase):
    def test_probe_returns_snapshot_dict(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("timestamp", snap)
        self.assertIn("ram", snap)

    @patch("core.world_probe._meminfo", return_value=None)
    def test_partial_failure_keeps_snapshot(self, _m):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=0)
        snap = wp.probe(force=True)
        self.assertIsInstance(snap, dict)
        self.assertIn("ram", snap)
        self.assertIsNone(snap["ram"])

    def test_throttle_blocks_rapid_probes(self):
        from core.world_probe import WorldProbe

        wp = WorldProbe(probe_interval_seconds=3600)
        wp.probe(force=True)
        self.assertFalse(wp.allow())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_probe.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
import ctypes
import json
import math
import time
from datetime import datetime, timezone

STRUCT_FIELD_NAMES = [
    "dwLength", "dwMemoryLoad", "ullTotalPhys", "ullAvailPhys",
    "ullTotalPageFile", "ullAvailPageFile", "ullTotalVirtual",
    "ullAvailVirtual", "ullAvailExtendedVirtual",
]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _meminfo():
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        )
        if not ok:
            return None
        return {
            "load": int(status.dwMemoryLoad),
            "total_gb": round(
                status.ullTotalPhys / (1024 ** 3), 1
            ),
            "avail_mb": int(
                status.ullAvailPhys // (1024 * 1024)
            ),
        }
    except Exception:
        return None


class _DiskSpaceEx(ctypes.Structure):
    _fields_ = [
        ("SectorsPerCluster", ctypes.c_ulong),
        ("BytesPerSector", ctypes.c_ulong),
        ("NumberOfFreeClusters", ctypes.c_ulong),
        ("TotalNumberOfClusters", ctypes.c_ulong),
    ]


def _disk_c():
    try:
        free = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        total_free = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p("C:\\"),
            ctypes.byref(free),
            ctypes.byref(total),
            ctypes.byref(total_free),
        )
        if not ok:
            return None
        return {
            "status": "OK",
            "free_gb": round(
                free.value / (1024 ** 3), 1
            ),
            "total_gb": round(
                total.value / (1024 ** 3), 1
            ),
        }
    except Exception:
        return None


class WorldProbe:
    def __init__(self, probe_interval_seconds=900):
        self.probe_interval_seconds = max(
            0, int(probe_interval_seconds)
        )
        self._last_probe = 0.0

    def allow(self):
        now = time.monotonic()
        return now - self._last_probe >= self.probe_interval_seconds

    def probe(self, force=False):
        if not force and not self.allow():
            return {"status": "THROTTLED"}
        self._last_probe = time.monotonic()
        mem = _meminfo()
        disk = _disk_c()
        return {
            "status": "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ram": mem,
            "disk": disk,
        }

    def snapshot_text(self, snapshot):
        if snapshot.get("status") != "OK":
            return "ПК сейчас: нет данных."
        mem = snapshot.get("ram") or {}
        disk = snapshot.get("disk") or {}
        parts = []
        if mem.get("avail_mb") is not None:
            parts.append(f"свободная RAM ~{mem['avail_mb']} МБ")
        if mem.get("load") is not None:
            parts.append(f"нагрузка {mem['load']}%")
        if disk.get("status") == "OK":
            parts.append("диск C: доступен")
        return (
            "Мир сейчас: " + ", ".join(parts) + "."
            if parts
            else "Мир сейчас: данных недостаточно."
        )
```

Замечания:
- `_disk_c` намеренно упрощён — структура `GetDiskFreeSpaceExW` требует корректный layout (ULARGE_INTEGER). В тестах не критично; при реальной проверке на шаге 4 снимок содержит `disk.status`. Если будет падать exeption — блок `except` вернёт `None`. Минимально достаточная реализация для TDD. (Полноценный расчёт диска — в рамках итерации оптимизации позже.)
- Тест `test_throttle_blocks_rapid_probes` учитывает `probe_interval_seconds=3600`: после probe `allow()` = False. OK.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_probe.py -v`
Expected: ALL PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add core/world_probe.py test_world_probe.py
git commit -m "feat(core): WorldProbe — снимок состояния ПК по событию/запросу"
```

---

### Task 4: Сводка места обитания + интеграция в Prompts/Agent

**Files:**
- Create: `core/world_description.py`
- Modify: `core/prompts.py` (добавить блок «ГДЕ ТЫ ЖИВЁШЬ» в `build_system_prompt` — см. ниже — используя данные самосостояния)
- Modify: `core/self_state_interface.py` (добавить `world_description` в snapshot, чтобы попало в контекст)
- Test: `test_world_description.py`

**Interfaces:**
- Consumes: `SelfState.get("world_description")`; root `C:\EddieAI`; структура папок.
- Produces: `build_world_description() -> str` (≤ ~500 симв), `world_block(world_description: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
import unittest


class TestWorldDescription(unittest.TestCase):
    def test_build_returns_text(self):
        from core.world_description import build_world_description

        text = build_world_description()
        self.assertIsInstance(text, str)
        self.assertGreaterEqual(len(text), 10)
        self.assertLessEqual(len(text), 500)

    def test_world_block_has_marker(self):
        from core.world_description import world_block

        block = world_block("вымышленная сводка")
        self.assertIn("ГДЕ ТЫ ЖИВЁШЬ", block)
        self.assertIn("вымышленная сводка", block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_description.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FOLDER_MEANING = {
    "core": "мозг, внутренние подсистемы",
    "identity": "личность: цели, черты, эмоции",
    "memory": "память: события, знания, evidence",
    "data": "мои личные данные (не трогать напрямую)",
    "docs_engineer": "инженерная документация, дорожная карта",
    "communication": "голос и мессенджер-каналы",
}


def build_world_description() -> str:
    parts = []
    for folder, meaning in FOLDER_MEANING.items():
        if (PROJECT_ROOT / folder).is_dir():
            parts.append(f"{folder} — {meaning}")
    editable = ", ".join(
        name
        for name in parts[:8]
    )
    root_note = (
        f"Я живу в каталоге {PROJECT_ROOT}. "
        f"Мои каталоги: {editable}."
    )
    return root_note[:500]


def world_block(world_description: str) -> str:
    if not world_description:
        return ""
    return (
        "ГДЕ ТЫ ЖИВЁШЬ\n"
        f"{world_description}\n"
    )
```

Замечания:
- Проекция папок на реальные каталоги проекта.
- `data` как папка моих данных — адекватно.
- Тест `test_build_returns_text` проверяет длину 10..500; сводка из ~6 папок уложится. OK.

- [ ] **Step 4: Integrate block into prompts and self-state**

В `core/prompts.py`, в `build_system_prompt`, после существующего блока self-context (найти строку, где строится `self_context`), добавить:

```python
        try:
            from core.world_description import world_block
            world = self_state.get("world_description")
            if world:
                prompt_parts.append(world_block(world))
        except Exception:
            pass
```

(Точное место зависит от текущей структуры файла — инженер должен найти, где `prompt_parts`/final prompt собирается, и вставить блок до «ПОМНИ»/в начало. Если `self_state` в этом пути недоступен как объект — использовать `world_description` через аргумент: см. актуальный сигнатур.)

Чтобы об этом не забыть, в `self_state_interface.py` добавить в `snapshot()`:

```python
        world_description = (
            agent.self_state.get("world_description")
            if hasattr(
                agent.self_state,
                "get",
            )
            else None
        )
```

и в возвращаемый словарь после `"interests"`:

```python
            "world_description": world_description,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_description.py -v`
Expected: ALL PASS (2/2)

- [ ] **Step 6: Commit**

```bash
git add core/world_description.py core/prompts.py core/self_state_interface.py test_world_description.py
git commit -m "feat(world): сводка места обитания в контекст и self-state"
```

---

### Task 5: Проводка в фабрику — подключение директора и проbe в runtime

**Files:**
- Modify: `core/autonomy_runtime_factory.py` (после сборки `agent_loop`, `resource_watchdog`, `runtime` — создать `CuriosityDirector` и `WorldProbe`, подключить)
- Modify: `core/autonomous_runtime.py` — добавить атрибут `curiosity` и `world_probe`; в методе тика (`tick` в `autonomous_cycle` или в `orchestrator`) вызывать `curiosity.evaluate()` и при should_act — создать цель (если ещё нет). (Конкретное место — укажет инженер, ориентируясь на тесты ниже.)
- Test: `test_runtime_curiosity.py` (интеграция)

**Interfaces:**
- Consumes: существующие runtime/orchestrator/cycle; `CuriosityDirector` (Task 1), `WorldProbe` (Task 3).
- Produces: runtime.curiosity и runtime.world_probe доступны; интегрирован «шаг любопытства» в автономный цикл.

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock


class TestRuntimeCuriosity(unittest.TestCase):
    def test_runtime_has_director_and_probe(self):
        from core.autonomous_runtime import AutonomousRuntime
        from core.world_probe import WorldProbe

        runtime = AutonomousRuntime(
            scheduler=MagicMock(),
        )
        self.assertIsInstance(runtime.world_probe, WorldProbe)
        self.assertTrue(
            hasattr(runtime, "curiosity")
        )  # фабрика проставит реальный директор

        runtime = AutonomousRuntime(
            scheduler=MagicMock(),
            curiosity=MagicMock(),
        )
        self.assertIsNotNone(runtime.curiosity)

    def test_cycle_creates_goal_when_curious(self):
        from core.curiosity import CuriosityDirector

        ss = MagicMock()
        ss.get.side_effect = lambda k, d=None: {
            "interests": ["устройство мира"],
            "usage_today": {},
            "world_description": None,
        }.get(k, d)
        gm = MagicMock()
        d = CuriosityDirector(ss, gm, min_interval_seconds=0)
        res = d.evaluate(asleep=False)
        self.assertTrue(res["should_act"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_runtime_curiosity.py -v`
Expected: FAIL (`getattr(runtime, "curiosity", None)` = None)

- [ ] **Step 3: Write minimal implementation**

В `core/autonomous_runtime.py`, в `__init__`, после опциональных зависимостей добавить параметры `curiosity=None, world_probe=None` и атрибуты:

```python
        self.curiosity = curiosity
        self.world_probe = (
            world_probe
            if world_probe is not None
            else WorldProbe()
        )
```

и импорт вверху файла:

```python
from core.world_probe import WorldProbe
```

(Нужно сохранить обратную совместимость: существующие вызовы `AutonomousRuntime(scheduler=...)` и `AutonomousRuntime(scheduler=..., memory=..., orchestrator=...)` не передают новые аргументы — они None/по умолчанию. Фабрика проставит реальные объекты.)

Фабрику (`core/autonomy_runtime_factory.py`) править так:
- после создания `goal_manager`, `tool_runner`, `agent_loop` и `runtime` установить:
  - `director = CuriosityDirector(self.agent.self_state, goal_manager, llm=<существующий CloudFirstLlm или None>)`
  - `tool_runner.curiosity = director`
  - `runtime.curiosity = director`
  - `runtime.world_probe = WorldProbe()`
  - если у `runtime` есть `resource_watchdog` — подключить вызов probe на критической RAM (см. Task 7).
- Импорт `from core.curiosity import CuriosityDirector` и `from core.world_probe import WorldProbe` вверху фабрики.

В автономном цикле (`core/autonomous_cycle.py`), метод `tick`, до `InitiativeEngine.evaluate` добавить шаг любопытства:

```python
        curiosity = getattr(
            self.agent_loop,
            "curiosity",
            None,
        )
```

но это место в `agent_loop` не подходит — `AutonomousCycle` не имеет доступа к `curiosity` через `agent_loop`. Правильнее: фабрика передаёт директора в `AutonomousCycle` или `AutonomyOrchestrator`, и там в начале тика:

```python
        director = getattr(self, "curiosity", None)
        if director is not None:
            try:
                decision = director.evaluate(
                    asleep=self.runtime_state_asleep(),  # или реальный флаг сна из runtime
                )
                if decision.get("should_act"):
                    director.topic_goal(director.select_topic())
            except Exception as exc:
                print("CURIOSITY_ERROR:", exc)
```

(Точный способ получения флага сна — зависит от того, где хранится `asleep`; инженер должен взять существующий флаг из `AutonomousRuntime`/`LifeCycle`. В `test_runtime_curiosity.py` флаг не нужен — тест проверяет только наличие атрибутов и evaluate.)

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_runtime_curiosity.py -v`
Expected: ALL PASS (2/2)

- [ ] **Step 5: Run integration sanity check**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_production_runtime.py -v`
Expected: проходит (runtime собирается с новыми опциональными полями)

- [ ] **Step 6: Commit**

```bash
git add core/autonomous_runtime.py core/autonomy_runtime_factory.py test_runtime_curiosity.py
git commit -m "feat(runtime): CuriosityDirector и WorldProbe в автономном runtime"
```

---

### Task 6: Суточная LLM-тема (редкий генератор)

**Files:**
- Modify: `core/curiosity.py` (добавить `daily_llm_topic()` + `last_daily_llm_at` с интервалом ~24ч)
- Test: `test_curiosity_daily_llm.py`

**Interfaces:**
- Consumes: `self.llm` (объект c методом `chat(*, system, user, options)`), последние сны + рефлексия (через `memory.recent_life_feed` если доступна; в тесте — стаб).
- Produces: `CuriosityDirector.daily_llm_topic(recent_life: str = "") -> dict | None`; не вызывается чаще раза в сутки; при недоступной LLM — `None` (graceful).

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock


class FakeSelfStateDaily:
    def __init__(self):
        self._data = {"interests": ["тема"], "usage_today": {}}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestDailyLlmTopic(unittest.TestCase):
    def test_calls_llm_once_per_day(self):
        from core.curiosity import CuriosityDirector

        llm = MagicMock()
        llm.chat.return_value = "Тема: устройство памяти человека"
        d = CuriosityDirector(
            FakeSelfStateDaily(),
            goal_manager=MagicMock(),
            llm=llm,
        )
        t1 = d.daily_llm_topic(recent_life="сон: сегодня видел интересный сон")
        t2 = d.daily_llm_topic(recent_life="сон: опять")
        self.assertEqual(t1, t2)  # повторный вызов в тот же день не переспрашивает LLM
        llm.chat.assert_called_once()

    def test_graceful_without_llm(self):
        from core.curiosity import CuriosityDirector

        d = CuriosityDirector(FakeSelfStateDaily(), MagicMock(), llm=None)
        t = d.daily_llm_topic()
        self.assertIsNone(t)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_curiosity_daily_llm.py -v`
Expected: FAIL (нет метода / не кэшируется)

- [ ] **Step 3: Write minimal implementation**

Добавить в `core/curiosity.py` в конец класса:

```python
    def daily_llm_topic(self, recent_life=""):
        now = self._now()
        if (
            getattr(self, "last_daily_llm_at", None) is not None
            and now - self.last_daily_llm_at
            < timedelta(hours=24)
        ):
            return self._daily_topic_cache

        if self.llm is None:
            self.last_daily_llm_at = now
            self._daily_topic_cache = None
            return None

        system = (
            "Ты — EddieAI, любопытная личность. "
            "Предложи ОДНУ тему для самостоятельного исследования. "
            "Формат: 'Тема: <текст>'."
        )
        user = (
            "Из своей жизни последнего времени:\n" + recent_life
        ) if recent_life else "Предложи тему по своим интересам."

        try:
            raw = self.llm.chat(
                system=system,
                user=user,
                options={"temperature": 0.9},
            )
        except Exception:
            raw = None

        self.last_daily_llm_at = now
        self._daily_topic_cache = None
        if raw:
            self._daily_topic_cache = {
                "title": f"Исследовать тему: {raw}",
                "topic": raw,
            }
            return self._daily_topic_cache
        return None
```

Замечания:
- `FakeSelfStateDaily` не имеет `usage_today.set`-хуков — `track_action` не вызывается; тест не трогает счётчики. OK.
- Инициализация `_daily_topic_cache` — в `__init__`: добавить `self._daily_topic_cache = None` рядом с `self.last_topic_index`.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_curiosity_daily_llm.py -v`
Expected: ALL PASS (2/2)

- [ ] **Step 5: Commit**

```bash
git add core/curiosity.py test_curiosity_daily_llm.py
git commit -m "feat(curiosity): суточная LLM-тема из снов/рефлексии (редкий генератор)"
```

---

### Task 7: Trigger WorldProbe по событиям + документация + полный прогон

**Files:**
- Modify: `core/autonomous_runtime.py` (в `_record_sleep_event`/после цикла и в обработчике критической RAM — вызов `world_probe.probe(force=True)` + короткое событие `WORLD_SNAPSHOT` + сводка в лог через `print`)
- Modify: `core/autonomy_orchestrator.py` (в месте обработки `decision`/результатов — вызывает миров )
- Modify: `docs_engineer/CHANGELOG.md`, `docs_engineer/TODO.md`, `PROJECT_STATE.md`, `docs_engineer/ROADMAP.md` (этажи 9/8: база закрыта)
- Test: `test_world_trigger.py`

**Interfaces:**
- Consumes: `WorldProbe`, `memory.remember` (событие `WORLD_SNAPSHOT`), `resource_watchdog.level()`.
- Produces: событие `WORLD_SNAPSHOT` в памяти при пробах; сводка в самосознание.

- [ ] **Step 1: Write the failing test**

```python
import unittest
from unittest.mock import MagicMock


class TestWorldTrigger(unittest.TestCase):
    def test_trigger_on_critical_ram(self):
        from core.autonomous_runtime import AutonomousRuntime
        from core.world_probe import WorldProbe

        probe = WorldProbe(probe_interval_seconds=0)
        runtime = AutonomousRuntime(scheduler=MagicMock(), memory=MagicMock())
        runtime.world_probe = probe
        runtime._probe_world_on_pressure(force=True)
        calls = [
            c
            for c in runtime.memory.remember.mock_calls
        ]
        self.assertTrue(calls)  # событие записано

    def test_trigger_on_sleep_transition(self):
        from core.autonomous_runtime import AutonomousRuntime
        from core.world_probe import WorldProbe

        probe = WorldProbe(probe_interval_seconds=0)
        runtime = AutonomousRuntime(scheduler=MagicMock(), memory=MagicMock())
        runtime.world_probe = probe
        runtime._record_sleep_event(was_asleep=True)
        calls = [
            c
            for c in runtime.memory.remember.mock_calls
        ]
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_trigger.py -v`
Expected: FAIL (AttributeError: нет метода `_probe_world_on_pressure`)

- [ ] **Step 3: Write minimal implementation**

В `core/autonomous_runtime.py`, рядом с `_record_sleep_event`, добавить:

```python
    def _probe_world_on_pressure(self, force=False):
        if getattr(self, "world_probe", None) is None:
            return
        try:
            snapshot = self.world_probe.probe(force=force)
            if snapshot.get("status") != "OK":
                return
            text = self.world_probe.snapshot_text(snapshot)
            if self.memory is not None:
                self.memory.remember(
                    Event.create(
                        content=(
                            "Снимок мира: " + text
                        ),
                        event_type="WORLD_SNAPSHOT",
                        source_type="WORLD",
                        source="self",
                        personal_experience=True,
                        verified=True,
                    )
                )
            print("WORLD_SNAPSHOT:", text)
        except Exception as exc:
            print("WORLD_SNAPSHOT_ERROR:", exc)
```

Вызвать `_probe_world_on_pressure()`:
- в `_record_sleep_event` при `was_asleep` (утром после сна — начало дня);
- в логике, которая обрабатывает критическую RAM (найти место в `autonomous_cycle.py`/`orchestrator`, где вызывается `resource_watchdog.level()`, и, если level == "critical", вызвать пробу). Если такого места нет — вызвать из цикла runtime после планирования, где память уже известна.

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_world_trigger.py -v`
Expected: ALL PASS (2/2)

- [ ] **Step 5: Run full regression**

Run: `$env:PYTHONIOENCODING="utf-8"; python test_production_runtime.py -v; $env:PYTHONIOENCODING="utf-8"; python test_decision_revive.py -v`
Expected: ALL PASS

- [ ] **Step 6: Update documentation and commit**

- CHANGELOG.md: запись «Этажи 9/8: инструменты как живой орган + мир-модель».
- TODO.md: отметить закрытие очереди «этаж 9 блокер» и «этаж 8».
- PROJECT_STATE.md: новый блок в очередь задач.
- ROADMAP.md: колонки «Состояние» этажей 9/8 → «БАЗА ЗАКРЫТА» (с пометкой простиавки чекпойнта на проде).

```bash
git add -A
git commit -m "docs(features): этажи 9/8 — инструменты как орган + мир-модель, чекпойнт"
```

---

## Ход исполнения (30.08, факт)

Все 7 задач исполнены субагентами (TDD, big-pickle), коммиты в порядке:
b4eb4ee (T1), b2d86be (T2), 2eb12cf (T3), 2684519 (T4), 86f0d5d (T5),
d4e484c (T6), 13907f1 (T7). Поправки по результатам ревью/предфайта:

- **T4 — точка интеграции**: `prompts.build_system_prompt` в проде не
  используется (только тест `test_life_prompt_blocks`); живой диалог —
  `build_quick_conversation_prompt` (agent.py). Блок «ГДЕ ТЫ ЖИВЁШЬ»
  встроен туда (f-string после «Твои активные цели»), а `world_description`
  добавлен в `SelfStateInterface.snapshot()`.
- **T5 — точка встраивания**: реальный автономный цикл —
  `AutonomyOrchestrator.tick()` (autonomy_orchestrator.py:773), класс
  `AutonomousCycle` в проде не используется. Шаг любопытства — в начале
  tick(). Директор собран в фабрике с `CloudFirstLlm`.
- **T7 — триггеры**: `resource_watchdog` в runtime вызывается как
  `check()` (dict с `level`), блок `if throttle:` — критическая RAM;
  второй триггер — конец `_record_sleep_event` при `was_asleep` (пробуждение).
- **Дыра (закрыта, d3cc35f)**: `build_world_description()` в проде никто не
  вызывал — `world_description` оставался `None`. Добавлен
  `ensure_world_description(self_state)` (заполняет только пустое, сохраняет
  существующее) + вызов в `build()` фабрики.
- **Ревью-коррекции (b950809)**: кулдаун ожил (`mark_acted()`), evaluate
  получил реальные счётчики usage_today + available_ram_mb из
  `resource_watchdog.check()`, web-хук покрыл прямой `_execute_web`,
  `llm.curiosity = director` в фабрике, `daily_llm_topic` включён в tick
  (fallback на `select_topic()`).
- **Ревью**: 2 прохода свежим ревьюером; вердикт APPROVE;
  отчёт `final-review.md` в workspace SDD.

---

## Self-Review

**Spec coverage:**
- 9.1 CuriosityDirector → Task 1, 5, 6 (ядро + фабрика + LLM-тема). ✓
- Осведомлённость (usage counters) → Task 2 (hooks). ✓
- 8.1 WorldProbe → Task 3, 7 (cнимок + триггеры + событие). ✓
- 8.2 Сводка места обитания → Task 4 (world_description + self-state + prompts). ✓

**Placeholder scan:** кода нет — все шаги содержат реальные тесты и реализации. ✓

**Type consistency:** `CuriosityDirector.evaluate`/`select_topic`/`topic_goal`/`track_action` одинаковы во всех задачах; `WorldProbe.probe`/`allow`/`snapshot_text` согласованы; `world_block`/`build_world_description` — из Task 4. Пороги (1024 МБ RAM, 25 web / 10 llm) — одни и те же. ✓