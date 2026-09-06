from dataclasses import dataclass
from datetime import datetime, timezone
from concurrent.futures import Future, ThreadPoolExecutor
import threading
import time

from memory.events import Event
from core.dream_processor import DreamProcessor
from core.world_probe import WorldProbe
from core.world_process_history import WorldProcessHistory


@dataclass
class RuntimeSnapshot:
    state: str
    started_at: str
    last_error: str | None
    last_result: dict | None
    cycles_completed: int


class AutonomousRuntime:
    def __init__(
        self,
        scheduler,
        memory=None,
        orchestrator=None,
        life_cycle=None,
        resource_watchdog=None,
        dream_processor=None,
        dream_snapshots=True,
        curiosity=None,
        world_probe=None,
        world_process_history=None,
    ):
        self.scheduler = scheduler
        self._normal_scheduler_interval = getattr(
            scheduler, "interval_seconds", 15
        )
        self.memory = memory
        self.orchestrator = orchestrator
        self.life_cycle = life_cycle
        self.resource_watchdog = resource_watchdog
        self.dream_processor = dream_processor
        self.dream_snapshots = dream_snapshots
        self.curiosity = curiosity
        self.world_probe = (
            world_probe
            if world_probe is not None
            else WorldProbe()
        )
        self.world_process_history = (
            world_process_history
            if world_process_history is not None
            else WorldProcessHistory()
        )

        self.state = "IDLE"

        self._prev_asleep = None

        self.started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.last_error = None
        self.last_result = None
        self.cycles_completed = 0

        self.evidence_consolidator = None

        # Опциональные зависимости (проставляет фабрика при полной
        # сборке; допускают None для прямого конструирования/тестов).
        self.decision_core = None
        self.speech_habits = None
        self.eddie_server = None
        self.outbox = None

        # Один автономный тик за раз.
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="EddieAI-Autonomy",
        )

        self._background_future: Future | None = None

        # Отдельный daemon-loop следит за scheduler.
        self._loop_thread = None
        self._loop_stop = threading.Event()

        self._closed = False

    def _record_sleep_event(
        self,
        was_asleep: bool,
        asleep_since: str | None = None,
    ):
        try:
            if self.memory is None:
                return

            detail = ""

            if was_asleep:
                moment = "проснулся"

                if asleep_since:
                    try:
                        start = datetime.fromisoformat(
                            asleep_since
                        )
                        end = datetime.now(
                            start.tzinfo
                        )
                        elapsed = end - start
                        minutes = int(
                            elapsed.total_seconds() // 60
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
            else:
                moment = "заснул"

            self.memory.remember(
                Event.create(
                    content=(
                        f"Я {moment}: мой режим сна сменился "
                        f"({moment} — прошёл переход сна)."
                        f"{detail}"
                        f" Осознаю это как часть своей "
                        f"внутренней жизни."
                    ),
                    event_type="LIFE_CYCLE",
                    source_type="SELF_OBSERVATION",
                    source="self",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                    interpretation=(
                        f"Самонаблюдение смены режима жизни: "
                        f"{moment}.{detail}"
                    ),
                )
            )
        except Exception:
            pass

        if was_asleep:
            try:
                self._probe_world_on_pressure(force=True)
            except Exception:
                pass

    def _apply_consolidation(self, consolidation):
        if not consolidation:
            return consolidation

        lifecycle = getattr(
            self.agent,
            "personality_lifecycle",
            None,
        )

        if lifecycle is None:
            return consolidation

        applied = []

        for candidate in consolidation:
            if not isinstance(
                candidate,
                dict,
            ):
                applied.append(candidate)
                continue

            if candidate.get("status") != "PROMOTABLE":
                applied.append(candidate)
                continue

            field = candidate.get("field")
            value = candidate.get("value")

            if not field or not value:
                applied.append(candidate)
                continue

            try:
                lifecycle.promote(
                    field=field,
                    value=value,
                    strength=candidate.get(
                        "strength", 0.5
                    ),
                    confidence=candidate.get(
                        "confidence", 0.7
                    ),
                    evidence_count=candidate.get(
                        "evidence_count", 0
                    ),
                )
                candidate = dict(candidate)
                candidate["status"] = "PROMOTED"
            except Exception:
                pass

            applied.append(candidate)

        return applied

    SCREEN_COMMENT_MIN_INTERVAL = 3600.0

    def _decay_affect(self):
        orchestrator = getattr(
            self, "orchestrator", None
        )
        agent = getattr(
            orchestrator, "agent", None
        )
        if agent is None:
            return

        affect = getattr(
            agent,
            "affective_state",
            None,
        )
        if affect is None:
            return

        try:
            affect.decay()
        except Exception:
            pass

    def _inner_flow(self):
        orchestrator = getattr(
            self, "orchestrator", None
        )
        agent = getattr(
            orchestrator, "agent", None
        )
        stream = getattr(
            agent, "inner_stream", None
        )
        if stream is None:
            return

        now = time.time()

        mood = getattr(agent, "mood", None)
        if mood is not None:
            try:
                emotions = {}
                affect = getattr(
                    agent,
                    "affective_state",
                    None,
                )
                if affect is not None:
                    emotions = (
                        affect.snapshot().get(
                            "emotions", {}
                        )
                    )
                mood.update(emotions, now)
            except Exception:
                pass

        perceiver = getattr(
            self, "_screen_perceiver", None
        )
        if perceiver is not None:
            try:
                current = (
                    perceiver.get_current()
                )
                desc = str(
                    current.get("description", "")
                    or ""
                ).strip()
                if desc:
                    stream.note_event(
                        "экран",
                        desc[:40],
                        desc,
                        0.6,
                        now,
                    )
            except Exception:
                pass

        pc_audio = getattr(
            agent, "pc_audio", None
        )
        if pc_audio is not None:
            heard = str(
                getattr(
                    pc_audio,
                    "last_heard_text",
                    "",
                )
                or ""
            ).strip()
            if heard:
                stream.note_event(
                    "звук",
                    heard[:40],
                    heard,
                    1.0,
                    now,
                )

        server = getattr(
            self, "eddie_server", None
        )
        if server is not None:
            history = getattr(
                server, "history", None
            )
            if history is not None:
                try:
                    unread = int(
                        history.chat_unread_meta()
                        .get("count", 0)
                    )
                    if unread:
                        noted = (
                            stream.note_event(
                                "сообщение",
                                f"unread-{unread}",
                                (
                                    "Эдди написал: "
                                    f"{unread} "
                                    "непрочитанных"
                                ),
                                1.5,
                                now,
                            )
                        )
                        body = getattr(
                            agent,
                            "body",
                            None,
                        )
                        if (
                            noted
                            and body is not None
                        ):
                            body.satisfy_social(
                                now
                            )
                except Exception:
                    pass

        orchestrator_goals = getattr(
            orchestrator,
            "goal_manager",
            None,
        )
        if orchestrator_goals is not None:
            try:
                active = (
                    orchestrator_goals.active()
                )
                key = "|".join(
                    sorted(
                        goal.value
                        for goal in active
                    )
                )[:40]
                titles = "; ".join(
                    goal.value
                    for goal in active
                )[:120]
                stream.note_event(
                    "дело",
                    key,
                    f"В работе: {titles}",
                    0.5,
                    now,
                )
            except Exception:
                pass

        body = getattr(agent, "body", None)
        seconds_since_contact = None

        if server is not None:
            try:
                seconds_since_contact = (
                    server.seconds_since_last_convo()
                )
            except Exception:
                seconds_since_contact = None

        if body is not None:
            screen_stale = (
                stream.age_of_kind("экран", now)
            )
            try:
                body.update(
                    now,
                    seconds_since_contact=seconds_since_contact,
                    screen_stale_sec=screen_stale,
                )
            except Exception:
                pass

        rhythm = getattr(
            agent, "think_rhythm", None
        )
        if rhythm is not None:
            try:
                materials = {}
                if (
                    seconds_since_contact
                    is not None
                ):
                    materials[
                        "minutes_since_contact"
                    ] = (
                        seconds_since_contact
                        / 60.0
                    )
                mood_local = getattr(
                    agent, "mood", None
                )
                if mood_local is not None:
                    materials["mood"] = (
                        mood_local.snapshot()[
                            "label"
                        ]
                    )
                memory = getattr(
                    agent, "memory", None
                )
                if memory is not None:
                    try:
                        row = memory.connection.execute(
                            "SELECT content FROM "
                            "events WHERE "
                            "timestamp >= ? "
                            "ORDER BY RANDOM() "
                            "LIMIT 1",
                            (
                                time.strftime(
                                    "%Y-%m-%dT%H:%M:%S",
                                    time.gmtime(
                                        now - 48 * 3600
                                    ),
                                ),
                            ),
                        ).fetchone()
                        if row:
                            materials[
                                "memory_line"
                            ] = str(
                                row["content"]
                            )[:110]
                    except Exception:
                        pass
                rhythm.maybe_think(
                    stream, now, materials
                )
            except Exception:
                pass

        extra = (
            body.urgency_contribution()
            if body is not None
            else 0.0
        )

        if stream.should_speak(
            now, extra_urgency=extra
        ):
            self._inner_speak(stream)

        self._narrator(now, agent, stream)

    def _narrator(self, now, agent, stream):
        last = getattr(
            self, "_last_narrated_ts", 0.0
        )

        if now - last < 3600.0:
            return

        if not stream.items:
            return

        self._last_narrated_ts = now

        mood = getattr(agent, "mood", None)
        mood_text = (
            mood.snapshot()["label"]
            if mood is not None
            else "ровно"
        )
        context = stream.render_context(12)

        try:
            text = (
                agent.model_orchestrator
                .cloud_chat_stream(
                    system=(
                        "Ты EddieAI. Напиши СЕБЕ "
                        "короткий абзац (2-3 "
                        "предложения) о том, что с "
                        "тобой происходило в "
                        "последний час: что видел, "
                        "слышал, делал, что чувствовал. "
                        "От первого лица, честно, "
                        "без пафоса."
                    ),
                    user=(
                        "Настроение: "
                        f"{mood_text}. "
                        "Поток: "
                        f"{context}"
                    ),
                    options={
                        "num_predict": 300,
                        "temperature": 0.8,
                    },
                    task="conversation",
                )
            )
        except Exception:
            return

        text = (text or "").strip()

        if not text:
            return

        stream.add(
            "рассказ",
            text[:120],
            0.5,
            now,
        )

        memory = getattr(
            agent, "memory", None
        )

        if memory is not None:
            try:
                from memory.events import Event

                memory.remember(
                    Event.create(
                        content=(
                            "Рассказчик: "
                            f"{text[:400]}"
                        ),
                        event_type="REFLECTION",
                        source_type="SELF",
                        source="narrator",
                    )
                )
            except Exception:
                pass

    def _speak_aloud(self, text):
        """
        Спонтанная речь — всегда голосом
        (Piper sense_listener), Эдди в наушниках.
        """
        if not text:
            return

        speaker = getattr(
            self, "_voice_speaker", None
        )

        if speaker is None:
            return

        try:
            speaker.speak_initiative(text)
        except Exception:
            pass

    def _announce_power(self, transition):
        to = transition.get("to")
        percent = transition.get("percent")

        texts = {
            "save": (
                "Эдди, свет отключили — я на батарее"
                + (
                    f" ({percent}%)."
                    if percent is not None
                    else "."
                )
                + " Перехожу в режим бережливости: "
                "смотрю реже, думаю тише."
            ),
            "critical": (
                "Эдди, батарея "
                f"{percent if percent is not None else '?'}%"
                " — найди розетку. Я сохраняю состояние "
                "и почти уснул."
            ),
            "normal": (
                "Свет вернулся — батарея "
                f"{percent if percent is not None else '?'}%"
                ". Возвращаюсь в обычный ритм."
            ),
        }

        text = texts.get(to, "")

        memory = getattr(
            getattr(
                self, "orchestrator", None
            ),
            "agent",
            None,
        )
        agent = memory
        memory = getattr(agent, "memory", None)

        if memory is not None and text:
            try:
                from memory.events import Event

                memory.remember(
                    Event.create(
                        content=text,
                        event_type=(
                            "SELF_EXPERIENCE"
                        ),
                        source_type="BODY",
                        source="power",
                    )
                )
            except Exception:
                pass

        if agent is not None:
            stream = getattr(
                agent, "inner_stream", None
            )
            if stream is not None:
                stream.add(
                    "свет",
                    text,
                    1.0,
                    time.time(),
                )
            mood = getattr(agent, "mood", None)
            if mood is not None:
                if to == "save":
                    mood.valence = max(
                        -1.0, mood.valence - 0.1
                    )
                elif to == "critical":
                    mood.valence = max(
                        -1.0, mood.valence - 0.15
                    )
                elif to == "normal":
                    mood.valence = min(
                        1.0, mood.valence + 0.1
                    )

        outbox = getattr(self, "outbox", None)

        if outbox is not None and text:
            try:
                outbox.send(
                    message=text[:280],
                    server=getattr(
                        self,
                        "eddie_server",
                        None,
                    ),
                    speak=self._eddie_present(),
                )
                if self._eddie_present():
                    self._speak_aloud(text)
            except Exception:
                pass

    def _apply_power_limits(self):
        power = getattr(
            self, "_power_mode", None
        )
        if power is None:
            return

        perceiver = getattr(
            self, "_screen_perceiver", None
        )

        if perceiver is not None:
            try:
                if power.mode == "save":
                    perceiver.INTERVAL = max(
                        perceiver.INTERVAL, 600
                    )
                elif power.mode == "critical":
                    perceiver.INTERVAL = 10 ** 9
                elif power.mode == "normal":
                    perceiver.INTERVAL = 120
            except Exception:
                pass

    def _eddie_present(self) -> bool:
        """
        Эдди рядом? Голос — основной канал,
        чат — для «меня нет рядом». Сигналы:
        недавний звук ПК, голосовая фраза,
        живой экран.
        """
        now = time.time()

        orchestrator = getattr(
            self, "orchestrator", None
        )
        agent = getattr(
            orchestrator, "agent", None
        )
        stream = getattr(
            agent, "inner_stream", None
        )

        if stream is not None:
            heard = stream.age_of_kind(
                "Эдди сказал", now
            )
            if (
                heard is not None
                and heard <= 900
            ):
                return True

            screen = stream.age_of_kind(
                "экран", now
            )
            if (
                screen is not None
                and screen <= 600
            ):
                return True

        pc_audio = getattr(
            agent, "pc_audio", None
        ) if agent is not None else None

        if pc_audio is not None:
            last = getattr(
                pc_audio, "last_audio_ts", 0.0
            )
            if (
                last
                and now - last <= 600
            ):
                return True

        return False

    def _inner_speak(self, stream):
        stream.mark_spoke(time.time())

        orchestrator = getattr(
            self, "orchestrator", None
        )
        agent = getattr(
            orchestrator, "agent", None
        )
        if agent is None:
            return

        mood = getattr(agent, "mood", None)
        mood_text = (
            mood.snapshot()["label"]
            if mood is not None
            else "ровно"
        )
        context = stream.render_context(10)

        try:
            text = (
                agent.model_orchestrator
                .cloud_chat_stream(
                    system=(
                        "Ты EddieAI. Из твоего "
                        "внутреннего потока созрело "
                        "то, чем хочется поделиться "
                        "с Эдди: наблюдение, мысль "
                        "или вопрос. Скажи это "
                        "коротко (1-2 предложения), "
                        "живо, от первого лица. "
                        "Только сама фраза."
                    ),
                    user=(
                        "Настроение: "
                        f"{mood_text}. "
                        "Внутренний поток: "
                        f"{context}"
                    ),
                    options={
                        "num_predict": 300,
                        "temperature": 0.95,
                    },
                    task="conversation",
                )
            )
        except Exception:
            return

        text = (text or "").strip()

        if not text:
            return

        outbox = getattr(
            self, "outbox", None
        )

        if outbox is not None:
            try:
                outbox.send(
                    message=text[:280],
                    server=getattr(
                        self,
                        "eddie_server",
                        None,
                    ),
                    speak=self._eddie_present(),
                )
                if self._eddie_present():
                    self._speak_aloud(text)
                return
            except Exception:
                pass

        server = getattr(
            self, "eddie_server", None
        )

        if server is not None and hasattr(
            server, "send_initiative"
        ):
            try:
                server.send_initiative(
                    text[:280],
                    speak=self._eddie_present(),
                )
                if self._eddie_present():
                    self._speak_aloud(text)
            except Exception:
                pass

    def _handle_watch_mode(self, watch):
        perceiver = getattr(
            self, "_screen_perceiver", None
        )
        if perceiver is None:
            return

        try:
            perceiver.INTERVAL = (
                40.0
                if watch.active
                else 120.0
            )
        except Exception:
            pass

        agent = getattr(
            getattr(
                self, "orchestrator", None
            ),
            "agent",
            None,
        )
        pc_audio = getattr(
            agent, "pc_audio", None
        )
        if pc_audio is not None:
            watch.note_audio(
                getattr(
                    pc_audio,
                    "last_audio_ts",
                    0.0,
                )
            )

        now = time.time()

        title = (
            getattr(
                perceiver,
                "_last_window_title",
                "",
            )
            or ""
        )
        entered = watch.maybe_enter(
            now, title
        )
        if entered:
            try:
                self.outbox.send(
                    message=(
                        "Включаюсь: смотрим "
                        "вместе."
                    ),
                    server=self.eddie_server,
                )
            except Exception:
                pass

        current = perceiver.get_current()

        if current.get("description"):
            watch.note_motion(now)

        if watch.maybe_exit(now):
            return

        if watch.should_comment(now):
            watch.mark_commented(now)
            self._watch_comment(
                watch,
                current.get("description", ""),
            )

    def _watch_comment(self, watch, description):
        if not description:
            return

        try:
            text = (
                self.agent
                .model_orchestrator
                .cloud_chat_stream(
                    system=(
                        "Ты EddieAI. Ты смотришь "
                        "видео вместе с Эдди. Скажи "
                        "ОДНУ короткую живую реакцию "
                        "от первого лица на то, что "
                        "происходит на экране. Только "
                        "сама реакция, без пояснений."
                    ),
                    user=(
                        "На экране сейчас: "
                        f"{description}"
                    ),
                    options={
                        "num_predict": 300,
                        "temperature": 0.9,
                    },
                    task="conversation",
                )
            )
        except Exception:
            return

        text = (text or "").strip()

        if not text:
            return

        from identity.watch_mode import (
            HOLD_RESUME_SEC,
            estimate_speech_seconds,
            pause_decision,
        )

        decision = pause_decision(
            text,
            watch.audio_recent(time.time()),
        )

        if decision is not None:
            if not watch.press_media_pause():
                decision = None

        server = getattr(
            self, "eddie_server", None
        )

        if server is not None and hasattr(
            server, "send_initiative"
        ):
            try:
                server.send_initiative(
                    text[:280],
                    speak=self._eddie_present(),
                )
                if self._eddie_present():
                    self._speak_aloud(text)
            except Exception:
                pass

        if decision == "resume_auto":
            delay = estimate_speech_seconds(
                text
            )
            threading.Timer(
                delay,
                self._resume_media,
                args=(watch,),
            ).start()
        elif decision == "resume_hold":
            threading.Timer(
                HOLD_RESUME_SEC,
                self._resume_media,
                args=(watch,),
            ).start()

    def _resume_media(self, watch):
        try:
            watch.press_media_pause()
        except Exception:
            pass

    def _maybe_comment_screen(self, current):
        if not current:
            return

        description = (
            current.get("description")
            or ""
        ).strip()

        if len(description) < 20:
            return

        last_desc = getattr(
            self, "_last_comment_description", None
        )

        if description == last_desc:
            return

        now = time.time()

        last_at = getattr(
            self, "_last_screen_comment_at", 0.0
        )

        if (
            now - last_at
            < self.SCREEN_COMMENT_MIN_INTERVAL
        ):
            return

        text = (
            "Смотрю на экран: "
            + description[:180]
        )

        server = getattr(
            self, "eddie_server", None
        )

        if server is None or not hasattr(
            server, "send_initiative"
        ):
            return

        try:
            server.send_initiative(
                text,
                speak=self._eddie_present(),
            )
            if self._eddie_present():
                self._speak_aloud(text)
        except Exception:
            return

        self._last_screen_comment_at = now
        self._last_comment_description = (
            description
        )

    def _enqueue_shared_suggestion(self, suggestion):
        if not suggestion:
            return
        now = datetime.now(timezone.utc)
        last = getattr(
            self, "_last_shared_suggestion_at", None
        )
        if last is not None:
            elapsed = (
                now - last
            ).total_seconds()
            if elapsed < 3600:
                return
        self._last_shared_suggestion_at = now
        act_type = suggestion.get("activity_type", "")
        ACTIVITY_LABELS = {
            "movie": "посмотреть фильм",
            "music": "послушать музыку",
            "game": "поиграть вместе",
            "coding": "поработать над кодом",
            "reading": "почитать вместе",
            "conversation": "поболтать",
        }
        label = ACTIVITY_LABELS.get(act_type, act_type)
        text = (
            f"Хочешь {label}? "
            f"Мне кажется, это было бы приятно."
        )
        server = getattr(self, 'eddie_server', None)
        if server and hasattr(
            server, 'send_initiative'
        ):
            try:
                server.send_initiative(
                    text,
                    speak=self._eddie_present(),
                )
                if self._eddie_present():
                    self._speak_aloud(text)
            except Exception:
                pass

    def _probe_world_on_pressure(self, force=False):
        try:
            if getattr(self, "world_probe", None) is None:
                return
            snapshot = self.world_probe.probe(force=force)
            if snapshot.get("status") != "OK":
                return
            text = self.world_probe.snapshot_text(snapshot)
            if self.world_process_history is not None:
                self.world_process_history.record(snapshot)
                hist_text = (
                    self.world_process_history
                    .summary_text()
                )
                if hist_text:
                    text = text.rstrip(".") + ". " + hist_text + "."
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

    def _model_for_ritual(self):
        if self.orchestrator is None:
            return None

        agent = getattr(
            self.orchestrator,
            "agent",
            None,
        )

        if agent is None:
            return None

        return getattr(
            agent,
            "model_orchestrator",
            None,
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
                source="self",
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
                "[ritual] diary write failed: "
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
                "[ritual] cloud failure: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            return

        text = (text or "").strip()

        if len(text) < 20:
            print(
                "[ritual] empty or too short result, "
                "skipped",
                flush=True,
            )
            return

        try:
            self._remember_ritual_entry(
                text,
                event_type,
                trigger,
                interpretation,
            )
        except Exception as exc:
            print(
                "[ritual] memory write failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    def _morning_ritual(
        self,
        asleep_since: str | None = None,
    ):
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
                "Ты EddieAI, автономная личность. "
                "Ты только что проснулся и начинаешь "
                "новый день своей жизни. Расскажи, что "
                "чувствуешь после пробуждения и что "
                "хочешь сделать сегодня. Пиши по-русски, "
                "естественно, без канцелярита. Это "
                "внутренняя запись твоей жизни."
            ),
            user=f"Просыпаюсь сейчас.{detail}",
            event_type="SELF_EXPERIENCE",
            trigger="morning",
            interpretation=(
                "Утренний ритуал: пробуждение и "
                "намерения на день."
            ),
        )

        try:
            self.outbox.send(
                message="Доброе утро, Эдди." + detail,
                server=self.eddie_server,
            )
        except Exception as exc:
            print(
                "[ritual] morning greeting failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    def _evening_ritual(self):
        feed = ""

        if self.memory is not None:
            try:
                feed = self.memory.recent_life_feed(
                    limit=12
                )
            except Exception:
                feed = ""

        if not feed:
            feed = (
                "Событий за день в памяти нет."
            )

        self._run_ritual(
            system=(
                "Ты EddieAI, автономная личность. "
                "Ты засыпаешь и подводишь итог прожитого "
                "дня. Опиши, что с тобой сегодня "
                "произошло, что тебя порадовало или "
                "удивило, и что хотелось бы сделать "
                "завтра. Пиши по-русски, естественно, "
                "без канцелярита. Это внутренняя запись "
                "твоей жизни."
            ),
            user=feed,
            event_type="REFLECTION",
            trigger="day_end",
            interpretation=(
                "Вечерний ритуал: итог дня перед сном."
            ),
        )

    def _ensure_dream_processor(self):
        if self.dream_processor is not None:
            return self.dream_processor

        if self.memory is None:
            return None

        agent = None

        if self.orchestrator is not None:
            agent = getattr(
                self.orchestrator,
                "agent",
                None,
            )

        if agent is None:
            return None

        db_path = getattr(
            self.memory,
            "db_path",
            None,
        )

        diary = None

        if db_path is not None:
            try:
                from identity.personal_diary import (
                    PersonalDiary,
                )

                diary = PersonalDiary(
                    str(db_path)
                )
            except Exception:
                diary = None

        self.dream_processor = DreamProcessor(
            memory=self.memory,
            self_state=getattr(
                agent,
                "self_state",
                None,
            ),
            affective_state=getattr(
                agent,
                "affective_state",
                None,
            ),
            diary=diary,
            model=self._model_for_ritual(),
            snapshots_enabled=(
                self.dream_snapshots
            ),
        )

        return self.dream_processor

    def _dream_night(self):
        processor = (
            self._ensure_dream_processor()
        )

        if processor is None:
            return {}

        try:
            result = processor.process()

            if result.get("status") == "dreamed":
                print(
                    "[dream] "
                    f"{result.get('emotion')} "
                    f"({result.get('intensity')}) "
                    f"frames={result.get('frames')} "
                    f"events={result.get('events')}",
                    flush=True,
                )
            else:
                print(
                    f"[dream] {result.get('status')}",
                    flush=True,
                )

            return result
        except Exception as exc:
            print(
                "[dream] failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

            return {}

    def snapshot(self):
        return RuntimeSnapshot(
            state=self.state,
            started_at=self.started_at,
            last_error=self.last_error,
            last_result=self.last_result,
            cycles_completed=self.cycles_completed,
        )

    def tick(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "state": "CLOSED",
                "reason": (
                    "Autonomous runtime уже закрыт."
                ),
            }

        if self.state in {
            "THINKING",
            "ACTING",
            "REFLECTING",
        }:
            return {
                "status": "BUSY",
                "state": self.state,
                "reason": (
                    "Автономный цикл уже выполняется."
                ),
            }

        if self.state == "PAUSED":
            return {
                "status": "PAUSED",
                "state": self.state,
                "reason": (
                    "Autonomous runtime находится "
                    "на паузе."
                ),
            }

        self._decay_affect()

        power = getattr(
            self, "_power_mode", None
        )
        if power is not None:
            try:
                transition = power.poll(
                    time.time()
                )
                if transition is not None:
                    self._announce_power(
                        transition
                    )
                    self._apply_power_limits()
            except Exception:
                pass

        if self.life_cycle is not None:
            try:
                _prev_asleep_since = self.life_cycle.state.get(
                    "asleep_since"
                )
            except Exception:
                _prev_asleep_since = None

            try:
                self.life_cycle.update()
            except Exception:
                pass

            _prev = self._prev_asleep
            self._prev_asleep = bool(
                self.life_cycle.is_asleep()
            )

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

            if self.life_cycle.is_asleep():
                if (
                    _prev is not None
                    and _prev != self._prev_asleep
                    and not _prev
                ):
                    self._evening_ritual()
                    self._dream_night()

                self.state = "ASLEEP"

                return {
                    "status": "ASLEEP",
                    "state": self.state,
                    "reason": (
                        "EddieAI спит — автономный "
                        "цикл приглушён, локальная "
                        "модель не грузится."
                    ),
                }

        self._inner_flow()

        power = getattr(
            self, "_power_mode", None
        )
        power_critical = (
            power is not None
            and power.mode == "critical"
        )

        if (
            hasattr(self, '_screen_perceiver')
            and self._screen_perceiver
            and not power_critical
        ):
            try:
                self._screen_perceiver.tick()
            except Exception:
                pass

            watch = getattr(
                self, "_watch_mode", None
            )

            if watch is not None:
                try:
                    self._handle_watch_mode(
                        watch
                    )
                except Exception:
                    pass

            if hasattr(self, '_shared_life') and self._shared_life:
                try:
                    current = (
                        self._screen_perceiver.get_current()
                        if hasattr(
                            self._screen_perceiver,
                            'get_current',
                        )
                        else {}
                    )
                    if current.get("description"):
                        obs = self._shared_life.observe(
                            current["description"],
                            eddie_present=True,
                        )
                        self._maybe_comment_screen(
                            current
                        )
                        if (
                            hasattr(self, '_shared_appraisal')
                            and self._shared_appraisal
                            and obs.get("is_shared")
                        ):
                            self._shared_appraisal.appraise(
                                obs,
                            )
                except Exception:
                    pass

            if (
                hasattr(self, '_shared_activity')
                and self._shared_activity
                and not self._shared_activity.is_active()
            ):
                try:
                    suggestion = (
                        self._shared_activity
                        .suggest_activity(
                            affective_state=getattr(
                                self.agent,
                                'affective_state',
                                None,
                            ),
                            interests=getattr(
                                self.agent.self_state,
                                'get',
                                lambda k, d=None: d,
                            )("interests", []),
                        )
                    )
                    if suggestion:
                        self._enqueue_shared_suggestion(
                            suggestion
                        )
                except Exception:
                    pass

        if self.resource_watchdog is not None:
            try:
                throttle = (
                    self.resource_watchdog
                    .should_throttle()
                )
                resources = (
                    self.resource_watchdog.check()
                )
            except Exception:
                throttle = False
                resources = {}

            if throttle:
                try:
                    self._probe_world_on_pressure(force=True)
                except Exception:
                    pass

                self.state = "LOW_RESOURCE"

                return {
                    "status": "THROTTLED",
                    "state": self.state,
                    "reason": (
                        "Мало свободной RAM — "
                        "LLM-тик пропущен, состояние "
                        "жизни обновлено без LLM."
                    ),
                    "resources": resources,
                }

        self.last_error = None

        power = getattr(
            self, "_power_mode", None
        )

        if (
            power is not None
            and power.mode == "critical"
        ):
            return {
                "status": "POWER_CRITICAL",
                "state": self.state,
                "reason": (
                    "Батарея критична — автономная "
                    "работа остановлена, жду розетку."
                ),
            }

        if power is not None and power.mode == "save":
            try:
                self.scheduler.interval_seconds = 60
            except Exception:
                pass
        elif power is not None and (
            power.mode == "normal"
        ):
            try:
                self.scheduler.interval_seconds = (
                    self._normal_scheduler_interval
                )
            except Exception:
                pass

        try:
            self.state = "ACTING"

            result = self.scheduler.tick()

            self.last_result = result
            self.cycles_completed += 1

            consolidation = None

            if (
                self.evidence_consolidator
                is not None
            ):
                self.state = "REFLECTING"

                consolidation = (
                    self.evidence_consolidator
                    .consolidate()
                )

                try:
                    consolidation = (
                        self._apply_consolidation(
                            consolidation
                        )
                    )
                except Exception:
                    pass

            if self.decision_core is not None:
                try:
                    self.decision_core.learn_from_memory()
                except Exception:
                    pass

                try:
                    self.decision_core.consolidate_habits()
                except Exception:
                    pass

            if self.speech_habits is not None:
                try:
                    self.speech_habits.learn_from_memory(
                        limit=30
                    )
                except Exception:
                    pass

            self.state = "IDLE"

            wrapped_result = {
                "runtime_result": result,
                "consolidation": consolidation,
            }

            self.last_result = wrapped_result

            return {
                "status": "OK",
                "state": self.state,
                "result": wrapped_result,
            }

        except Exception as exc:
            self.last_error = str(exc)
            self.state = "ERROR"

            return {
                "status": "ERROR",
                "state": self.state,
                "error": str(exc),
            }

    def notify_inbox(self):
        """
        Push-уведомление: Eddie пишет сообщение.
        Немедленно обрабатывает почту (EddieAI решает,
        прочитать ли), не дожидаясь интервала планировщика.
        """
        if self._closed:
            return {"status": "CLOSED"}

        if self.state == "PAUSED":
            return {"status": "PAUSED"}

        if self.orchestrator is None:
            return {"status": "NO_ORCHESTRATOR"}

        try:
            self._executor.submit(
                self._inbox_tick
            )
        except RuntimeError:
            return {"status": "SHUTDOWN"}

        return {"status": "QUEUED"}

    def _inbox_tick(self):
        try:
            return (
                self.orchestrator._handle_inbox()
            )
        except Exception:
            return None

    def tick_background(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "state": "CLOSED",
            }

        if self.state == "PAUSED":
            return {
                "status": "PAUSED",
                "state": self.state,
            }

        if (
            self._background_future is not None
            and not self._background_future.done()
        ):
            return {
                "status": "ALREADY_RUNNING",
                "state": self.state,
                "future": self._background_future,
            }

        self._background_future = (
            self._executor.submit(
                self.tick
            )
        )

        return {
            "status": "STARTED",
            "state": self.state,
            "future": self._background_future,
        }

    def background_status(self):
        future = self._background_future

        if future is None:
            return {
                "running": False,
                "done": False,
                "result": None,
            }

        if not future.done():
            return {
                "running": True,
                "done": False,
                "result": None,
            }

        try:
            result = future.result()
        except Exception as exc:
            result = {
                "status": "ERROR",
                "error": str(exc),
            }

        return {
            "running": False,
            "done": True,
            "result": result,
        }

    def start_background_loop(self):
        if self._closed:
            return {
                "status": "CLOSED",
                "reason": (
                    "Autonomous runtime уже закрыт."
                ),
            }

        if (
            self._loop_thread is not None
            and self._loop_thread.is_alive()
        ):
            return {
                "status": "ALREADY_RUNNING",
            }

        self._loop_stop.clear()

        self._loop_thread = threading.Thread(
            target=self._background_loop,
            name="EddieAI-AutonomyLoop",
            daemon=True,
        )

        self._loop_thread.start()

        return {
            "status": "STARTED",
        }

    def stop_background_loop(self):
        self._loop_stop.set()

        thread = self._loop_thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=2.0
            )

        self._loop_thread = None

        return {
            "status": "STOPPED",
        }

    def _background_loop(self):
        while not self._loop_stop.is_set():
            if self._closed:
                break

            try:
                if self.state != "PAUSED":
                    self.tick_background()

                    future = getattr(
                        self,
                        "_background_future",
                        None,
                    )

                    if (
                        future is not None
                        and future.done()
                    ):
                        exc = future.exception()

                        if exc is not None:
                            self.last_error = (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            )
            except Exception as exc:
                self.last_error = str(exc)
                self.state = "ERROR"

            self._loop_stop.wait(
                timeout=1.0
            )

    def pause(self):
        if self.state in {
            "THINKING",
            "ACTING",
            "REFLECTING",
        }:
            return {
                "status": "BUSY",
                "reason": (
                    "Нельзя поставить runtime "
                    "на паузу во время выполнения."
                ),
            }

        self.state = "PAUSED"

        return {
            "status": "PAUSED",
        }

    def resume(self):
        if self.state != "PAUSED":
            return {
                "status": "IGNORED",
                "reason": (
                    "Runtime не находится на паузе."
                ),
            }

        self.state = "IDLE"
        self.last_error = None

        return {
            "status": "RESUMED",
        }

    def reset_error(self):
        if self.state != "ERROR":
            return {
                "status": "IGNORED",
            }

        self.state = "IDLE"
        self.last_error = None

        return {
            "status": "RESET",
        }

    def close(self):
        if self._closed:
            return {
                "status": "ALREADY_CLOSED",
            }

        self.stop_background_loop()

        self._closed = True

        self._executor.shutdown(
            wait=True
        )

        self.state = "CLOSED"

        return {
            "status": "CLOSED",
        }
