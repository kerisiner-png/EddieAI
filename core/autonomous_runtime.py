from dataclasses import dataclass
from datetime import datetime, timezone
from concurrent.futures import Future, ThreadPoolExecutor
import threading

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
                server.send_initiative(text)
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

        if hasattr(self, '_screen_perceiver') and self._screen_perceiver:
            try:
                self._screen_perceiver.tick()
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
