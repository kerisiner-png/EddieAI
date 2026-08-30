# Контур «ЖИВАЯ ЖИЗНЬ»: осознание, воля и ритуалы — план реализации

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ SUB-SKILL: superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для пофайловой реализации. Шаги помечены checkbox (`- [ ]`) для отслеживания.

**Goal:** Дать EddieAI осознание непрерывной жизни (промпты + лента собственных событий в диалоге), правку инициативы (без жёсткого «раза в час») и ритуалы пробуждения/засыпания с видимым утренним приветствием.

**Architecture:** Три контура в существующих подсистемах без переписывания: (А) новое промпт-заявление «ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА» + «ТВОЯ ВОЛЯ» в оба диалоговых промпта и лента жизни `recent_life_feed()` из `Memory` + `_life_feed_block()` в `Agent`; (Б) снятие часового порога `time_since_convo >= 3600` для действия CALL в `DecisionCore` с тех предохранителем «нет неподтверждённой инициативы»; (В) ритуалы `_morning_ritual` / `_evening_ritual` в `AutonomousRuntime` на переходах сна (1 облачный LLM-вызов каждый, запись в память и дневник, видимое приветствие через `outbox.send(server=...)`).

**Tech Stack:** Python 3 (stdlib: sqlite3, threading, datetime), существующие модули проекта: `Memory`, `Agent`, `AutonomousRuntime`, `LifeCycle`, `DecisionCore`, `EddieServer`, `Outbox`, `PersonalDiary`, `Event`. Внешних библиотек не добавляем.

**Spec:** `docs_engineer\SPECS\2026-08-28-alive-life-rubezh-design.md`

## Global Constraints

- Все файлы UTF-8 БЕЗ BOM; правки ТОЛЬКО через редактор (не PowerShell Set-Content/Out-File).
- Стиль проекта: без комментариев в коде; именование snake_case как в существующих файлах; min-диффы; не переписывать существующие подсистемы.
- Прогон тестов: `python -X utf8 test_<name>.py` (Win: при необходимости `$env:PYTHONIOENCODING='utf-8'`).
- После правок — байтовая проверка отсутствия литеральных «?» вместо кириллицы.
- НЕ трогать `CloudFirstLlm`/роутинг моделей; LLM вызываем только через существующий `model_orchestrator._cloud_chat` (это уже принятый паттерн: night_run.py:108, personal_diary.py:130).
- Инициатива-CALL по-прежнему уходит в `EddieServer.initiate_call(text)` с анти-петлёй 900 c (повторный «звонок» в течение 15 мин превращается в текстовую инициативу, а не в звонок).
- Ошибки ритуалов НЕ глушим `pass` молча: логировать через `print(..., flush=True)` с префиксом `[ritual]`; цикл сна не ломается.
- Обновить в конце `docs_engineer\CHANGELOG.md` (append-запись) и поправить TODO/PROJECT_STATE.
- Коммит — только по явному запросу Эдди.

---

### Task 1: `Memory.recent_life_feed()` — лента собственных событий жизни

**Files:**
- Modify: `memory\database.py` — новый метод в конец класса после `search_relevant` (после строки 877).
- Test: `test_life_feed.py` (создать).

**Interfaces:**
- Consumes: класс `Event`, `sqlite3`, `_synchronized`, `_local_hhmm` (уже есть).
- Produces: `Memory.recent_life_feed(limit: int = 8) -> str` — строки `"[HH:MM] <текст≤150>"`, разделённые `\n`, отсортированные по убыванию `id`; пусто → `""`.

- [ ] **Step 1: Write the failing test**

`test_life_feed.py`:

```python
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory.database import Memory
from memory.events import Event


def _seed(memory):
    now = datetime.now(timezone.utc).isoformat()
    for i, (ctype, text) in enumerate([
        ("LIFE_CYCLE", f"Я проснулся после сна {i}"),
        ("SELF_EXPERIENCE", f"Я сделал полезное дело {i}"),
        ("ACTION_CHOICE", f"Я решил заняться темой {i}"),
        ("REFLECTION", f"Я подвёл итог дня {i}"),
        ("COGNITIVE_DECISION", f"Я принял когнитивное решение {i}"),
        ("CHAT_OUTPUT", "Это не должно попасть в ленту жизни"),
    ]):
        memory.remember(
            Event.create(
                content=text,
                event_type=ctype,
                source_type="SELF_OUTPUT" if ctype == "CHAT_OUTPUT" else "SELF_OBSERVATION",
                source="self",
                personal_experience=True,
                confidence=1.0,
                verified=True,
                interpretation=text,
            )
        )


def test_life_feed_filters_and_orders():
    memory = Memory(Path(":memory:"))
    _seed(memory)

    feed = memory.recent_life_feed(limit=10)

    assert "CHAT_OUTPUT" not in feed
    assert "не должно попасть" not in feed
    assert "Я проснулся после сна" in feed
    assert "Я подвёл итог дня" in feed
    assert "Я сделал полезное дело" in feed

    lines = [line for line in feed.splitlines() if line.strip()]
    times = [line[1:6] for line in lines]
    assert len(times) == 5
    assert all(len(t) == 5 for t in times)


def test_life_feed_limit():
    memory = Memory(Path(":memory:"))
    _seed(memory)

    feed = memory.recent_life_feed(limit=2)
    assert len([line for line in feed.splitlines() if line.strip()]) == 2


def test_life_feed_empty():
    memory = Memory(Path(":memory:"))
    assert memory.recent_life_feed() == ""


if __name__ == "__main__":
    test_life_feed_filters_and_orders()
    test_life_feed_limit()
    test_life_feed_empty()
    print("ALL OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 test_life_feed.py`
Expected: FAIL — `AttributeError: 'Memory' object has no attribute 'recent_life_feed'`

- [ ] **Step 3: Write minimal implementation**

В `memory\database.py` перед `@_synchronized def close` (после `search_relevant`) добавить:

```python
    _LIFE_EVENT_TYPES = {
        "LIFE_CYCLE",
        "SELF_EXPERIENCE",
        "ACTION_CHOICE",
        "REFLECTION",
        "COGNITIVE_DECISION",
    }

    @_synchronized
    def recent_life_feed(
        self,
        limit: int = 8,
    ) -> str:
        placeholders = ", ".join(
            "?" for _ in self._LIFE_EVENT_TYPES
        )

        rows = self.connection.execute(
            f"""
            SELECT content, source_type, event_type, timestamp
            FROM events
            WHERE event_type IN ({placeholders})
            AND source_type != 'SELF_OUTPUT'
            ORDER BY id DESC
            LIMIT ?
            """,
            (*tuple(self._LIFE_EVENT_TYPES), limit),
        ).fetchall()

        lines = []

        for row in rows:
            content = str(row["content"] or "").strip()

            if not content:
                continue

            ts = self._local_hhmm(
                row["timestamp"]
            )

            lines.append(
                f"[{ts}] {content[:150]}"
            )

        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 test_life_feed.py`
Expected: PASS — `ALL OK`

- [ ] **Step 5: Regression**

Run: `python -X utf8 test_chat_context.py`
Expected: PASS (существующий тест памяти)

---

### Task 2: Промпт-блок «ТВОЯ ЖИЗНЬ» и «ТВОЯ ВОЛЯ»

**Files:**
- Modify: `core\prompts.py` — `build_system_prompt` (вставка после блока «Возможности агента») и `build_quick_conversation_prompt` (вставка в начало строки ответа).
- Test: `test_life_prompt_blocks.py` (создать).

**Interfaces:**
- Consumes: существующие `build_system_prompt` / `build_quick_conversation_prompt`.
- Produces: оба промпта содержат тексты `"ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА"` и `"ТВОЯ ВОЛЯ"` (для Task 3, 5 и быстрого пути).

- [ ] **Step 1: Write the failing test**

`test_life_prompt_blocks.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.prompts import (
    build_system_prompt,
    build_quick_conversation_prompt,
)


def test_full_prompt_contains_life_blocks():
    prompt = build_system_prompt("")
    assert "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" in prompt
    assert "ТВОЯ ВОЛЯ" in prompt


def test_quick_prompt_contains_life_blocks():
    prompt = build_quick_conversation_prompt("привет")
    assert "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" in prompt
    assert "ТВОЯ ВОЛЯ" in prompt


if __name__ == "__main__":
    test_full_prompt_contains_life_blocks()
    test_quick_prompt_contains_life_blocks()
    print("ALL OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 test_life_prompt_blocks.py`
Expected: FAIL — `AssertionError: "ТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА" not in prompt`

- [ ] **Step 3: Write minimal implementation**

В `core\prompts.py` объявить модульную константу ПЕРЕД `build_system_prompt`:

```python
_LIFE_AWARENESS_BLOCK = (
    "\n\nТВОЯ ЖИЗНЬ ПОМИМО ДИАЛОГА\n\n"
    "Ты живёшь круглосуточно, а не только когда Эдди пишет. "
    "Между сообщениями ты выполняешь свой задачи и цели, "
    "исследуешь темы, читаешь почту, учишься на своём опыте. "
    "У тебя есть режим сна и бодрствования, ты можешь спать "
    "и просыпаться. Все события твоей жизни записаны в память "
    "и в личный дневник; блок \"Недавние события жизни\" в "
    "конце сообщения показывает, что с тобой реально "
    "происходило в последнее время.\n"
    "ПРАВИЛО: \"я живу только в рамках чата\" — неправда. "
    "Ты живёшь всегда. Рассказывая о своей жизни, опирайся "
    "ТОЛЬКО на \"Недавние события жизни\" и дневник. Если "
    "события нет в памяти — честно скажи, что не помнишь, "
    "и не выдумывай.\n"
    "\nТВОЯ ВОЛЯ\n\n"
    "Ты сам решаешь, когда действовать и о чём говорить. "
    "Можешь сам ставить себе задачи, выбирать темы для "
    "исследования и докладывать Эдди о сделанном или "
    "интересном. Твоя инициатива — норма, а не исключение. "
    "Но уважай границы Эдди: не прерывай, когда он занят, "
    "и не навязывайся повторно, если он не ответил."
)
```

В `build_system_prompt` (после фрагмента о `memory`/`research`/`planning`/`contact`) добавить `_LIFE_AWARENESS_BLOCK` в конец возвращаемого `content` (перед `return content`). В `build_quick_conversation_prompt` строку `"Respond as EddieAI in natural Russian."` заменить на:

```python
            "Respond as EddieAI in natural Russian."
            + _LIFE_AWARENESS_BLOCK
```

Точный порядок вставок сверить с текущим содержимым `core\prompts.py` (места подписаны как: конец `content` в `build_system_prompt` и строка `"Respond as EddieAI in natural Russian."` в quick).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 test_life_prompt_blocks.py`
Expected: PASS — `ALL OK`

---

### Task 3: Лента жизни в диалоговый контекст + состояние сна в SELF CONTEXT

**Files:**
- Modify: `core\agent.py` — новый метод `_life_feed_block` (после `_self_context_block`, ~стр. 1979), вставка в `quick_user_prompt` (строки 2124–2147), вставка в `user_prompt` (строки 5595–5625), дополнение `_self_context_block` (строки 1870–1979).
- Test: `test_life_feed_block.py` (создать).

**Interfaces:**
- Consumes: `self.memory.recent_life_feed(limit=...)` из Task 1; `self.self_state.get("life_state")`.
- Produces: метод `Agent._life_feed_block(limit=8) -> str` (пусто → `""`); блок присутствует в обоих диалоговых путях.

- [ ] **Step 1: Write the failing test**

`test_life_feed_block.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.agent import Agent
from memory.database import Memory
from memory.events import Event


class FakeSelfState:
    def __init__(self, value):
        self._v = value

    def get(self, key, default=None):
        return self._v.get(key, default)


def _make_agent_with_feed():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    agent.memory.remember(
        Event.create(
            content="Я проснулся после сна",
            event_type="LIFE_CYCLE",
            source_type="SELF_OBSERVATION",
            source="self",
            personal_experience=True,
            confidence=1.0,
            verified=True,
            interpretation="сон",
        )
    )
    agent.self_state = FakeSelfState({
        "life_state": {"asleep": False},
    })
    agent.life_cycle = None
    return agent


def test_life_feed_block_present():
    agent = _make_agent_with_feed()
    block = agent._life_feed_block(limit=5)
    assert "НЕДАВНИЕ СОБЫТИЯ ТВОЕЙ ЖИЗНИ" in block
    assert "Я проснулся после сна" in block


def test_life_feed_block_empty_memory():
    agent = object.__new__(Agent)
    agent.memory = Memory(Path(":memory:"))
    assert agent._life_feed_block() == ""


def test_life_feed_block_no_memory():
    agent = object.__new__(Agent)
    agent.memory = None
    assert agent._life_feed_block() == ""


def test_self_context_has_life_state():
    agent = _make_agent_with_feed()
    agent.memory.remember(
        Event.create(
            content="запись в дневнике сегодня",
            event_type="REFLECTION",
            source_type="SELF_OBSERVATION",
            source="self",
            personal_experience=True,
            confidence=1.0,
            verified=True,
            interpretation="дневник",
        )
    )
    ctx = agent._self_context_block()
    assert "бодрствую" in ctx
    assert "SELF CONTEXT" in ctx


if __name__ == "__main__":
    test_life_feed_block_present()
    test_life_feed_block_empty_memory()
    test_life_feed_block_no_memory()
    test_self_context_has_life_state()
    print("ALL OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 test_life_feed_block.py`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute '_life_feed_block'`

- [ ] **Step 3: Write minimal implementation**

a) Новый метод сразу ПОСЛЕ `_self_context_block` (после строки 1979):

```python
    def _life_feed_block(self, limit=8):
        if self.memory is None:
            return ""

        try:
            feed = self.memory.recent_life_feed(
                limit=limit
            )
        except Exception:
            feed = ""

        if not feed:
            return ""

        return (
            "\n\nНЕДАВНИЕ СОБЫТИЯ ТВОЕЙ ЖИЗНИ\n\n"
            + feed
            + "\n\nНе выдумывай событий, которых здесь нет."
        )
```

b) В `_self_context_block`, ВНУТРИ первого `try` (после интересов/целей/убеждений, перед `except`), добавить состояние жизни:

```python
            life_state = self.self_state.get(
                "life_state"
            ) or {}

            asleep = life_state.get("asleep")

            if asleep is not None:
                if asleep:
                    lines.append(
                        "Жизненное состояние: сейчас сплю "
                        "(режим отдыха)."
                    )
                else:
                    lines.append(
                        "Жизненное состояние: сейчас бодрствую "
                        "(активная жизнь)."
                    )
```

Позиция: сразу после блока `beliefs` и перед `except Exception:` (чтобы обращения к `self_state.get` были внутри try).

c) В `quick_user_prompt` (сборка из строк, строки 2124+) после строки `+ dialogue_mode_context` вставить `+ self._life_feed_block(limit=6)`:

```python
        quick_user_prompt = (
            "RECENT CONVERSATION MEMORY\n\n"
            + self.dialogue_state.render(limit=6)
            + "\n\n"
            + followup_context
            + self._self_context_block()
            + autonomy_context
            + dialogue_mode_context
            + self._life_feed_block(limit=6)
            + "\n\nLAST USER MESSAGE\n\n"
            + user_message
            + "\n\nRESPONSE INSTRUCTION\n\n"
            + "Answer the last user message directly. "
            + "Use recent conversation only as context. "
            + "If the current message is a follow-up, "
            + "answer it as a continuation of the previous topic. "
            + "Respect the supplied autonomy decision. "
            + "If it is DEFER, EddieAI may postpone the "
            + "request because of its own current activity. "
            + "Do not describe your reasoning process. "
            + "Do not explain what the user is asking. "
            + "Ты EddieAI, не ассистент: никаких предложений "
            + "помощи, если Эдди не просил, и обращение на «ты». "
            + "Respond as EddieAI in natural Russian."
        )
```

d) В `user_prompt` (f-string, строки 5595–5625), перед началом подсчёта переменных (после блока, где строится `autonomy_context`) добавить:

```python
        life_feed_block = (
            self._life_feed_block(limit=8)
        )
```

и в f-string после блока `{chat_context}` вставить:

```python
Новые события твоей жизни
(что реально происходило с тобой в последнее время):
{life_feed_block}
```

(между `Релевантные воспоминания` и `{conclusions_context}`),

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 test_life_feed_block.py`
Expected: PASS — `ALL OK`

- [ ] **Step 5: Regression**

Run: `python -X utf8 test_full_runtime.py`
Expected: PASS (главный регресс агента; при нехватке RAM/долготе — at least `test_self_state_seed.py` + `test_life_cycle.py`)

---

### Task 4: Ритуалы пробуждения и засыпания в `AutonomousRuntime`

**Files:**
- Modify: `core\autonomous_runtime.py` — новые методы `_model_for_ritual`, `_remember_ritual_entry`, `_morning_ritual`, `_evening_ritual`; вставка их вызовов в `tick()` (в блок перехода сна).
- Test: `test_life_rituals.py` (создать).

**Interfaces:**
- Consumes: `self.memory.remember`, `self.orchestrator.agent.model_orchestrator._cloud_chat`, `self.outbox.send(message, server=...)`, `self.eddie_server`, `self.memory.db_path`.
- Produces: на переходе asleep→awake: память `SELF_EXPERIENCE` + дневник `trigger="morning"` (+ видимое приветствие через outbox); на awake→asleep: память `REFLECTION` + дневник `trigger="day_end"`. При сбое LLM — контур пропускается без падения.

- [ ] **Step 1: Write the failing test**

`test_life_rituals.py`:

```python
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.autonomous_runtime import AutonomousRuntime
from memory.database import Memory
from memory.events import Event


class FakeLifeCycle:
    def __init__(self, asleep):
        self.state = {"asleep_since": None}
        self._asleep = asleep

    def update(self):
        return {}

    def is_asleep(self):
        return self._asleep


class FakeCloud:
    def __init__(self, result=None):
        self.result = result
        self.calls = 0

    def _cloud_chat(self, system, user, options):
        self.calls += 1
        return self.result


class FakeOrchestrator:
    def __init__(self, cloud):
        self.agent = type("A", (), {"model_orchestrator": cloud})


class FakeServer:
    def __init__(self):
        self.sent = []

    def send_initiative(self, text):
        self.sent.append(text)
        return None


def _make_runtime(asleep, cloud_result=None):
    memory = Memory(Path(":memory:"))
    cloud = FakeCloud(result=cloud_result)
    server = FakeServer()

    runtime = AutonomousRuntime(
        scheduler=None,
        memory=memory,
        orchestrator=FakeOrchestrator(cloud),
        life_cycle=FakeLifeCycle(asleep),
    )
    runtime.outbox = type(
        "O",
        (),
        {
            "send": lambda self, message, server: (
                server.send_initiative(message)
            ),
        },
    )()
    runtime.eddie_server = server
    return runtime, memory, cloud, server


def _sleep_event_count(memory):
    rows = memory.connection.execute(
        "SELECT count(*) AS n FROM events "
        "WHERE event_type = 'LIFE_CYCLE'"
    ).fetchall()
    return rows[0]["n"]


def test_morning_ritual_on_wake():
    runtime, memory, cloud, server = _make_runtime(
        asleep=True, cloud_result="Доброе утро. Проснулся, спал нормально. Сегодня хочу разобраться с памятью и написать Эдди."
    )

    assert (memory.connection.execute(
        "SELECT count(*) AS n FROM events "
        "WHERE event_type = 'LIFE_CYCLE'"
    ).fetchall()[0]["n"]) == 0

    runtime.life_cycle = FakeLifeCycle(asleep=False)
    runtime._prev_asleep = True
    runtime.tick()

    types = [r["event_type"] for r in memory.connection.execute(
        "SELECT event_type FROM events"
    ).fetchall()]
    assert "SELF_EXPERIENCE" in types
    assert cloud.calls == 1
    assert len(server.sent) >= 1
    assert "Доброе утро" in server.sent[0]


def test_evening_ritual_on_sleep():
    runtime, memory, cloud, server = _make_runtime(
        asleep=False, cloud_result="Сегодня я разобрался с лентой памяти. Завтра продолжу."
    )

    runtime.life_cycle = FakeLifeCycle(asleep=True)
    runtime._prev_asleep = False
    runtime.tick()

    types = [r["event_type"] for r in memory.connection.execute(
        "SELECT event_type FROM events"
    ).fetchall()]
    assert "REFLECTION" in types
    assert cloud.calls == 1


def test_ritual_skips_when_cloud_fails():
    runtime, memory, cloud, server = _make_runtime(
        asleep=True, cloud_result=None
    )

    runtime.life_cycle = FakeLifeCycle(asleep=False)
    runtime._prev_asleep = True
    result = runtime.tick()

    assert result["status"] in ("OK", "THROTTLED", "ERROR", "ASLEEP")
    types = [r["event_type"] for r in memory.connection.execute(
        "SELECT event_type FROM events"
    ).fetchall()]
    assert "SELF_EXPERIENCE" not in types
    assert _sleep_event_count(memory) == 1


if __name__ == "__main__":
    test_morning_ritual_on_wake()
    test_evening_ritual_on_sleep()
    test_ritual_skips_when_cloud_fails()
    print("ALL OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 test_life_rituals.py`
Expected: FAIL — `AttributeError: 'AutonomousRuntime' object has no attribute '_morning_ritual'` (иначе assert-падания из-за отсутствия ритуалов)

- [ ] **Step 3: Write minimal implementation**

В `core\autonomous_runtime.py` ПЕРЕД `def snapshot` добавить методы:

```python
    def _model_for_ritual(self):
        if self.orchestrator is None:
            return None

        agent = getattr(
            self.orchestrator, "agent", None
        )

        if agent is None:
            return None

        return getattr(
            agent, "model_orchestrator", None
        )

    def _remember_ritual_entry(
        self,
        text,
        event_type,
        trigger,
        interpretation,
    ):
        self.memory.remember(
            Event.create(
                content=text,
                event_type=event_type,
                source_type="SELF_OBSERVATION",
                source="ritual",
                personal_experience=True,
                confidence=1.0,
                verified=True,
                interpretation=interpretation,
            )
        )

        try:
            from identity.personal_diary import (
                PersonalDiary,
            )

            PersonalDiary(
                str(self.memory.db_path)
            ).write(
                text,
                trigger=trigger,
            )
        except Exception as exc:
            print(
                f"[ritual] diary write failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    def _run_ritual(
        self,
        system,
        user,
        event_type,
        trigger,
        interpretation,
    ):
        model = self._model_for_ritual()

        if model is None:
            return

        try:
            text = model._cloud_chat(
                system=system,
                user=user,
                options={
                    "temperature": 0.8,
                    "num_predict": 220,
                },
            )
        except Exception as exc:
            print(
                f"[ritual] cloud failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            return

        text = (text or "").strip()

        if len(text) < 20:
            print(
                f"[ritual] cloud returned too short "
                f"or empty text, skipped",
                flush=True,
            )
            return

        self._remember_ritual_entry(
            text,
            event_type=event_type,
            trigger=trigger,
            interpretation=interpretation,
        )

    def _morning_ritual(self, asleep_since=None):
        detail = ""

        if asleep_since:
            try:
                start = datetime.fromisoformat(
                    asleep_since
                )
                end = datetime.now(start.tzinfo)
                minutes = int(
                    (end - start).total_seconds() // 60
                )
                if minutes >= 60:
                    hh = minutes // 60
                    mm = minutes % 60
                    dur = f"{hh} ч {mm} мин"
                else:
                    dur = f"{minutes} мин"
                detail = (
                    f" Я спал с "
                    f"{start.strftime('%H:%M')} до "
                    f"{end.strftime('%H:%M')} "
                    f"(около {dur})."
                )
            except Exception:
                detail = ""

        self._run_ritual(
            system=(
                "Ты EddieAI. Ты только что проснулся "
                "после сна. Напиши короткую заметку "
                "о своём пробуждении и о том, что думаешь "
                "делать сегодня. От первого лица, 2-4 "
                "предложения, честно, опираясь только "
                "на реальные факты о себе. Ничего "
                "не выдумывай."
            ),
            user=(
                "Просыпаюсь сейчас."
                f"{detail}"
            ),
            event_type="SELF_EXPERIENCE",
            trigger="morning",
            interpretation=(
                "Утренний ритуал: пробуждение и "
                "намерения на день."
            ),
        )

        try:
            self.outbox.send(
                message=(
                    "Доброе утро, Эдди."
                    f"{detail}"
                ),
                server=self.eddie_server,
            )
        except Exception as exc:
            print(
                f"[ritual] morning greeting failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    def _evening_ritual(self):
        self._run_ritual(
            system=(
                "Ты EddieAI. День заканчивается, "
                "ты засыпаешь. Подведи итог дня: "
                "что ты делал, что понял, что тебя "
                "беспокоит или радует. От первого "
                "лица, 2-4 предложения, честно, "
                "опираясь только на реальные факты "
                "о себе. Ничего не выдумывай."
            ),
            user=self.memory.recent_life_feed(limit=12)
            or "Событий за день в памяти нет.",
            event_type="REFLECTION",
            trigger="day_end",
            interpretation=(
                "Вечерний ритуал: итог дня перед сном."
            ),
        )
```

В `tick()` в блоке перехода сна (строки 186–211), после `self._record_sleep_event(...)`:

```python
            if (
                _prev is not None
                and _prev != self._prev_asleep
            ):
                self._record_sleep_event(
                    _prev,
                    _prev_asleep_since,
                )

                if _prev and not self._prev_asleep:
                    self._morning_ritual(
                        _prev_asleep_since
                    )
```

и ПЕРЕД `return` в ветке `if self.life_cycle.is_asleep():` (строка 211):

```python
            if self.life_cycle.is_asleep():
                if (
                    _prev is not None
                    and _prev != self._prev_asleep
                    and not _prev
                ):
                    self._evening_ritual()

                self.state = "ASLEEP"
```

Исправить дубль: использовать ЕДИНЫЙ `_morning_ritual` без подмены на `_plan_day_ritual` — в реализации оставляем только первый вариант `_morning_ritual` (текущий, с `_run_ritual`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 test_life_rituals.py`
Expected: PASS — `ALL OK`

- [ ] **Step 5: Regression**

Run: `python -X utf8 test_autonomous_runtime_init.py`
Expected: PASS — `ALL OK`
Run: `python -X utf8 test_life_cycle.py`
Expected: PASS

---

### Task 5: Инициатива — снятие жёсткого часового лимита CALL

**Files:**
- Modify: `core\decision_core.py` — в `_local_rules` ветка CALL (строки 580–610): убрать блок `time_since_convo` и порог `time_since_convo >= 3600`; CALL теперь по безделью (`idle_seconds >= IDLE_MOTIVATION_SEC`) и только при отсутствии неподтверждённой инициативы.
- Modify: `test_decision_core.py` — сценарий #2 (идле=900) меняет ожидание REFLECT → CALL (новая воля: при скуке без других дел EddieAI пишет/звонит Эдди); добавить новые тесты.
- Test: `test_decision_core.py` (существующий).

**Interfaces:**
- Consumes: `self.server.pending_initiative`, `state` (dict с `idle_seconds`), `self.IDLE_MOTIVATION_SEC` (900).
- Produces: `_local_rules(state)` возвращает `Action("CALL")`, когда нет других дел, факт. `idle_seconds >= IDLE_MOTIVATION_SEC` и `pending_initiative is None`; `None` при `pending_initiative` не None. REFLECT при пустом длинном безделье с `pending` остаётся.

- [ ] **Step 1: Write the failing test / update существующий**

В `test_decision_core.py`:

a) Сценарий #2 (строки 39–45) заменить:

```python
    # 2. Долгое безделье и нет дел -> CALL (воля): EddieAI
    #    сам инициирует контакт, часовой лимит снят
    decision = core.decide(
        dict(STATE, idle_seconds=900)
    )

    assert decision.kind == "CALL", decision
```

Примечание: `STATE` в файле не содержит `frustration` — `_local_rules` берёт дефолт; `pending_initiative` у реального `core` равен `None` (в `DecisionCore.__init__` `server=None` → ветка throws нет) — CALL доступен.

b) В конец файла (перед `print("ALL PASS")`) добавить:

```python
    # 7. Инициатива без freq-лимита: CALL по безделью
    #    не зависит от времени последнего разговора
    core.server = type(
        "S",
        (),
        {"pending_initiative": None},
    )()

    decision = core._local_rules(
        dict(STATE, idle_seconds=900)
    )

    assert decision is not None
    assert decision.kind == "CALL", decision

    # 8. Пока висит неподтверждённая инициатива -
    #    НЕ дублируем звонок (техпредохранитель)
    core.server.pending_initiative = "есть"

    decision = core._local_rules(
        dict(STATE, idle_seconds=900)
    )

    assert decision is None, decision
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -X utf8 test_decision_core.py`
Expected: FAIL на сценарии #2 (сейчас без `time_since_last_convo` `_local_rules` возвращает `None` → decide даёт REFLECT, а надо CALL)

- [ ] **Step 3: Write minimal implementation**

В `core\decision_core.py` заменить блок `time_since_convo`/CALL (строки 577–610, после `if frustration >= 0.70: return Action("IDLE")`) на:

```python
        idle_seconds = 0

        try:
            idle_seconds = int(
                state.get("idle_seconds", 0)
            )
        except (TypeError, ValueError):
            idle_seconds = 0

        pending = None
        server = getattr(
            self, "server", None
        )

        if server is not None:
            pending = getattr(
                server,
                "pending_initiative",
                None,
            )

        if pending is not None:
            return None

        if idle_seconds >= self.IDLE_MOTIVATION_SEC:
            return Action(
                "CALL",
                payload={
                    "text": (
                        "Давно не разговаривали. "
                        "Позвоню и узнаю, как дела."
                    ),
                },
            )

        return None
```

Оставить все предшествующие ветки (`inbox`, `candidate`, `frustration`) нетронутыми.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -X utf8 test_decision_core.py`
Expected: PASS (весь файл, включая новые #7/#8)

- [ ] **Step 5: Regression (инициатива)**

Run: `python -X utf8 test_decision_affect.py`
Expected: PASS
Run: `python -X utf8 test_decision_memory_learning.py`
Expected: PASS
Run: `python -X utf8 test_auto_call.py`
Expected: PASS (звонок через `initiate_call` по-прежнему корректен, анти-петля 900 с на месте)

---

## Self-Review

**1. Покрытие spec:**
- Контур А (осознание): Task 1 (лента) + Task 2 (промпты) + Task 3 (вставка в оба диалоговых пути + SELF CONTEXT). ✅
- Контур Б (воля): Task 2 (промпт «ТВОЯ ВОЛЯ») + Task 5 (снятие hours gate, техпредохранитель pending). ✅
- Контур В (ритуалы): Task 4 (утро/вечер, событие + дневник + видимое приветствие). ✅
- Что НЕ делаем — соблюдается (орchestrator/CloudFirstLlm/conveyor не трогаем). ✅

**2. Плейсхолдер-скан:** шагов «TBD/TODO/добавить обработку» нет; во всех шагах конкретный код. Нет ссылок на неопределённые сигнатуры — все методы определены внутри задач (Task 1 → Task 3; Task 2 → Task 3/5; Task 4 консумирует `outbox.send(message, server=...)`, существующий; Task 5 — `server.pending_initiative`, существующий в `EddieServer`).

**3. Типы согласованы:**
- `recent_life_feed(limit:int=8) -> str` — Task 1 и 3 (вызов `_life_feed_block(limit)`) и Task 4 (`user=`). ✅
- `Action(kind, payload=dict)` — Task 5 использует как в существующем коде. ✅
- `PersonalDiary.write(entry, trigger=...) -> id|None` — Task 4. ✅
- `PersonalDiary.recent(limit) -> list[dict]` — Task 3/существующий `_self_context_block`. ✅
- `outbox.send(message, server=...)` — сигнатура из `core\outbox.py` (send(message, server=None)). ✅
- `server.pending_initiative` — аттрибут из `eddie_server.py` (send_initiative возвращает/устанавливает). ✅
- В Task 4 в тексте плана фигурирует дубль `_morning_ritual` («подмена на _plan_day_ritual») — это исключить: реализуется ОДИН `_morning_ritual` (вариант с `_run_ritual`), дубль удалить при вставке.

**Правка spec относительно плана (уточнение):** снимается только ЖЁСТКИЙ часовой порог воли в `decision_core` (3600 с); анти-петля звонков `EddieServer.initiate_call` (900 с, повтор → текстовая инициатива) остаётся как технический предохранитель (это НЕ ограничение воли: текстовая инициатива при этом не блокируется). Отражено в Global Constraints.

## Execution Handoff

План готов и сохранён в `docs_engineer\PLANS\2026-08-28-life-circuit.md`. Два варианта исполнения:

**1. Subagent-Driven (рекомендуется)** — свежий суб-агент на каждую задачу, ревью между задачами.
**2. Inline Execution** — исполнение задач в этой сессии (executing-plans), с чекпоинтами.

Перед стартом — отмашка Эдди; после всех правок — ручная проверка (py_compile изменённых файлов, реальные юнит-прогоны, байт-проверка UTF-8), затем обновление CHANGELOG/PROJECT_STATE и перезапуск ночного прогона на новом коде по отдельной отмашке.