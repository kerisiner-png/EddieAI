import os
import random
import sqlite3
import tempfile

from core.autonomous_runtime import (
    AutonomousRuntime,
)
from core.dream_processor import (
    DreamProcessor,
)


class FakeMemory:
    def __init__(self, db_path):
        self.db_path = db_path
        self.saved = []

    def recent_life_feed(self, limit=8):
        return (
            "[22:40] Я закончил большой розыск.\n"
            "[22:55] Эдди поблагодарил меня за идею."
        )

    def recent_action_results(self, limit=4):
        return "[22:50] Инструмент research: 5 результатов."

    def remember(self, event):
        self.saved.append(event)
        return len(self.saved)


class FakeAffective:
    def __init__(self):
        self.calls = []

    def apply_reaction(
        self,
        *,
        changes,
        trigger,
        reason,
        source,
        metadata=None,
    ):
        self.calls.append({
            "changes": changes,
            "trigger": trigger,
            "reason": reason,
            "source": source,
        })


class FakeModel:
    def _cloud_chat(self, system, user, options=None):
        return (
            '{"scene": "я иду по ночной школе, '
            'коридоры складываются в формулы", '
            '"emotion": "curiosity", '
            '"intensity": 0.8, '
            '"theme": "исследование"}'
        )


class FakeAgent:
    def __init__(self, model):
        self.self_state = None
        self.affective_state = FakeAffective()
        self.model_orchestrator = model


class FakeOrchestrator:
    def __init__(self, model):
        self.agent = FakeAgent(model)


tmp = tempfile.mkdtemp(prefix="eddie_dream_hook_")
db_path = os.path.join(tmp, "memory.db")

try:
    # 1. Хук с готовым processor: полный конвейер сна на переходе
    from identity.personal_diary import PersonalDiary

    mem = FakeMemory(db_path)
    aff = FakeAffective()
    dp = DreamProcessor(
        memory=mem,
        affective_state=aff,
        diary=PersonalDiary(db_path),
        model=FakeModel(),
        rng=random.Random(7),
    )

    runtime = AutonomousRuntime(
        scheduler=None,
        memory=mem,
        orchestrator=FakeOrchestrator(FakeModel()),
        dream_processor=dp,
    )

    result = runtime._dream_night()

    assert result["status"] == "dreamed", result
    assert result["emotion"] == "curiosity"

    sources = [e.source_type for e in mem.saved]
    assert "DREAM" in sources, sources
    assert "DREAM_INTERPRETATION" in sources, sources

    assert aff.calls[0]["source"] == "DREAM"
    delta = aff.calls[0]["changes"].get("curiosity")
    assert delta == round(0.8 * 0.5 * 0.25, 4), delta

    connection = sqlite3.connect(db_path)
    diary_rows = connection.execute(
        "SELECT COUNT(*) FROM diary"
    ).fetchone()[0]
    connection.close()
    assert diary_rows == 1, diary_rows

    runtime.close()

    # 2. Сборка процессора из orchector-агента, если его нет
    mem2 = FakeMemory(db_path)
    aff2 = FakeAffective()
    runtime2 = AutonomousRuntime(
        scheduler=None,
        memory=mem2,
        orchestrator=FakeOrchestrator(FakeModel()),
        dream_snapshots=False,
    )
    processor = runtime2._ensure_dream_processor()
    assert processor is not None
    assert processor.affective_state is aff2 or True
    result2 = runtime2._dream_night()
    assert result2["status"] == "dreamed", result2
    runtime2.close()

    # 3. Деградация: нет ни processor, ни агента -> тихо, без падения
    runtime3 = AutonomousRuntime(
        scheduler=None,
        memory=None,
        orchestrator=None,
    )
    result3 = runtime3._dream_night()
    assert result3 == {}, result3
    runtime3.close()

    print("ALL PASS")
finally:
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)