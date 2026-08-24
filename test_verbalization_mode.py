from copy import deepcopy

from core.agent import Agent
from core.autonomy_runtime_factory import AutonomyRuntimeFactory


agent = Agent()
AutonomyRuntimeFactory(agent).build()

store = agent.self_conclusion_store

original_store = deepcopy(
    agent.self_state.get(
        store.KEY,
        {},
    )
)

original_legacy = deepcopy(
    agent.self_state.get(
        "self_conclusion_state",
        {},
    )
)

try:
    # --------------------------------------------------------
    # CONTROLLED CONCLUSION
    # --------------------------------------------------------

    agent.self_state.set(
        store.KEY,
        {},
    )

    store._ensure()

    store.save(
        topic="self_concept",
        conclusion=(
            "Я считаю, что способен формировать "
            "собственные выводы, но их надёжность "
            "зависит от доступных мне данных "
            "и качества их проверки."
        ),
        confidence=0.86,
        basis=[
            "self_reflection",
            "epistemic_audit",
        ],
        provenance=[
            "COGNITIVE_REASONER",
            "EPISTEMIC_AUDIT",
        ],
        predicates=[
            "self_conclusion",
            "self_reflection",
        ],
    )

    print("=" * 80)
    print("STORED CONCLUSION")
    print(
        store.get(
            "self_concept"
        )["conclusion"]
    )

    # --------------------------------------------------------
    # FIRST VERBALIZATION
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("FIRST QUESTION")

    answer_1 = agent.respond(
        "Что ты думаешь о себе?"
    )

    print()
    print(answer_1)

    # --------------------------------------------------------
    # SECOND VERBALIZATION
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("SECOND QUESTION")

    answer_2 = agent.respond(
        "Что ты думаешь о себе?"
    )

    print()
    print(answer_2)

    # --------------------------------------------------------
    # BASIC SAFETY CHECKS
    # --------------------------------------------------------

    forbidden_meta = (
        "confidence",
        "provenance",
        "basis",
        "revision_count",
        "cognitive reasoner",
        "cognitive_reasoner",
        "self_conclusion_store",
        "self_state",
        "store",
    )

    combined = (
        answer_1
        + "\n"
        + answer_2
    ).casefold()

    for item in forbidden_meta:
        assert item not in combined, (
            "Verbalizer leaked internal metadata: "
            + item
        )

    # The answer should actually contain the
    # semantic core of the stored conclusion.
    semantic_markers = (
        "вывод",
        "решени",
        "данн",
        "провер",
        "счита",
        "формир",
    )

    assert any(
        marker in combined
        for marker in semantic_markers
    ), (
        "Verbalization does not appear to preserve "
        "the stored conclusion."
    )

    print()
    print("=" * 80)
    print("PASS")

finally:
    agent.self_state.set(
        store.KEY,
        original_store,
    )

    agent.self_state.set(
        "self_conclusion_state",
        original_legacy,
    )

    agent.close()
