# -*- coding: utf-8 -*-
# Вживление осознанного энергосбережения.
import sys

def patch_factory():
    p = 'core/autonomy_runtime_factory.py'
    s = open(p, encoding='utf-8').read()
    old = """        self.agent.inner_stream = InnerStream()
        self.agent.mood = Mood(
            self.agent.self_state
        )"""
    new = """        self.agent.inner_stream = InnerStream()
        self.agent.mood = Mood(
            self.agent.self_state
        )

        from core.power_mode import PowerMode

        power_mode = PowerMode()
        runtime._power_mode = power_mode
        self.agent.power_mode = power_mode"""
    assert s.count(old) == 1, "factory: %d" % s.count(old)
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('factory wired')

def patch_runtime():
    p = 'core/autonomous_runtime.py'
    s = open(p, encoding='utf-8').read()

    # 1) poll питания в тике
    old = """        self._decay_affect()

        if self.life_cycle is not None:"""
    new = """        self._decay_affect()

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

        if self.life_cycle is not None:"""
    assert s.count(old) == 1, "tick: %d" % s.count(old)
    s = s.replace(old, new)

    # 2) критичная батарея останавливает автономную работу
    old2 = """        self.last_error = None

        try:
            self.state = "ACTING"

            result = self.scheduler.tick()"""
    new2 = """        self.last_error = None

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

            result = self.scheduler.tick()"""
    assert s.count(old2) == 1, "sched: %d" % s.count(old2)
    s = s.replace(old2, new2)

    # 3) методы объявления и лимитов
    anchor = """    def _eddie_present(self) -> bool:"""
    methods = '''    def _announce_power(self, transition):
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

    def _eddie_present(self) -> bool:'''
    assert s.count(anchor) == 1, "anchor: %d" % s.count(anchor)
    s = s.replace(anchor, methods, 1)

    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('runtime wired')

def patch_normal_interval():
    # базовый интервал планировщика — атрибут рантайма
    p = 'core/autonomous_runtime.py'
    s = open(p, encoding='utf-8').read()
    old = """        self.scheduler = scheduler
        self.memory = memory"""
    new = """        self.scheduler = scheduler
        self._normal_scheduler_interval = getattr(
            scheduler, "interval_seconds", 15
        )
        self.memory = memory"""
    assert s.count(old) == 1
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('normal interval stored')

def patch_screen_block():
    # критичная батарея: не смотреть вовсе
    p = 'core/autonomous_runtime.py'
    s = open(p, encoding='utf-8').read()
    old = """        if hasattr(self, '_screen_perceiver') and self._screen_perceiver:
            try:
                self._screen_perceiver.tick()
            except Exception:
                pass"""
    new = """        power = getattr(
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
                pass"""
    assert s.count(old) == 1
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('screen gated')

def patch_cam():
    # вебка на батарее смотрит втрое реже
    p = 'identity/sense_listener.py'
    s = open(p, encoding='utf-8').read()
    old = """    def _cam_loop(self):
        while not self._stop.is_set():
            try:
                self._cam_pass()
            except Exception:
                pass
            self._stop.wait(
                timeout=self._webcam_interval
            )"""
    new = """    def _cam_loop(self):
        while not self._stop.is_set():
            try:
                self._cam_pass()
            except Exception:
                pass
            interval = self._webcam_interval

            power = getattr(
                self._agent,
                "power_mode",
                None,
            ) if self._agent is not None else None

            if power is not None and power.on_battery():
                interval *= 3

            self._stop.wait(timeout=interval)"""
    assert s.count(old) == 1
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('cam gated')

def patch_orchestrator():
    # локальные модели запрещены на батарее
    p = 'core/model_orchestrator.py'
    s = open(p, encoding='utf-8').read()
    old = """        free_gb = self.available_ram_gb()
        required_gb = self.MODEL_RAM_GB.get(model.name)
        if required_gb is not None and free_gb < required_gb:"""
    new = """        free_gb = self.available_ram_gb()
        required_gb = self.MODEL_RAM_GB.get(model.name)
        on_battery = not read_power_status().get(
            "ac_online", True
        ) if read_power_status().get("known") else False
        if required_gb is not None and (
            free_gb < required_gb or on_battery
        ):"""
    assert s.count(old) == 1
    s = s.replace(old, new)
    old2 = '''                print(
                    f"[orchestrator] мало RAM ({free_gb:.1f} GB) "
                    f"для {model.name}: даунгрейд на {lighter}"
                )'''
    new2 = '''                print(
                    f"[orchestrator] мало RAM ({free_gb:.1f} GB) "
                    f"для {model.name}: даунгрейд на {lighter}"
                    + (" (on battery)" if on_battery else "")
                )'''
    assert s.count(old2) == 1
    s = s.replace(old2, new2)
    # на батарее даунгрейд тоже запрещён — сразу отказ
    old3 = """            if (
                model.name != lighter
                and lighter_need is not None
                and free_gb >= lighter_need
            ):"""
    new3 = """            if (
                model.name != lighter
                and lighter_need is not None
                and free_gb >= lighter_need
                and not on_battery
            ):"""
    assert s.count(old3) == 1
    s = s.replace(old3, new3)
    # импорт
    old4 = "    SECRETS_DIR = Path.home() / \".eddieai_secrets\""
    new4 = """    from core.power_mode import read_power_status

    SECRETS_DIR = Path.home() / ".eddieai_secrets\""""
    assert s.count(old4) == 1
    s = s.replace(old4, new4)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('orchestrator battery gate')

def patch_heartbeat():
    p = 'run_forever.py'
    s = open(p, encoding='utf-8').read()
    old = """    try:
        cycles = getattr(
            runtime, "cycles_completed", None
        )"""
    new = """    try:
        power = getattr(
            runtime, "_power_mode", None
        )
        if power is not None:
            data["power"] = {
                "mode": power.mode,
                "ac_online": power.ac_online,
                "percent": power.percent,
            }
    except Exception:
        pass
    try:
        cycles = getattr(
            runtime, "cycles_completed", None
        )"""
    assert s.count(old) == 1
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('heartbeat power wired')

patch_factory()
patch_runtime()
patch_normal_interval()
patch_screen_block()
patch_cam()
patch_orchestrator()
patch_heartbeat()

for f in ['core/autonomy_runtime_factory.py', 'core/autonomous_runtime.py',
          'identity/sense_listener.py', 'core/model_orchestrator.py', 'run_forever.py']:
    import py_compile
    py_compile.compile(f, doraise=True)
print('ALL COMPILE OK')
