from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingPlan:
    """
    Решает, какие подсистемы действительно нужны
    для обработки текущего сообщения.

    Это не ответ и не reasoning.
    Это только план вычислений.
    """

    route: str

    affective_appraisal: bool
    affective_dialogue: bool
    quick_reflex: bool

    autonomy: bool
    direct_knowledge: bool

    reasoning: bool
    epistemic: bool

    self_context: bool
    persistent_conclusion: bool
    reconsider_conclusion: bool
    self_observation: bool

    claim_audit: bool
    self_consistency: bool

    reason: str


def build_processing_plan(
    *,
    message: str,
    route: str,
    cognitive_mode: str,
    has_persistent_conclusion: bool = False,
    conclusion_relevant: bool | None = None,
) -> ProcessingPlan:

    text = (
        str(message)
        .strip()
        .lower()
    )

    quick_phrases = {
        "привет",
        "здравствуй",
        "здравствуйте",
        "доброе утро",
        "добрый день",
        "добрый вечер",
        "как дела",
        "как ты",
        "окей",
        "ок",
        "понятно",
        "ясно",
        "спасибо",
        "спс",
        "хорошо",
        "ладно",
        "да",
        "нет",
    }

    trivial = (
        route == "GENERAL_QUERY"
        and (
            text in quick_phrases
            or len(text.split()) <= 3
        )
        and cognitive_mode == "QUICK"
    )

    if trivial:
        return ProcessingPlan(
            route=route,

            affective_appraisal=True,
            affective_dialogue=False,
            quick_reflex=True,

            autonomy=False,
            direct_knowledge=False,

            reasoning=False,
            epistemic=False,

            self_context=False,
            persistent_conclusion=False,
            reconsider_conclusion=False,
            self_observation=False,

            claim_audit=False,
            self_consistency=False,

            reason="trivial_message",
        )

    if route == "SELF_QUERY":
        reconsider_markers = (
            "почему",
            "зачем",
            "как ты пришёл",
            "как ты пришел",
            "на чём основано",
            "на чем основано",
            "какие у тебя основания",
            "какие у тебя доказательства",
            "откуда ты это узнал",
            "откуда ты это знаешь",
            "ты уверен",
            "насколько ты уверен",
            "ты сам так решил",
            "это твой вывод",
            "это твоё убеждение",
            "это твое убеждение",
            "ты можешь пересмотреть",
            "ты можешь изменить",
            "ты согласен со своим выводом",
            "ты согласен со своим предыдущим выводом",
            "ты согласен с ним",
            "ты согласен с этим выводом",
            "ты всё ещё так считаешь",
            "ты все еще так считаешь",
            "ты всё ещё думаешь так",
            "ты все еще думаешь так",
            "ты всё ещё придерживаешься",
            "ты все еще придерживаешься",
            "ты изменил своё мнение",
            "ты изменил свое мнение",
            "ты поменял мнение",
            "ты передумал",
            "ты передумала",
            "ты пересмотрел свой вывод",
            "ты пересмотрела свой вывод",
        )

        needs_reconsideration = (
            has_persistent_conclusion
            and cognitive_mode == "DEEP"
            and any(
                marker in text
                for marker in reconsider_markers
            )
        )

        use_persistent = (
            has_persistent_conclusion
            and (
                conclusion_relevant
                is not False
            )
            and cognitive_mode == "DEEP"
            and not needs_reconsideration
        )

        return ProcessingPlan(
            route=route,

            affective_appraisal=True,
            affective_dialogue=True,
            quick_reflex=False,

            autonomy=False,
            direct_knowledge=False,

            reasoning=(
                cognitive_mode == "DEEP"
                and (
                    not use_persistent
                    or needs_reconsideration
                )
            ),
            epistemic=True,

            self_context=True,
            persistent_conclusion=use_persistent,
            reconsider_conclusion=(
                needs_reconsideration
            ),
            self_observation=(
                cognitive_mode == "DEEP"
                and (
                    not use_persistent
                    or needs_reconsideration
                )
            ),

            claim_audit=(
                cognitive_mode == "DEEP"
            ),
            self_consistency=(
                cognitive_mode == "DEEP"
            ),

            reason="self_query",
        )

    if cognitive_mode == "DEEP":
        return ProcessingPlan(
            route=route,

            affective_appraisal=True,
            affective_dialogue=True,
            quick_reflex=False,

            autonomy=True,
            direct_knowledge=True,

            reasoning=True,
            epistemic=True,

            self_context=False,
            persistent_conclusion=False,
            reconsider_conclusion=False,
            self_observation=False,

            claim_audit=False,
            self_consistency=False,

            reason="deep_message",
        )

    return ProcessingPlan(
        route=route,

        affective_appraisal=True,  # Always true for autonomy
        affective_dialogue=True,
        quick_reflex=True,

        autonomy=True,
        direct_knowledge=True,

        reasoning=False,
        epistemic=True,

        self_context=False,
        persistent_conclusion=False,
        reconsider_conclusion=False,
        self_observation=False,

        claim_audit=False,
        self_consistency=False,

        reason="normal_conversation",
    )



