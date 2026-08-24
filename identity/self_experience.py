from dataclasses import dataclass

from memory.events import Event
from memory.knowledge import Knowledge


@dataclass
class ExperienceSignal:
    category: str
    value: str
    confidence: float = 0.8


class SelfExperienceConsolidator:
    """
    Консолидирует результат собственного действия.

    Важно:
    успешное действие само по себе не считается чертой.
    Сначала сохраняется опыт.
    Отдельный signal может превратиться в evidence.
    """

    ALLOWED_CATEGORIES = {
        "interest",
        "preference",
        "habit",
        "belief",
        "goal",
    }

    def __init__(
        self,
        memory,
        evidence,
    ):
        self.memory = memory
        self.evidence = evidence

    def record(
        self,
        action,
        result: dict,
    ):
        status = result.get(
            "status",
            "UNKNOWN",
        )

        tool = result.get(
            "tool",
            action.action_type,
        )

        content = self._build_experience(
            action,
            result,
        )

        event = Event.create(
            content=content,
            event_type="SELF_EXPERIENCE",
            source_type="TOOL",
            source=tool,
            personal_experience=True,
            confidence=(
                1.0
                if status == "OK"
                else 0.3
            ),
            verified=(status == "OK"),
        )

        self.memory.remember(event)

        knowledge = Knowledge(
            content=content,
            owner="SELF",
            source_type="TOOL",
            source=tool,
            confidence=(
                1.0
                if status == "OK"
                else 0.3
            ),
            verified=(status == "OK"),
            personal_experience=True,
        )

        self.memory.remember_knowledge(
            knowledge
        )

        return {
            "event": event,
            "knowledge": knowledge,
            "status": status,
        }

    def record_signals(
        self,
        signals: list[ExperienceSignal],
        source: str = "self_experience",
    ):
        recorded = []

        for signal in signals:
            if signal.category not in (
                self.ALLOWED_CATEGORIES
            ):
                continue

            value = signal.value.strip()

            if not value:
                continue

            record = self.evidence.add(
                category=signal.category,
                value=value,
                source="SELF_ACTION",
            )

            self.memory.remember(
                Event.create(
                    content=(
                        "Наблюдаемая особенность "
                        f"после собственного опыта: "
                        f"{signal.category} = {value}; "
                        f"уверенность={signal.confidence}"
                    ),
                    event_type="EVIDENCE",
                    source_type="SELF_ACTION",
                    source=source,
                    personal_experience=True,
                    confidence=signal.confidence,
                    verified=False,
                )
            )

            recorded.append(
                {
                    "signal": signal,
                    "evidence": record,
                }
            )

        return recorded

    def _build_experience(
        self,
        action,
        result,
    ) -> str:
        status = result.get(
            "status",
            "UNKNOWN",
        )

        tool = result.get(
            "tool",
            action.action_type,
        )

        payload = result.get(
            "result",
            {},
        )

        if isinstance(payload, dict):
            content = payload.get(
                "content"
            )

            if content:
                return (
                    f"Я самостоятельно выполнил "
                    f"действие '{action.target}' "
                    f"через инструмент {tool}. "
                    f"Результат: {content}"
                )

        return (
            f"Я самостоятельно выполнил "
            f"действие '{action.target}' "
            f"через инструмент {tool}. "
            f"Статус: {status}."
        )
