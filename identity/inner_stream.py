"""Рубеж D «Внутренний поток»: непрерывное внутреннее время EddieAI.

Поток сознания: события восприятия и дел врываются в поток и копят
URGENCY — накопленное «хочу сказать». Инициатива рождается из порога
накопления, а не из кулдауна. Настроение-фон (mood) — долгоживущее
состояние (часы), красящее восприятие и речь; медленно дрейфует к
аффективному тону. Поток живёт в памяти процесса (сознание умирает со
сном/рестартом — так задумано), настроение персистентно в self_state.
"""
import time


SPEAK_THRESHOLD = 3.0
SPEAK_MIN_INTERVAL = 900.0
URGENCY_HALF_LIFE = 1200.0
MOOD_TAU_SEC = 7200.0
MAX_STREAM_ITEMS = 40


def affect_valence(emotions) -> float:
    emotions = emotions or {}

    def get(name):
        try:
            return float(
                emotions.get(name, 0.0)
            )
        except (TypeError, ValueError):
            return 0.0

    positive = get("joy") + 0.5 * get(
        "curiosity"
    ) + 0.3 * get("surprise")
    negative = (
        get("sadness")
        + get("anger")
        + get("fear")
        + 0.8 * get("frustration")
    )

    return max(
        -1.0, min(1.0, positive - negative)
    )


def affect_energy(emotions) -> float:
    emotions = emotions or {}

    def get(name):
        try:
            return float(
                emotions.get(name, 0.0)
            )
        except (TypeError, ValueError):
            return 0.0

    raw = (
        0.4 * get("curiosity")
        + 0.3 * get("surprise")
        + 0.2 * get("frustration")
        + 0.3 * get("joy")
        - 0.3 * get("sadness")
    )

    return max(0.0, min(1.0, raw))


def mood_label(valence, energy) -> str:
    if valence < -0.3:
        return (
            "мрачно"
            if energy < 0.4
            else "раздражённо"
        )
    if valence > 0.3:
        return (
            "оживлённо"
            if energy >= 0.4
            else "тепло и вяло"
        )
    return (
        "ровно"
        if energy < 0.5
        else "настороженно-бодро"
    )


class Mood:
    """
    Долгоживущий фон-настроение: медленно
    дрейфует к аффективному тону (τ ~2 ч),
    персистентен в self_state["mood_state"].
    """

    def __init__(self, self_state):
        self.self_state = self_state

        saved = self_state.get(
            "mood_state", {}
        ) or {}

        self.valence = float(
            saved.get("valence", 0.0)
        )
        self.energy = float(
            saved.get("energy", 0.4)
        )
        self.updated_at = saved.get(
            "updated_at"
        )

    def snapshot(self):
        return {
            "valence": round(self.valence, 3),
            "energy": round(self.energy, 3),
            "label": mood_label(
                self.valence, self.energy
            ),
        }

    def update(self, emotions, now):
        target_v = affect_valence(emotions)
        target_e = affect_energy(emotions)

        previous = self.updated_at

        dt = 0.0

        if previous:
            try:
                import datetime

                prior = datetime.datetime.fromisoformat(
                    previous
                )
                if prior.tzinfo is None:
                    import datetime as dtmod

                    prior = prior.replace(
                        tzinfo=dtmod.timezone.utc
                    )
                dt = max(
                    0.0,
                    now - prior.timestamp(),
                )
            except Exception:
                dt = 0.0

        alpha = 1.0 - pow(
            0.5, dt / MOOD_TAU_SEC
        ) if dt > 0 else 0.0

        self.valence += (
            target_v - self.valence
        ) * alpha
        self.energy += (
            target_e - self.energy
        ) * alpha

        self.updated_at = (
            time.strftime(
                "%Y-%m-%dT%H:%M:%S",
                time.gmtime(now),
            )
            + "+00:00"
        )

        self.self_state.set(
            "mood_state",
            {
                "valence": round(
                    self.valence, 3
                ),
                "energy": round(
                    self.energy, 3
                ),
                "label": mood_label(
                    self.valence,
                    self.energy,
                ),
                "updated_at": (
                    self.updated_at
                ),
            },
        )


class InnerStream:
    """
    Поток сознания: события врываются,
    копят urgency («хочу сказать»);
    инициатива — из порога накопления.
    """

    def __init__(
        self,
        max_items=MAX_STREAM_ITEMS,
        speak_threshold=SPEAK_THRESHOLD,
        speak_min_interval=SPEAK_MIN_INTERVAL,
        urgency_half_life=URGENCY_HALF_LIFE,
    ):
        self.items = []
        self.max_items = max_items
        self.speak_threshold = speak_threshold
        self.speak_min_interval = (
            speak_min_interval
        )
        self.urgency_half_life = (
            urgency_half_life
        )
        self._urgency = 0.0
        self._last_decay_ts = 0.0
        self.last_said_ts = 0.0
        self._last_seen = {}

    def add(
        self,
        kind,
        text,
        weight=1.0,
        now=None,
    ):
        now = (
            now
            if now is not None
            else time.time()
        )

        self._decay(now)

        self.items.append({
            "ts": now,
            "kind": kind,
            "text": (text or "").strip()[:160],
        })

        if len(self.items) > self.max_items:
            self.items = self.items[
                -self.max_items:
            ]

        self._urgency += weight

    def note_event(
        self,
        kind,
        key,
        text,
        weight=1.0,
        now=None,
    ):
        """
        Событие врывается в поток, только
        если его ключ изменился с прошлого
        раза (не дублируем одинаковый экран).
        """
        now = (
            now
            if now is not None
            else time.time()
        )

        if (
            self._last_seen.get(kind)
            == key
        ):
            return False

        self._last_seen[kind] = key
        self.add(kind, text, weight, now)
        return True

    def _decay(self, now):
        if self._last_decay_ts == 0.0:
            self._last_decay_ts = now
            return

        elapsed = now - self._last_decay_ts

        if elapsed <= 0:
            return

        factor = pow(
            0.5,
            elapsed
            / self.urgency_half_life,
        )

        self._urgency *= factor
        self._last_decay_ts = now

    def urgency(self, now=None) -> float:
        now = (
            now
            if now is not None
            else time.time()
        )
        self._decay(now)
        return round(self._urgency, 3)

    def should_speak(self, now=None) -> bool:
        now = (
            now
            if now is not None
            else time.time()
        )

        if (
            now - self.last_said_ts
            < self.speak_min_interval
        ):
            return False

        return (
            self.urgency(now)
            >= self.speak_threshold
        )

    def mark_spoke(self, now=None):
        now = (
            now
            if now is not None
            else time.time()
        )
        self.last_said_ts = now
        self._urgency = 0.0
        self._last_decay_ts = now

    def render_context(self, limit=8) -> str:
        items = self.items[-limit:]

        if not items:
            return ""

        lines = []

        for item in items:
            stamp = time.strftime(
                "%H:%M",
                time.localtime(item["ts"]),
            )
            lines.append(
                f"[{stamp}] {item['kind']}: "
                f"{item['text']}"
            )

        return "\n".join(lines)
