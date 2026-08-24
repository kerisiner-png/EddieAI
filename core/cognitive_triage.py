from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import time

_DEFAULT_TRIAGE_DIR = Path(
    os.environ.get("EDDIE_DATA_DIR")
    or (
        Path(__file__).resolve().parent.parent
        / "data"
    )
)


@dataclass(frozen=True)
class TriageDecision:
    route: str
    reason: str
    expected_seconds: float
    expected_value: float
    cost_value_ratio: float


class CognitiveTriage:
    """
    Определяет, стоит ли тратить вычислительный ресурс
    на глубокую LLM-обработку.

    DETERMINISTIC:
        простые и очевидные случаи.

    QWEN:
        случаи, где дополнительное reasoning действительно
        потенциально ценно.
    """

    def __init__(
        self,
        path: str | None = None,
    ):
        if path is None:
            path = (
                _DEFAULT_TRIAGE_DIR
                / "cognitive_performance.json"
            )

        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.records = self._load()

    def _load(self):
        if not self.path.exists():
            return {}

        try:
            return json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return {}

    def _save(self):
        temp = self.path.with_suffix(".tmp")

        temp.write_text(
            json.dumps(
                self.records,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temp.replace(self.path)

    def _estimate_seconds(
        self,
        operation: str,
        default: float,
    ) -> float:

        record = self.records.get(
            operation
        )

        if not record:
            return default

        samples = record.get(
            "durations",
            [],
        )

        if not samples:
            return default

        return (
            sum(samples)
            / len(samples)
        )

    def evaluate(
        self,
        *,
        content: str,
        event_type: str,
        route: str,
        reason: str,
    ) -> TriageDecision:

        text = content.lower()

        # ---------------------------------------------
        # SIMPLE / DETERMINISTIC CASES
        # ---------------------------------------------

        if event_type == "USER_INTEREST":
            return TriageDecision(
                route="DETERMINISTIC",
                reason="user_interest_is_structurally_simple",
                expected_seconds=0.05,
                expected_value=0.45,
                cost_value_ratio=9.0,
            )

        if (
            "привет" in text
            or "спасибо" in text
        ):
            return TriageDecision(
                route="DETERMINISTIC",
                reason="routine_conversation",
                expected_seconds=0.01,
                expected_value=0.05,
                cost_value_ratio=5.0,
            )

        # ---------------------------------------------
        # HIGH-VALUE REASONING
        # ---------------------------------------------

        high_reasoning_markers = (
            "противореч",
            "почему",
            "причин",
            "сравни",
            "выведи",
            "стратег",
            "архитектур",
            "саморазвит",
            "самомодел",
            "belief",
            "убеждени",
            "конфликт",
            "нескольк",
        )

        reasoning_required = any(
            marker in text
            for marker in high_reasoning_markers
        )

        expected_seconds = (
            self._estimate_seconds(
                "qwen",
                120.0,
            )
        )

        if reasoning_required:
            expected_value = 0.90

            return TriageDecision(
                route="QWEN",
                reason="high_reasoning_value",
                expected_seconds=expected_seconds,
                expected_value=expected_value,
                cost_value_ratio=(
                    expected_value
                    / max(expected_seconds, 0.01)
                ),
            )

        # ---------------------------------------------
        # DEFAULT
        # ---------------------------------------------

        expected_value = 0.35

        # Длинное содержимое потенциально полезнее,
        # но всё ещё не обязательно требует Qwen.
        if len(content) > 300:
            expected_value += 0.15

        if (
            event_type in {
                "SELF_CONTRADICTION",
                "EVIDENCE",
            }
        ):
            expected_value += 0.15

        ratio = (
            expected_value
            / max(expected_seconds, 0.01)
        )

        # Не тратим ~2 минуты ради небольшого
        # потенциального выигрыша.
        if (
            expected_seconds > 30.0
            and expected_value < 0.70
        ):
            return TriageDecision(
                route="DETERMINISTIC",
                reason="llm_cost_exceeds_expected_value",
                expected_seconds=expected_seconds,
                expected_value=expected_value,
                cost_value_ratio=ratio,
            )

        return TriageDecision(
            route="QWEN",
            reason="default_reasoning",
            expected_seconds=expected_seconds,
            expected_value=expected_value,
            cost_value_ratio=ratio,
        )

    def record_duration(
        self,
        operation: str,
        duration: float,
    ):
        record = self.records.setdefault(
            operation,
            {
                "durations": [],
            },
        )

        durations = record[
            "durations"
        ]

        durations.append(
            float(duration)
        )

        # Храним только последние 20 измерений.
        record["durations"] = durations[-20:]

        self._save()

    def stats(self):
        result = {}

        for operation, record in (
            self.records.items()
        ):
            durations = record.get(
                "durations",
                [],
            )

            if not durations:
                continue

            result[operation] = {
                "samples": len(durations),
                "average_seconds": (
                    sum(durations)
                    / len(durations)
                ),
                "last_seconds": durations[-1],
            }

        return result
