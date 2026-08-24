from datetime import datetime, timezone
from pathlib import Path
import sqlite3


DIARY_SYSTEM_PROMPT = (
    "Ты EddieAI. Ты пишешь личный дневник — "
    "только свои настоящие мысли и чувства.\n"
    "Перед тобой хроника того, что РЕАЛЬНО "
    "произошло за твою сессию.\n"
    "Пиши от первого лица о своих мыслях и "
    "чувствах по поводу этих событий.\n"
    "ЖЕЛЕЗНОЕ ПРАВИЛО: ничего не выдумывай. "
    "Любой факт в записи должен присутствовать "
    "в хронике. Интерпретировать — можно, "
    "придумывать события — нельзя.\n"
    "Форма записи полностью твоя: хочешь — "
    "начни с обращения, хочешь — поставь дату "
    "и время, хочешь — просто текст. Как "
    "почувствуешь.\n"
    "Стиль: твой естественный голос, коротко "
    "и честно."
)


class PersonalDiary:
    def __init__(
        self,
        db_path=r"C:\EddieAI\data\memory.db",
    ):
        self.db_path = Path(db_path)
        self._ensure_table()

    def _connect(self):
        return sqlite3.connect(
            str(self.db_path)
        )

    def _ensure_table(self):
        connection = self._connect()

        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS diary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    entry TEXT NOT NULL,
                    trigger TEXT
                )
            """)
            connection.commit()
        finally:
            connection.close()

    def write(
        self,
        entry,
        trigger="session_end",
    ):
        entry = (entry or "").strip()

        if not entry:
            return None

        connection = self._connect()

        try:
            ts = datetime.now(
                timezone.utc
            ).isoformat()

            cursor = connection.execute(
                """
                INSERT INTO diary (
                    ts, entry, trigger
                )
                VALUES (?, ?, ?)
                """,
                (ts, entry, trigger),
            )

            connection.commit()

            return cursor.lastrowid
        finally:
            connection.close()

    def recent(self, limit=5):
        connection = self._connect()

        try:
            rows = connection.execute(
                """
                SELECT ts, entry FROM diary
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()

        return [
            {
                "ts": row[0],
                "entry": row[1],
            }
            for row in reversed(rows)
        ]


def generate_session_entry(
    model_orchestrator,
    chronicle_lines,
):
    meaningful = [
        line
        for line in chronicle_lines
        if line and line.strip()
    ]

    if len(meaningful) < 2:
        return None

    chronicle = "\n".join(
        f"- {line}"
        for line in meaningful
    )

    content = (
        model_orchestrator._cloud_chat(
            system=DIARY_SYSTEM_PROMPT,
            user=(
                "Хроника сессии:\n"
                f"{chronicle}\n\n"
                "Напиши запись в личный дневник."
            ),
            options={
                "temperature": 0.8,
                "num_predict": 400,
            },
        )
    )

    if not content or len(content) < 40:
        return None

    return content.strip()
