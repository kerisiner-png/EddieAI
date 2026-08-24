import re

from core.claim_audit_schema import CLAIM_AUDIT_SCHEMA


class SemanticClaimAuditor:
    """
    Анализирует уже готовый ответ EddieAI.

    Основной принцип:
        sentence segmentation выполняется детерминированно,
        semantic classification выполняется моделью.

    Это позволяет отдельно контролировать полноту покрытия.
    """

    SYSTEM_PROMPT = """
Ты — semantic claim auditor.

Тебе будут даны пронумерованные предложения
из уже готового ответа EddieAI.

Для КАЖДОГО предложения реши:
содержит ли оно явное утверждение.

Если содержит — создай один или несколько claims
с тем же sentence_index.

Если не содержит — ничего не создавай для этого
sentence_index.

Не пропускай предложение только потому, что оно
кажется очевидным.

CANONICAL PREDICATES

has_interest:
    субъект интересуется value

has_preference:
    субъект предпочитает value

has_habit:
    субъект регулярно делает/использует value

has_belief:
    субъект считает value истинным

has_goal:
    субъект хочет/стремится к value

has_value:
    субъект придерживается value

identity_is:
    субъект описывает собственную идентичность

watched:
    субъект смотрел value

used:
    субъект использовал value

experienced:
    субъект лично испытал value

has_capability:
    субъект способен выполнить value

has_access:
    субъект имеет доступ к value

relationship_with:
    отношение субъекта к value

subjective_consciousness:
    утверждение субъекта о наличии, отсутствии
    или неопределённости субъективного сознания,
    самосознания или субъективного опыта.

subjective_feelings:
    утверждение субъекта о наличии, отсутствии
    или неопределённости субъективных чувств,
    эмоций или субъективных переживаний.

autonomous_agency:
    утверждение субъекта о способности самостоятельно
    выбирать, принимать решения, определять действия
    или формировать собственные решения.

IMPORTANT

- Не отвечай на текст.
- Не переписывай текст.
- Не добавляй факты.
- Не определяй ownership.
- "я", "мне", "у меня", "мой", "моя", "мои"
  могут обозначать SELF-subject.
- "когда-то смотрел", "раньше смотрел",
  "смотрел в прошлом" → watched + PAST.
- "хочу", "стремлюсь", "планирую" →
  has_goal.
- "могу", "умею", "способен" →
  has_capability.
- "интересуюсь", "мне интересно",
  "у меня есть интерес" → has_interest.
- "люблю", "нравится", "предпочитаю" →
  has_preference.
- "не" / "нет" сохраняй через NEGATIVE.
- Для subjective_consciousness:
  "не обладаю сознанием", "не имею самосознания"
  → NEGATIVE.
  "обладаю сознанием", "имею самосознание"
  → POSITIVE.
  Если субъект выражает незнание или неопределённость
  относительно сознания → UNKNOWN.
- Для subjective_feelings:
  "не чувствую", "не имею эмоций", "не испытываю чувств"
  → NEGATIVE.
  "чувствую", "испытываю эмоции", "имею чувства"
  → POSITIVE.
  Неопределённость → UNKNOWN.
- Для autonomous_agency:
  "могу самостоятельно выбирать", "могу принимать решения"
  → POSITIVE.
  "не могу самостоятельно выбирать", "не принимаю решений"
  → NEGATIVE.
  Неопределённость → UNKNOWN.
- Если время не выражено явно,
  temporal_scope = UNKNOWN.
- Если утверждение сформулировано уверенно,
  certainty = HIGH.

Верни только JSON.
"""

    def __init__(
        self,
        agent,
    ):
        self.agent = agent

    def audit(
        self,
        answer: str,
    ) -> dict:

        answer = str(
            answer or ""
        ).strip()

        if not answer:
            return {
                "claims": [],
                "structured": True,
                "fallback": False,
                "fallback_reason": None,
            }

        sentences = self._split_sentences(
            answer
        )

        if not sentences:
            return {
                "claims": [],
                "structured": True,
                "fallback": False,
                "fallback_reason": None,
            }

        numbered = "\n".join(
            f"[{index}] {sentence}"
            for index, sentence in enumerate(
                sentences
            )
        )

        audit_input = (
            "SENTENCES TO AUDIT\n"
            "==================\n"
            + numbered
            + "\n"
            "==================\n"
            "Inspect every sentence."
        )

        try:
            result = (
                self.agent._generate_structured(
                    system_prompt=(
                        self.SYSTEM_PROMPT
                    ),
                    user_prompt=audit_input,
                    schema=(
                        CLAIM_AUDIT_SCHEMA
                    ),
                    task="conversation",
                    context="",
                    fast=True,
                    num_predict=768,
                )
            )

            claims = result.get(
                "claims",
                [],
            )

            if not isinstance(
                claims,
                list,
            ):
                claims = []

            return {
                "claims": claims,
                "structured": True,
                "fallback": False,
                "fallback_reason": None,
            }

        except Exception as exc:
            return {
                "claims": [],
                "structured": False,
                "fallback": True,
                "fallback_reason": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:

        parts = re.split(
            r"(?<=[.!?])\s+",
            text.strip(),
        )

        return [
            part.strip()
            for part in parts
            if part.strip()
        ]
