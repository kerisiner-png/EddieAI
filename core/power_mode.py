"""Осознанное энергосбережение EddieAI.

Ноутбук живёт и на батарее. EddieAI воспринимает питание
как факт своего тела: свет пропал — он ЗНАЕТ это, объявляет
Эдди и осознанно переходит в режим бережливости (реже смотрит,
тише думает, локальные модели запрещены); свет вернулся —
возвращается в обычный ритм. Критичная батарея — мольба
о розетке и остановка автономной работы.
"""
import ctypes
import time


SAVE_BATTERY_MIN = 15
CRITICAL_BATTERY_MAX = 15


def read_power_status() -> dict:
    """
    Фактическое питание машины (Win32
    GetSystemPowerStatus). На системах без
    ответа — неизвестно (в плену у сети).
    """
    class POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("Reserved1", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_uint32),
            ("BatteryFullLifeTime", ctypes.c_uint32),
        ]

    try:
        status = POWER_STATUS()
        result = ctypes.windll.kernel32.GetSystemPowerStatus(
            ctypes.byref(status)
        )
        if not result:
            return {"known": False}

        ac_online = status.ACLineStatus == 1
        has_battery = not (
            status.BatteryFlag & 128
        )
        percent = status.BatteryLifePercent

        if percent > 100 or not has_battery:
            percent = None

        return {
            "known": True,
            "ac_online": ac_online,
            "has_battery": has_battery,
            "percent": percent,
        }
    except Exception:
        return {"known": False}


class PowerMode:
    """
    Осознанный режим питания: NORMAL → SAVE →
    CRITICAL → обратно. Переход объявляется
    ОДИН раз (poll возвращает описание
    перехода для объявления Эдди).
    """

    def __init__(
        self,
        status_provider=read_power_status,
        critical_max=CRITICAL_BATTERY_MAX,
    ):
        self.status_provider = status_provider
        self.critical_max = critical_max
        self.mode = "normal"
        self.percent = None
        self.ac_online = True
        self._announced = "normal"

    def poll(self, now) -> dict | None:
        status = self.status_provider()

        if not status.get("known"):
            return None

        self.ac_online = bool(
            status.get("ac_online", True)
        )
        self.percent = status.get("percent")

        previous_mode = self.mode
        self._decide()

        if self.mode != previous_mode:
            transition = {
                "from": previous_mode,
                "to": self.mode,
                "percent": self.percent,
                "at": now,
            }
            self._announced = self.mode
            return transition

        if (
            self.mode == "critical"
            and self._announced != "critical"
        ):
            self._announced = "critical"
            return {
                "from": "save",
                "to": "critical",
                "percent": self.percent,
                "at": now,
            }

        return None

    def _decide(self):
        if self.ac_online:
            self.mode = "normal"
            return

        percent = self.percent

        if (
            percent is not None
            and percent <= self.critical_max
        ):
            self.mode = "critical"
        else:
            self.mode = "save"

    def on_battery(self) -> bool:
        return self.mode in {
            "save",
            "critical",
        }
