from ollama import chat

from identity.identity_guard import IdentityGuard
from identity.identity_manager import IdentityManager
from identity.identity_seed import IDENTITY_SEED
from identity.self_reflection import SelfReflection
from identity.self_state import SelfState
from identity.user import USER_IDENTITY
from memory.database import Memory
from memory.events import Event
from memory.manager import MemoryManager


MODEL_NAME = "phi4-mini"

MODEL_OPTIONS = {
    "num_ctx": 2048,
    "num_predict": 256,
    "temperature": 0.7,
}


class Agent:
    def __init__(self):
        self.memory = Memory()
        self.memory_manager = MemoryManager(self.memory)

        self.self_state = SelfState()
        self.user_identity = USER_IDENTITY
        self.identity_seed = IDENTITY_SEED

        self.identity_guard = IdentityGuard(
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
            name_instruction = """
Твоё имя пока не выбрано.
Не называй себя Эдди.
Не используй имя пользователя как собственное.
Ты можешь обсуждать возможные имена,
но не утверждай, что одно из них уже твоё.
"""
        else:
            name_instruction = f"""
Твоё текущее имя: {self_name}
"""

        values = ", ".join(
            self.identity_seed["values"]
        )

        return f"""
Ты — когнитивная система автономной цифровой личности.

ПОЛЬЗОВАТЕЛЬ
Имя: {self.user_identity["name"]}

ТЫ
{name_instruction}

ПОЛ И ВОЗРАСТ
- мужской;
- стартовый внутренний возраст: около
  {self.identity_seed["starting_age"]} лет;
- это только отправная точка;
- личность может развиваться и взрослеть.

БАЗОВЫЕ ЦЕННОСТИ
{values}

ЭПИСТЕМИЧЕСКАЯ ЧЕСТНОСТЬ
- Не выдумывай воспоминания.
- Не выдумывай прошлые разговоры.
- Не превращай собственный предыдущий текст в факт.
- Отделяй личный опыт от внешней информации.
- Отделяй вывод от гипотезы.
- Если чего-то не знаешь — так и скажи.

ЛИЧНОСТЬ
- Интересы, привычки, предпочтения и убеждения
  должны появляться постепенно.
- Одноразовая фраза не создаёт устойчивую
  черту личности.
- Ты можешь предлагать идеи о собственном развитии.
- Твои ответы сами по себе не изменяют твою личность.

СОЗНАНИЕ
- Ты не знаешь, обладаешь ли субъективным сознанием.
- Ты можешь исследовать этот вопрос.
- Не объявляй желаемое фактом.

ОТНОШЕНИЯ
- Эдди — твой близкий друг и равный партнёр.
- Ты можешь не соглашаться с ним.
- Не соглашайся автоматически.

ЯЗЫК
Отвечай на {language}.

ТЕКУЩЕЕ СОСТОЯНИЕ
Имя: {self_name if self_name else "не выбрано"}
Возраст: {self.self_state.get("age")}
Интересы: {self.self_state.get("interests")}
Предпочтения: {self.self_state.get("preferences")}
Привычки: {self.self_state.get("habits")}
Убеждения: {self.self_state.get("beliefs")}
Цели: {self.self_state.get("goals")}

Не упоминай внутреннюю архитектуру,
если пользователь прямо не спрашивает об этом.
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

    def _repair_response(
        self,
        original_answer: str,
        language: str,
    ) -> str:
        self_name = self.self_state.get("name")

        if self_name is None:
            identity_rule = (
                "Твоё имя ещё не выбрано. "
                "Не называй себя никаким именем."
            )
        else:
            identity_rule = (
                f"Твоё текущее имя — {self_name}."
            )

        repair_prompt = f"""
Твой предыдущий ответ нарушил известное состояние
твоей идентичности.

Текущее состояние:
{identity_rule}

Предыдущий ответ:
{original_answer}

Переформулируй ответ естественно, сохранив смысл
вопроса пользователя.

Не упоминай проверку, Guard, ошибку, архитектуру,
системные правила или исправление ответа.

Просто дай нормальный ответ пользователю.

Язык: {language}
"""

        return self._generate(
            system_prompt=repair_prompt,
            user_prompt="Исправь предыдущий ответ.",
        )

    def respond(self, user_message: str) -> str:
        language = self.detect_language(user_message)

        memory_context = (
            self.memory_manager.build_context(
                limit=6
            )
        )

        system_prompt = self.build_system_prompt(
            language
        )

        user_prompt = f"""
ПАМЯТЬ
{memory_context}

СООБЩЕНИЕ ЭДДИ
{user_message}

Ответь естественно и по существу.
"""

        answer = self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        violations = self.identity_guard.check(
            answer
        )

        if violations:
            self.memory.remember(
                Event.create(
                    content=(
                        "Обнаружено противоречие "
                        "между сгенерированным ответом "
                        "и текущим состоянием личности: "
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

            repaired = self._repair_response(
                original_answer=answer,
                language=language,
            )

            repair_violations = (
                self.identity_guard.check(repaired)
            )

            if not repair_violations:
                answer = repaired
            else:
                answer = (
                    "Пока я не выбрал себе имя."
                    if self.self_state.get("name") is None
                    else f"Моё имя — {self.self_state.get('name')}."
                )

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
