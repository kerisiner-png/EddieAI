import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent


class NightConsolidator:
    """
    Этаж 7 «Внутренняя жизнь»: превращение хроники
    сессии в личностные выводы.

    Уровни:
    1. Структурная сводка дня — всегда работает,
       без LLM.
    2. Вывод дня в self_conclusions («что этот день
       мне дал») — через облачный LLM; записывается
       только если модель вернула содержательный текст.
    """

    def __init__(
        self,
        memory,
        model_orchestrator=None,
        conclusion_store=None,
        db_path=None,
    ):
        self.memory = memory
        self.model_orchestrator = (
            model_orchestrator
        )
        self.conclusion_store = (
            conclusion_store
        )
        self.db_path = (
            Path(db_path)
            if db_path
            else _BASE_DIR / "data" / "memory.db"
        )

    # ---------------------------------------------
    # ХРОНИКА
    # ---------------------------------------------

    def collect_chronicle(
        self,
        since_id: int = 0,
        limit: int = 200,
    ) -> list[dict]:
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            timeout=10,
        )
        conn.row_factory = sqlite3.Row

        try:
            rows = conn.execute(
                "SELECT id, event_type, source, "
                "substr(content, 1, 160) AS c "
                "FROM events "
                "WHERE id > ? "
                "ORDER BY id ASC LIMIT ?",
                (since_id, limit),
            ).fetchall()
        finally:
            conn.close()

        return [
            {
                "id": r["id"],
                "type": r["event_type"],
                "source": r["source"],
                "text": r["c"],
            }
            for r in rows
        ]

    # ---------------------------------------------
    # СТРУКТУРНАЯ СВОДКА (без LLM)
    # ---------------------------------------------

    @staticmethod
    def structural_summary(
        chronicle: list[dict],
    ) -> dict:
        counts: dict[str, int] = {}

        for item in chronicle:
            key = item["type"]
            counts[key] = (
                counts.get(key, 0) + 1
            )

        actions = sum(
            v
            for k, v in counts.items()
            if k in {
                "TOOL_RESULT",
                "SELF_EXPERIENCE",
                "ACTION_CHOICE",
            }
        )

        return {
            "events_total": len(chronicle),
            "actions_performed": actions,
            "by_type": counts,
        }

    # ---------------------------------------------
    # ВЫВОД ДНЯ ЧЕРЕЗ LLM
    # ---------------------------------------------

    def day_conclusion_via_llm(
        self,
        chronicle: list[dict],
    ) -> dict | None:
        if (
            self.model_orchestrator is None
            or not chronicle
        ):
            return None

        lines = []

        for item in chronicle[-60:]:
            text = (item["text"] or "").replace(
                "\n",
                " ",
            )

            if text:
                lines.append(
                    f"- [{item['type']}] {text}"
                )

        prompt = f"""
Перед тобой хроника событий из твоей жизни
за день. Это РЕАЛЬНО произошедшее.

Хроника:
{chr(10).join(lines)}

Сформулируй 1–3 кратких вывода о себе:
что этот день тебе дал, что ты понял,
какие темы оказались для тебя важными.

Правила:
- Только на основе хроники.
- От первого лица EddieAI.
- Никаких выдуманных событий.
- Без пояснений и размышлений: ответ
  начинается сразу с JSON.
- topic и text — на русском языке.
- Верни JSON: {{"conclusions":
  [{{"topic": "...", "text": "...",
  "confidence": 0.0}}]}}
"""

        system = (
            "Ты EddieAI. Ты осмысляешь прожитый "
            "день и формулируешь честные выводы "
            "о себе. Осторожно: не выдумывай. "
            "Не пиши пояснений и размышлений. "
            "Ответ начинается сразу с JSON."
        )

        options = {
            "temperature": 0.4,
            "num_predict": 2048,
        }

        for attempt in (
            ("reflection", system),
            ("reflection", system),
            ("deep", system),
        ):
            task, sys_text = attempt

            try:
                raw = (
                    self.model_orchestrator
                    ._cloud_chat(
                        system=sys_text,
                        user=prompt,
                        options=options,
                        task=task,
                    )
                )
            except Exception:
                raw = None

            if not raw:
                continue

            data = self._parse_json_object(
                raw
            )

            if (
                data is not None
                and isinstance(data, dict)
            ):
                return data

        return None

    @staticmethod
    def _parse_json_object(raw: str):
        first = raw.find("{")
        last = raw.rfind("}")

        if first == -1 or last == -1:
            return None

        if last < first:
            return None

        try:
            return json.loads(
                raw[first : last + 1]
            )
        except json.JSONDecodeError:
            return None

    # ---------------------------------------------
    # ЗАПИСЬ ВЫВОДОВ В ЛИЧНОСТЬ
    # ---------------------------------------------

    def save_conclusions(
        self,
        conclusions: list[dict],
        day_stamp: str,
    ):
        saved = []

        if (
            self.conclusion_store is None
        ):
            return saved

        for item in conclusions[:3]:
            topic = str(
                item.get("topic", "")
            ).strip()

            text = str(
                item.get("text", "")
            ).strip()

            confidence = float(
                item.get("confidence", 0.5)
            )

            if (
                not topic
                or not text
                or len(text) < 20
            ):
                continue

            try:
                self.conclusion_store.save(
                    topic=(
                        f"Вывод дня {day_stamp}: "
                        f"{topic}"
                    ),
                    conclusion=text,
                    confidence=max(
                        0.2,
                        min(0.9, confidence),
                    ),
                    basis=[
                        "хроника дневной сессии",
                    ],
                    provenance=[
                        "self_reflection",
                    ],
                    predicates=["realized"],
                    language="ru",
                )

                saved.append(topic)
            except Exception:
                continue

        return saved

    # ---------------------------------------------
    # ЗАПУСК
    # ---------------------------------------------

    def run(
        self,
        since_id: int = 0,
    ) -> dict:
        chronicle = self.collect_chronicle(
            since_id
        )

        summary = (
            self.structural_summary(chronicle)
        )

        result = {
            "chronicle_events": len(chronicle),
            "summary": summary,
            "conclusions_saved": [],
            "llm_used": False,
        }

        if not chronicle:
            return result

        day_stamp = datetime.now(
            timezone.utc
        ).strftime("%d.%m.%Y")

        conclusions = (
            self.day_conclusion_via_llm(
                chronicle
            )
        )

        if conclusions:
            result["llm_used"] = True

            result[
                "conclusions_saved"
            ] = self.save_conclusions(
                conclusions.get(
                    "conclusions",
                    [],
                ),
                day_stamp,
            )

        return result
