import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from memory.database import Memory
from memory.evidence import EvidenceEngine
from memory.events import Event
from core.agent_loop import AgentLoop
from identity.action_preference_detector import ActionPreferenceDetector
from identity.identity_manager import IdentityManager
from identity.self_state import SelfState


class DummyExpRecorder:
    def __init__(self, memory):
        self.memory = memory


class DummyOutbox:
    def __init__(self):
        self.messages = []

    def send(self, message, server=None):
        self.messages.append(message)
        return True


def _action_payload(context, options, selected, task=None):
    choice = {
        "context_type": context,
        "options": options,
        "selected": selected,
    }
    if task:
        choice["task"] = task
    return json.dumps(
        {"choice": choice},
        ensure_ascii=False,
    )


def _fill_choices(memory, task=None, sequence=None):
    if sequence is None:
        sequence = ["read", "read", "read", "walk"]
    for sel in sequence:
        memory.remember(Event.create(
            content=_action_payload(
                "break", ["read", "walk"], sel, task=task,
            ),
            event_type="ACTION_CHOICE",
            source_type="SELF_ACTION",
            personal_experience=True,
        ))


def _make_loop(tmpdir, db_name):
    db = Path(tmpdir) / db_name
    memory = Memory(db)
    evidence = EvidenceEngine(memory)
    detector = ActionPreferenceDetector(memory, evidence)
    state = SelfState(Path(tmpdir) / f"{db_name}_self.json")
    manager = IdentityManager(state, memory)
    outbox = DummyOutbox()

    loop = AgentLoop(
        goal_manager=object(),
        goal_planner=object(),
        action_planner=object(),
        tool_runner=object(),
        task_controller=object(),
        experience_recorder=DummyExpRecorder(memory),
        action_preference_detector=detector,
        habit_pattern_detector=None,
        belief_pattern_detector=None,
        evidence=evidence,
        identity_manager=manager,
        outbox=outbox,
    )
    return memory, outbox, loop


def test_new_preference_sent_to_outbox(tmpdir):
    memory, outbox, loop = _make_loop(tmpdir, "new.db")
    try:
        seq = (["read"] * 9) + (["walk"] * 3)
        _fill_choices(memory, task="почитать книгу", sequence=seq)

        results = loop._process_identity_detectors()

        pref_results = [
            r for r in results
            if r["category"] == "preference"
        ]
        assert pref_results, "детектор должен найти preference"
        assert pref_results[0]["result"] == "accepted"

        assert outbox.messages, "новое предпочтение должно уйти в outbox"
        msg = outbox.messages[-1]
        assert "перерыв" in msg.lower() or "книг" in msg.lower()
    finally:
        memory.close()


def test_no_duplicate_outbox_on_repeat(tmpdir):
    memory, outbox, loop = _make_loop(tmpdir, "dedup.db")
    try:
        seq = (["read"] * 9) + (["walk"] * 3)
        _fill_choices(memory, task="почитать книгу", sequence=seq)

        loop._process_identity_detectors()
        first_count = len(outbox.messages)
        assert first_count >= 1

        # Повторный проход: preference уже зафиксирована -> no new outbox.
        loop._process_identity_detectors()
        second_count = len(outbox.messages)
        assert second_count == first_count, (
            "повторный detect не должен дублировать outbox-сообщение"
        )
    finally:
        memory.close()


def test_no_outbox_when_disabled(tmpdir):
    db = Path(tmpdir) / "nobox.db"
    memory = Memory(db)
    evidence = EvidenceEngine(memory)
    detector = ActionPreferenceDetector(memory, evidence)
    state = SelfState(Path(tmpdir) / "nobox_self.json")
    manager = IdentityManager(state, memory)

    loop = AgentLoop(
        goal_manager=object(),
        goal_planner=object(),
        action_planner=object(),
        tool_runner=object(),
        task_controller=object(),
        experience_recorder=DummyExpRecorder(memory),
        action_preference_detector=detector,
        habit_pattern_detector=None,
        belief_pattern_detector=None,
        evidence=evidence,
        identity_manager=manager,
        outbox=None,
    )
    try:
        seq = (["read"] * 9) + (["walk"] * 3)
        _fill_choices(memory, task="почитать книгу", sequence=seq)
        results = loop._process_identity_detectors()
        accepted = [
            r for r in results
            if r["category"] == "preference"
            and r["result"] == "accepted"
        ]
        assert accepted, "предпочтение должно промоутиться и без outbox"
    finally:
        memory.close()


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="pref_outbox_")
    test_new_preference_sent_to_outbox(tmpdir)
    test_no_duplicate_outbox_on_repeat(tmpdir)
    test_no_outbox_when_disabled(tmpdir)
    print("ALL OK")
