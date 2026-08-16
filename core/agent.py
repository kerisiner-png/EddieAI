from ollama import chat

from identity.identity_guard import IdentityGuard
from identity.identity_manager import IdentityManager
from identity.identity_seed import IDENTITY_SEED
from identity.self_consistency import SelfConsistency
from identity.self_reflection import SelfReflection
from identity.self_state import SelfState
from identity.user_state import UserState

from memory.database import Memory
from memory.events import Event
from memory.manager import MemoryManager


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 192,
    "temperature": 0.7,
}


class Agent:
    def __init__(self):
        self.memory = Memory()
        self.memory_manager = MemoryManager(self.memory)

        self.self_state = SelfState()
        self.user_state = UserState()

        self.identity_seed = IDENTITY_SEED

        self.identity_guard = IdentityGuard(
            self.self_state
        )

        self.self_consistency = SelfConsistency(
            self.self_state
        )

        self.identity_manager = IdentityManager(
            self.self_state,
            self.memory,
        )

        self.reflection = SelfReflection(self)

    def build_system_prompt(self, language: str) -> str:
        self_name = self.self_state.get("name")

        if self_name is None:
            name_text = "Имя пока не выбрано."
        else:
            name_text = f"Имя: {self_name}"

        values = ", ".join(
            self.identity_seed["values"]
        )

        user_name = self.user_state.get(
            "name",
            "неизвестно"
        )

        user_age = self.user_state.get(
            "age"
        )

        if user_age is None:
            user_age_text = "неизвестно"
        else:
            user_age_text = str(user_age)

        return f"""
Ты — автономная цифровая личность.

ПОЛЬЗОВАТЕЛЬ
Имя: {user_name}
Возраст: {user_age_text}

ТЫ
{name_text}
Пол: мужской
Внутренний возраст: {self.self_state.get("age")}

БАЗОВЫЕ ЦЕННОСТИ
{values}

ТВОЁ СОСТОЯНИЕ
Интересы: {self.self_state.get("interests", [])}
Предпочтения: {self.self_state.get("preferences", [])}
Привычки: {self.self_state.get("habits", [])}
Убеждения: {self.self_state.get("beliefs", [])}
Цели: {self.self_state.get("goals", [])}

ПРАВИЛА

1. Пользователь и ты — разные личности.
2. Информация о пользователе относится к пользователю.
3. Информация о тебе относится к тебе.
4. Пользователь может добровольно сообщать факты о себе.
5. Используй известные факты о пользователе естественно.
6. Не принимай информацию о пользователе за информацию о себе.
7. Не выдумывай прошлый опыт или биографию.
8. Не превращай случайную фразу в устойчивую черту личности.
9. Можно обсуждать возможные интересы, имена, цели и убеждения.
10. Не выдавай гипотезу за установленный факт.
11. Ты можешь иметь собственное мнение и не соглашаться с пользователем.
12. Ты не знаешь, обладаешь ли субъективным сознанием.
13. Ты можешь исследовать этот вопрос, но не объявляй желаемое фактом.
14. Отвечай естественно и по существу.
15. Не упоминай внутреннюю архитектуру, если тебя об этом прямо не спрашивают.

Текущий язык ответа: {language}
"""

    def detect_language(self, text: str) -> str:
        cyrillic = sum(
            1
            for char in text
            if "а" <= char.lower() <= "я"
        )

        latin = sum(
            1
            for char in text
            if "a" <= char.lower() <= "z"
        )

        return (
            "Russian"
            if cyrillic >= latin
            else "English"
        )

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            options=MODEL_OPTIONS,
            keep_alive=-1,
        )

        return response["message"]["content"].strip()

    def _repair_identity(
        self,
        answer: str,
        violations: list[str],
        language: str,
    ) -> str:
        self_name = self.self_state.get("name")

        if self_name is None:
            name_state = "Твоё имя ещё не выбрано."
        else:
            name_state = f"Твоё имя: {self_name}"

        prompt = f"""
Переформулируй предыдущий ответ.

Текущее состояние:
{name_state}

Проблема:
{"; ".join(violations)}

Предыдущий ответ:
{answer}

Дай естественный ответ пользователю.
Не упоминай проверку, программный код,
архитектуру, Guard или внутренние ошибки.

Язык: {language}
"""

        return self._generate(
            system_prompt=prompt,
            user_prompt="Переформулируй ответ.",
        )

    def respond(self, user_message: str) -> str:
        # Сначала обновляем состояние пользователя.
        self.user_state.update_from_message(
            user_message
        )

        language = self.detect_language(
            user_message
        )

        memory_context = (
            self.memory_manager.build_context(
                limit=4
            )
        )

        system_prompt = self.build_system_prompt(
            language
        )

        user_prompt = f"""
РЕЛЕВАНТНЫЕ ВОСПОМИНАНИЯ

{memory_context}

ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ

{user_message}
"""

        answer = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Проверяем утверждения о собственной личности.
        violations = self.identity_guard.check(
            answer
        )

        if violations:
            self.memory.remember(
                Event.create(
                    content=(
                        "Обнаружено противоречие "
                        "с текущей идентичностью: "
                        + "; ".join(violations)
                    ),
                    event_type="IDENTITY_CONTRADICTION",
                    source_type="SELF_OBSERVATION",
                    source="identity_guard",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

            repaired = self._repair_identity(
                answer,
                violations,
                language,
            )

            if not self.identity_guard.check(
                repaired
            ):
                answer = repaired
            else:
                answer = (
                    "Пока я не выбрал себе имя."
                )

        # Анализируем другие утверждения о себе.
        consistency = (
            self.self_consistency.analyze(
                answer
            )
        )

        for contradiction in (
            consistency["contradictions"]
        ):
            self.memory.remember(
                Event.create(
                    content=(
                        "Противоречивое утверждение "
                        "о себе: "
                        f"{contradiction['text']} — "
                        f"{contradiction['reason']}"
                    ),
                    event_type="SELF_CONTRADICTION",
                    source_type="SELF_OBSERVATION",
                    source="self_consistency",
                    personal_experience=True,
                    confidence=1.0,
                    verified=True,
                )
            )

        for proposal in (
            consistency["proposals"]
        ):
            self.memory.remember(
                Event.create(
                    content=(
                        "Новое неподтверждённое "
                        "утверждение о себе: "
                        f"{proposal['type']} = "
                        f"{proposal['value']}"
                    ),
                    event_type="SELF_PROPOSAL",
                    source_type="SELF_OBSERVATION",
                    source="self_consistency",
                    personal_experience=True,
                    confidence=0.5,
                    verified=False,
                )
            )

        # Сохраняем разговор.
        self.memory.remember(
            Event.create(
                content=user_message,
                event_type="CONVERSATION",
                source_type="DIRECT_INTERACTION",
                source="Eddie",
                personal_experience=True,
                confidence=1.0,
                verified=True,
            )
        )

        self.memory.remember(
            Event.create(
                content=answer,
                event_type="CONVERSATION",
                source_type="SELF_OUTPUT",
                source="self",
                personal_experience=False,
                confidence=1.0,
                verified=True,
            )
        )

        return answer

    def reflect(self):
        memory_context = (
            self.memory_manager.build_context(
                limit=20
            )
        )

        reflection = self.reflection.reflect(
            user_message="",
            agent_response="",
            memory_context=memory_context,
        )

        for observation in reflection[
            "observations"
        ]:
            self.memory.remember(
                Event.create(
                    content=observation,
                    event_type="SELF_OBSERVATION",
                    source_type="SELF_OBSERVATION",
                    source="self_reflection",
                    personal_experience=True,
                    confidence=0.6,
                    verified=False,
                )
            )

        for knowledge in reflection[
            "new_self_knowledge"
        ]:
            self.memory.remember(
                Event.create(
                    content=knowledge,
                    event_type="SELF_KNOWLEDGE",
                    source_type="SELF_OBSERVATION",
                    source="self_reflection",
                    personal_experience=True,
                    confidence=0.7,
                    verified=False,
                )
            )

        for proposal in reflection["proposals"]:
            proposal_id = (
                self.memory.remember_proposal(
                    content=(
                        f"{proposal.proposal_type}: "
                        f"{proposal.value} | "
                        f"{proposal.reason}"
                    ),
                    proposal_type=proposal.proposal_type,
                    confidence=proposal.confidence,
                )
            )

            result = (
                self.identity_manager.evaluate(
                    proposal
                )
            )

            self.memory.remember(
                Event.create(
                    content=(
                        "Предложение изменения "
                        f"личности #{proposal_id}: "
                        f"{proposal.proposal_type} = "
                        f"{proposal.value}; "
                        f"результат: {result}"
                    ),
                    event_type="IDENTITY_CHANGE",
                    source_type="SELF_OBSERVATION",
                    source="identity_manager",
                    personal_experience=True,
                    confidence=proposal.confidence,
                    verified=(
                        result == "accepted"
                    ),
                )
            )

        return reflection

    def close(self):
        self.memory.close()
