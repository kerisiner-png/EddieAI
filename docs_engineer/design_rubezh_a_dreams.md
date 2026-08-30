# Дизайн рубежа A «Душа впитывает» — СНЫ (С1–С4)

Дата: 29.08.2026. Статус: ЗАКРЫТ (С1–С4 реализованы TDD 29.08; приёмка
в бою 30.08 — все 4 критерия подтверждены артефактами сна 29.08 23:45;
см. CHANGELOG 30.08 и TODO «Рубеж A — ЗАКРЫТ»).
Автор: главный инженер (opencode / big-pickle). Основание: TODO.md
«МЕХАНИЗМ СНОВ (утверждено Эдди 25.08 ночь)» + решения Эдди 29.08:
осмысление снов — облачный flash; объём — весь каскад С1–С4; частота —
один сон на входе в SLEEP.

## Цель и критерий

Сон — легитимный конвейер «жатка дня → ассоциативное сновидение →
эмоции и записи → diff души». Рубеж A считается пройденным, когда (все
пункты):

1. Ночь, в памяти которой был эмоционально сильный день (кризис/успех),
   оставляет ненулевой `diff` души (счётчики и/или поля) — сон «двинул
   душу впитыванием».
2. Эмоциональный след сна **не превосходит** след равнозначного
   явного события (страх от сна < страх от яви, сила = вес DREAM 0.25).
3. 0 прямых изменений черт личности от снов (черты — только через
   легитимные proposal-конвейеры низкого давления; в этом рубеже —
   вообще не трогаем).
4. Каждый артефакт сна помечен провенансом `DREAM` / `DREAM_INTERPRETATION`.

## Ограничения и правила безопасности (утверждены 25.08, без изменений)

- source=DREAM обязателен на каждом артефакте сна.
- Вес сна: DREAM = 0.25, DREAM_INTERPRETATION = 0.35 (против 1.0 у яви).
- Черты личности сном напрямую не меняются (никаких прямых set).
- Лимит повторов одного сюжета сна: 3 за ночь (урок токсичной спирали).
- Осмысление снов — облачный zen-deepseek-flash (решение Эдди 29.08):
  локальная модель ночью не грузится (RAM, RAM-guard).
- Сны происходят тихо, без диалога и без автономных действий.
- Сон не обязан использовать мировой движок для осмысления: мировой
  сон (С3) — источник «кадров», опциональный в бою (окружение), всегда
  доступный на полигоне. Фолбэк без мира — внутренняя ассоциативная
  склейка кадров дня.

## Архитектура

```
пробуждение LifeCycle.asleep=False
        ^                       вход в SLEEP (asleep=True)
        |                       │
 утренний ритуал (есть)         вечерний ритуал (есть)
        |                       │
   +___автономный цикл______+   _evening_ritual() → обновляю хук
   |    (мир-тик, LLM)      |   _dream_night() ← НОВЫЙ (С2+С3+С4)
   +------------------------+        │
                                     ▼
                     DreamProcessor.process(now=…)
                     ├─ harvest()      события дня + аффект до сна
                     ├─ replay()       реальные сегменты (честный каркас)
                     ├─ frames()       кадры сна: skew() ИЛИ night() (С3)
                     ├─ dream()        flash → JSON {scene, emotion,
                     │                 intensity, theme}
                     ├─ affect()       apply_reaction(delta=intensity*0.5*W)
                     ├─ record()       Event DREAM + DREAM_INTERPRETATION
                     │                 + PersonalDiary «Сегодня мне снилось…»
                     └─ snapshot()     pre/post души + diff (критерий)
```

Место входа: `AutonomousRuntime.tick()` при переходах SLEEP уже вызывает
`_evening_ritual()`; рядом добавляется `self._dream_night()` (лениво,
через orchestrator.agent). Облачный вызов — ровно один за ночь (~$0.004),
с фолбэком без эмоций при сбое.

## С1. Провенанс DREAM (memory/provenance.py)

- `VALID_SOURCES` += `"DREAM"`, `"DREAM_INTERPRETATION"`.
- `SOURCE_WEIGHTS` += `DREAM: 0.25`, `DREAM_INTERPRETATION: 0.35`.
- Проверка: прогон всего набора существующих вызовов `validate_source`
  и `source_weight` (регрессия по проекту) — ломки нет.
- Тест: `test_provenance_dream.py` (веса, валидация, старые источники).

## С2. Ядро `core/dream_processor.py` (НЕ трогает DecisionRuntime)

Класс `DreamProcessor`, чистая логика, зависимости инъецируются.

Конструктор:
```
DreamProcessor(
    memory=None,            # Memory (жатка, запись)
    self_state=None,        # SelfState (snapshot души, аффект)
    affective_state=None,   # AffectiveState.apply_reaction (писатель)
    diary=None,             # PersonalDiary (или None → пропуск)
    model=None,             # провайдер _cloud_chat (или None → dry)
    night=None,             # callable(segments) -> list[dict] (С3) | None
    rng=None,               # random.Random (детерминизм в тестах)
    max_replay_segments=6,
    max_frames=4,
    plot_repeat_limit=3,
)
```

Пайплайн (методы):

- `harvest(limit=40)`: `memory.recent_life_feed(limit=…)` +
  `memory.recent_action_results(limit=…)`; при отсутствии memory —
  список из переданных сегментов. Результат — список «сегментов дня»
  (словарей: текст, тип, время).
- `replay(segments)`: первые `max_replay_segments` реальных сегментов,
  обезличенные (без персональных данных; тексты усекаются до 300 зн.).
- `skew(replay)`: строит 2–4 ассоциативных кадра: перемешивание
  мест/действующих лиц/тем реальных сегментов; новые факты не
  фабрикуются (только перекомпоновка); повтор сюжета > 3 запрещён.
  Является фолбэком для `frames()`.
- `frames(segments)`: если `night` задан → `night(replay)` (С3-мировой
  сон); иначе `skew(replay)`.
- `dream(frames)`: системный промпт «EddieAI видит сон…», пользователь —
  кадры, жёсткая JSON-схема через контекст (не через валидатор JSON
  только на ответе): пары для flash (task="reflection" — уже роутится
  на flash) или task="deep"? НЕТ: сон НЕ требует жёсткой логики —
  используем стандартный диалоговый конвейер `model._cloud_chat`,
  options: temperature 0.9, num_predict ~500 (простое, то же, что
  ритуалы). Ответ парсится JSON: {"scene": str, "emotion": str,
  "intensity": 0..1, "theme": str}. При ошибке/не-JSON — фолбэк:
  сон = первый кадр, emotion="neutral", intensity=0.1 (сон не падает).
- `affect(dream)`: дельта эмоций из сна: известно правило: интенсивность
  сна применяется с весом DREAM (0.25) и доп. демпфером 0.5 (итог
  ~×0.125 от интенсивности). `apply_reaction(
    changes={emotion: delta}, trigger="dream", reason=…, source="DREAM",
    metadata={"scene":…})`. Эмоция-имя из сна должно принадлежать
  `DEFAULT_EMOTIONS`, иначе нейтральный фолбэк.
- `record(dream, frames)`: `memory.remember(Event.create(
    content=f"Мне снилось: {scene}…", event_type="DREAM",
    source_type="DREAM", source="self", personal_experience=True,
    confidence=0.25, interpretation=…, verified=False))` +
    вторая запись интерпретации `DREAM_INTERPRETATION` (вес 0.35) +
    `diary.write("Сегодня мне снилось: …", trigger="dream")`.
- `snapshot()`: вызов `soul_snapshot.take_snapshot("dream_before")` до
  и `("dream_after")` после + `soul_snapshot.diff` — возвращается в
  результат `process()`. Файловый доступ обёрнут в try (без снов —
  хуже нет, снимок опционален вне производительности).
- `run()` / `process(now=None)`: единый публичный метод: harvest →
  replay → frames → dream → affect → record → snapshot; возвращает
  `{"status": "dreamed"|"empty"|"dry", "scene":…, "emotion":…,
   "diff": …, "frames": n, "events": [ids]}`. При пустой жате —
  `status="empty"` и запись «сон без сюжета» не делается (сон может
  быть «тихим»: сон без кадров → не пишем DREAM, только дневник если есть).

Тесты: `test_dream_processor.py` (ТДД):
- пустая жатва → status empty, 0 записей;
- реплей ≥ кадры: модель-заглушка (FakeDream: returns dict) → пишет
  DREAM-событие с источником и весом; apply_reaction вызвана с демпфером;
- не-JSON/сбой модели → фолбэк без эмоций, но DREAM-запись остаётся
  (сон не падает);
- эмоция не из списка → нейтральный фолбэк;
- limit повторных сюжетов = 3;
- детерминизм с фиксированным rng.

## С3. Мировой сон `simulation_framework/dream_night.py`

Сольный модуль (своеобразный «генератор кадров сна»):
- Вход: `segments` (реплей реального дня из С2) — список словарей.
- Построение: из элементов реальных дней (места, люди, занятия)
  собирается ассоциативный микромир: 2–4 коротких «эпизода» сна,
  хронология ускорена (10–30 вирт.-минут), LLM не используется.
- Выход: список кадров `[{scene}, …]`, каждый с полем `source="DREAM"`,
  `confidence=0.25` и отметкой `dream=True` — примета для bridge.
- Режимы использования:
  a) внутри DreamProcessor через `night=` (полигон/демо);
  b) автономный прогон-скрипт: `python dream_night.py --day-events ev.json
     --out dream.json` с наглядным журналом (используется как источник
     для полномасштабных «мировых снов» в будущих прогонах).
- Лёгкий: не требует SimulationRuntime и не поднимает LLM/тяжёлых
  процессов. Там, где может быть использован SimulationRuntime для
  полного мира — это отдельный future-шаг вне этого рубежа (не блокирует
  критерий: сон есть и без движка, как заложено в С2).

Итог С3: существует рабочий генератор «мировых кадров сна», совместимый
с С2 по контракту и весам. Код живёт в simulation_framework.

## С4. Интеграция в суточный цикл (core/autonomous_runtime.py)

1. В `_evening_ritual()` (вызывается при переходе awake→asleep) после
   существующих действий — вызов `self._dream_night()`:
   `DreamProcessor(...)` из runtime-компонентов (через
   `self.orchestrator.agent`: `memory`, `self_state`, `affective_state`,
   `model_orchestrator`; diary = PersonalDiary(db_path=memory.db_path) —
   глядя на `_remember_ritual_entry`, там уже такой паттерн); модель —
   `self._model_for_ritual()`.
   Вся обработка обёрнута try/except: сон не должен ломать переход сна.
2. Утренний отчёт: *не меняется* — утром `_morning_ritual` уже тянет
   `recent_life_feed` и дневник; запись сна (DREAM-события + дневник)
   попадает в корм утреннего ритуала (утренний LLM-ритуал видит его
   через recent_life_feed и дневник). Дополнительно ничего не нужно.
3. Снимки души под сон: pre = inside `_dream_night` берёт
   `soul_snapshot.take_snapshot("dream_before")` (делается при входе
   в сон), post — сразу после обработки. Отчёт сна содержит diff.
4. Защита от повторов: сон обрабатывается **один раз за фазу SLEEP**
   (однократный вызов при переходе; при пробуждении/засыпании повтор не
   запускается, так как `_evening_ritual` вызывается только при смене
   фазы).

Тест: `test_dream_runtime_hook.py`: FakeLifeCycle переход awake→asleep →
проверяется, что хук `_dream_night` вызван ровно один раз; без model
(dry) — тихий выход; с «FakeDream» — событие DREAM записано. Использую
существующие тест-фикстуры (test_life_rituals.py) как образец.

## Реализация (очередность, TDD)

1. С1: test_provenance_dream.py → provenance.py (RED→GREEN).
2. С2: test_dream_processor.py → core/dream_processor.py (RED→GREEN).
3. С3: dream_night.py + самотест-прогон (детерминированные выходные
   кадры; байт-проверка UTF-8).
4. С4: test_dream_runtime_hook.py → правки autonomous_runtime.py
   (RED→GREEN).
5. Регрессия: test_life_rituals, test_life_cycle, test_life_feed_block,
   test_life_prompt_blocks, test_action_results_block, test_semantic_judge
   (+life_context), test_semantic_judge_life_context, test_model_router_reflection,
   test_production_runtime init (healthcheck), py_compile по затронутым.
6. Энд-ту-энд проверка пайплайна на реальной памяти (sandbox-копия или
   в памяти c FakeMemory): сон из реальной жаты → события/дневник.
7. Документация: CHANGELOG (раздел 29/30.08), TODO (С1–С4 статусы),
   MEMORY (уроки), PROJECT_STATE (рубеж A, реестр).

## Риски и предусмотренные защиты

- Сбой flash (не-JSON/обрыв) → фолбэк-сон без эмоций; сон не роняет
  ночной цикл.
- Рост RAM: сны лёгкие (только вызов API + SQLite); SimulationRuntime
  не поднимается в бою (С3 — отдельный прогон/полигон).
- Повтор сюжета ночами: лимит 3 + детерминизм rng в тестах.
- Совместимость: DecisionRuntime не трогаем; провенанс расширяем
  аддитивно (обратная совместимость существующих источников).
- Критерий измеряется: ночь с эмоционально ярким днём → diff ≠ пуст;
  численно в отчёте сна (файл/печать при прогоне).

## Открытые мелочи (решаются при реализации)

- Эмоция сна и её имя: берём из flash, сверяя с DEFAULT_EMOTIONS;
  маппинг «интенсивность → дельта» фиксируется в коде константой
  DREAM_EMOTION_GAIN = 0.5 (демпфер) * 0.25 (вес сна).
- Тексты сна обезличены (без имён и персональных деталей).

## Критерий приёмки (одна строка из пункта выше)

Ночь с кризисом в памяти → `diff` души ≠ пуст; страх от сна < страха
от яви (вес DREAM); 0 прямых изменений черт; все записи помечены
`DREAM`/`DREAM_INTERPRETATION`.