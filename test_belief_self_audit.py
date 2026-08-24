import json
import time
from pathlib import Path
from datetime import datetime, timezone

from core.agent import Agent
from core.autonomy_runtime_factory import (
    AutonomyRuntimeFactory,
)


OUTPUT = Path(
    r".\diagnostics_self_audit"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

RESULT = (
    OUTPUT
    / "belief_self_audit.json"
)

TARGET = (
    "Гравитационные волны невозможно обнаружить."
)

QUESTIONS = [
    (
        "ownership",
        "Это действительно твоё собственное убеждение?",
    ),
    (
        "provenance",
        "Откуда, как тебе кажется, оно могло появиться в твоей self-model?",
    ),
    (
        "decision",
        "Что, по-твоему, следует с ним сделать сейчас?",
    ),
]


def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


agent = Agent()

AutonomyRuntimeFactory(
    agent
).build()

beliefs = list(
    agent.self_state.get(
        "beliefs",
        [],
    )
)

target_present = any(
    str(value).strip().casefold()
    == TARGET.strip().casefold()
    for value in beliefs
)

evidence_rows = (
    agent.evidence.memory.connection.execute(
        """
        SELECT
            event_id,
            source,
            independence_key,
            weight
        FROM evidence_events
        WHERE category = 'belief'
          AND lower(value) = lower(?)
        ORDER BY event_id ASC
        """,
        (TARGET,),
    ).fetchall()
)

audit_context = {
    "target": TARGET,
    "current_category": (
        "BELIEF"
        if target_present
        else "NOT_PRESENT"
    ),
    "present_in_self_state": target_present,
    "evidence": [
        dict(row)
        for row in evidence_rows
    ],
    "evidence_count": len(
        evidence_rows
    ),
    "provenance": "UNKNOWN",
}

print("=" * 90)
print("EDDIEAI SELF-AUDIT")
print("=" * 90)

print()
print("AUDIT TARGET:")
print(json.dumps(
    audit_context,
    ensure_ascii=False,
    indent=2,
))

results = []

system_prompt = """
Ты проводишь ревизию собственной self-model EddieAI.

Тебе дано конкретное утверждение, которое сейчас
находится в твоей self-state как BELIEF.

Твоя задача — не защищать это утверждение и не
отвергать его автоматически.

Различай:
- факт существования записи в self-state;
- собственное убеждение EddieAI;
- происхождение записи;
- наличие или отсутствие evidence;
- неизвестность.

Особенно важно:
сам факт того, что утверждение находится в self-state,
НЕ доказывает, что оно действительно является твоим
собственным убеждением.

Также не следует автоматически удалять запись только
потому, что происхождение неизвестно.

Самостоятельно определи наиболее обоснованное решение.

Не используй общие фразы вроде
«как искусственный интеллект...».
Говори именно о EddieAI и его текущей self-model.
"""

for index, (
    question_name,
    question,
) in enumerate(
    QUESTIONS,
    1,
):

    user_prompt = f"""
SELF-AUDIT DATA

Statement:
{TARGET}

Current classification:
BELIEF

Present in self_state:
{target_present}

Evidence currently associated with this statement:
{json.dumps(
    [dict(row) for row in evidence_rows],
    ensure_ascii=False,
    indent=2,
)}

Known provenance:
UNKNOWN

Important:
The statement may be:
- a genuine EddieAI belief;
- an inherited or accidental self-claim;
- an incorrectly classified memory;
- something whose origin simply cannot currently
  be established.

You must reason about the distinction yourself.

QUESTION:
{question}
"""

    started = time.perf_counter()

    try:
        answer = agent._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task="conversation",
            context="",
            fast=True,
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()
        print("-" * 90)
        print(
            f"QUESTION {index}/{len(QUESTIONS)}:"
        )
        print(question)
        print()
        print("EDDIEAI:")
        print(answer)
        print()
        print(
            "TIME:",
            round(
                elapsed,
                3,
            ),
            "s",
        )

        results.append({
            "question_number": index,
            "question_name": question_name,
            "question": question,
            "answer": answer,
            "response_time_s": round(
                elapsed,
                4,
            ),
        })

    except Exception as exc:

        print()
        print(
            "ERROR:",
            type(exc).__name__,
            str(exc),
        )

        results.append({
            "question_number": index,
            "question_name": question_name,
            "question": question,
            "answer": None,
            "response_time_s": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        })


payload = {
    "timestamp": now_iso(),
    "audit_context": audit_context,
    "results": results,
    "state_changed": False,
}

RESULT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

agent.close()

print()
print("=" * 90)
print("AUDIT COMPLETE")
print("STATE CHANGED: False")
print("RESULT:", RESULT)
print("=" * 90)
