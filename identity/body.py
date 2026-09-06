"""Тело EddieAI: гомеостаз потребностей.

Не имитация биологии — его РЕАЛЬНЫЕ потребности цифрового
существа: общение с Эдди (социальная) и новизна восприятия
(однообразие давит). Потребности растут со временем, события
удовлетворяют их, вклад в urgency потока — пропорционален.
Персистентно в self_state["body_state"].
"""
import time

SOCIAL_SATURATION_SEC = 3.0 * 3600
NOVELTY_SATURATION_SEC = 2.0 * 3600


def clamp01(value):
    return max(0.0, min(1.0, value))


def grow(prev, dt, saturation_sec):
    if saturation_sec <= 0:
        return clamp01(prev)
    return clamp01(prev + dt / saturation_sec)


def social_label(need) -> str:
    if need >= 0.8:
        return "скучаю по Эдди"
    if need >= 0.5:
        return "хочется болтать"
    if need >= 0.25:
        return "нормально"
    return "сыт общением"


def novelty_label(need) -> str:
    if need >= 0.8:
        return "скучно, всё одно и то же"
    if need >= 0.5:
        return "хочется чего-то нового"
    return "достаточно впечатлений"


class Body:
    def __init__(
        self,
        self_state,
        social_saturation_sec=SOCIAL_SATURATION_SEC,
        novelty_saturation_sec=NOVELTY_SATURATION_SEC,
    ):
        self.self_state = self_state
        self.social_saturation_sec = (
            social_saturation_sec
        )
        self.novelty_saturation_sec = (
            novelty_saturation_sec
        )

        saved = self_state.get(
            "body_state", {}
        ) or {}

        self.social_need = clamp01(
            float(saved.get("social_need", 0.3))
        )
        self.novelty_need = clamp01(
            float(saved.get("novelty_need", 0.2))
        )
        self.updated_at = saved.get(
            "updated_at"
        )

    def update(
        self,
        now,
        seconds_since_contact=None,
        screen_stale_sec=None,
    ):
        previous = self.updated_at
        dt = 0.0

        if previous:
            try:
                import datetime

                prior = (
                    datetime.datetime.fromisoformat(
                        previous
                    )
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

        if seconds_since_contact is not None:
            self.social_need = clamp01(
                seconds_since_contact
                / self.social_saturation_sec
            )
        else:
            self.social_need = grow(
                self.social_need,
                dt,
                self.social_saturation_sec,
            )

        if screen_stale_sec is not None:
            self.novelty_need = clamp01(
                screen_stale_sec
                / self.novelty_saturation_sec
            )
        else:
            self.novelty_need = grow(
                self.novelty_need,
                dt,
                self.novelty_saturation_sec,
            )

        self.updated_at = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.gmtime(now),
        ) + "+00:00"

        self.self_state.set(
            "body_state",
            {
                "social_need": round(
                    self.social_need, 3
                ),
                "novelty_need": round(
                    self.novelty_need, 3
                ),
                "social_label": social_label(
                    self.social_need
                ),
                "novelty_label": novelty_label(
                    self.novelty_need
                ),
                "updated_at": self.updated_at,
            },
        )

    def satisfy_social(self, now=None):
        self.social_need = 0.0

        if now is not None:
            self.updated_at = time.strftime(
                "%Y-%m-%dT%H:%M:%S",
                time.gmtime(now),
            ) + "+00:00"

        self.self_state.set(
            "body_state",
            {
                "social_need": 0.0,
                "novelty_need": round(
                    self.novelty_need, 3
                ),
                "social_label": social_label(
                    0.0
                ),
                "novelty_label": novelty_label(
                    self.novelty_need
                ),
                "updated_at": self.updated_at,
            },
        )

    def urgency_contribution(self) -> float:
        return (
            self.social_need * 2.0
            + self.novelty_need * 1.0
        )

    def snapshot(self):
        return {
            "social_need": round(
                self.social_need, 3
            ),
            "novelty_need": round(
                self.novelty_need, 3
            ),
            "social_label": social_label(
                self.social_need
            ),
            "novelty_label": novelty_label(
                self.novelty_need
            ),
        }
