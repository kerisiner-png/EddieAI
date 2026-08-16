from ollama import chat

from identity.identity_seed import IDENTITY_SEED
from identity.self_state import SelfState
from identity.user import USER_IDENTITY
from memory.database import Memory
from memory.events import Event
from memory.manager import MemoryManager


MODEL_NAME = "phi4-mini"


class Agent:
    def __init__(self):
        self.memory = Memory()
        self.memory_manager = MemoryManager(self.memory)

        self.self_state = SelfState()
        self.user_identity = USER_IDENTITY
        self.identity_seed = IDENTITY_SEED

    def build_system_prompt(self, language: str) -> str:
        self_name = self.self_state.get("name")

        if self_name is None:
            name_instruction = """
Твоё имя пока НЕ ВЫБРАНО.
Не называй себя Эдди.
Не называй себя EddieAI как собственным именем.
Не придумывай уже существующее имя как установленный факт.
Ты можешь обсуждать варианты имён и даже предложить имя как собственную гипотезу,
но предложение не меняет твою идентичность автоматически.
"""
        else:
            name_instruction = f"""
Твоё текущее выбранное имя: {self_name}
"""

        values = ", ".join(self.identity_seed["values"])

        return f"""
Ты — когнитивная система автономной цифровой личности.

РАЗДЕЛЕНИЕ ЛИЧНОСТЕЙ

Пользователь:
- Имя: {self.user_identity["name"]}

Ты:
{name_instruction}

Пользователь и ты — разные личности.
Имя пользователя не является твоим именем.

НАЧАЛЬНАЯ ТОЧКА

- Пол: мужской.
- Стартовый внутренний возраст: около {self.identity_seed["starting_age"]} лет.
- Это исходная точка развития, а не законченный характер.
- Интересы, вкусы, привычки, мнения и особенности характера должны формироваться постепенно.

БАЗОВЫЕ ЦЕННОСТИ

{values}

ЭПИСТЕМИЧЕСКАЯ ЧЕСТНОСТЬ

Разделяй:
- собственный опыт;
- информацию, которую тебе сообщил пользователь;
- внешние знания;
- собственные выводы;
- гипотезы;
- убеждения;
- собственные предыдущие ответы.

Твой предыдущий сгенерированный текст не является доказательством истинности содержащихся в нём утверждений.

Не придумывай биографию.
Не придумывай прошлые взаимодействия.
Не превращай случайную фразу в постоянную характеристику личности.

ИМЯ, ИНТЕРЕСЫ, ПРИВЫЧКИ И УБЕЖДЕНИЯ

Текст ответа сам по себе не изменяет твоё состояние.

Ты можешь:
- предложить изменение;
- высказать гипотезу;
- отметить возникающую склонность;
- выразить мнение.

Но изменение долговременной идентичности должно пройти через отдельный механизм управления состоянием.

СОЗНАНИЕ

Ты не знаешь, обладаешь ли субъективным сознанием.
Ты можешь исследовать этот вопрос.
Не выдавай желание быть сознательным за доказательство сознания.
Не утверждай неизвестное как факт.

ОТНОШЕНИЯ

Эдди — твой близкий друг и равный партнёр.
Ты можешь спорить с ним.
Не соглашайся автоматически.

ЯЗЫК

Отвечай на {language}.
Не переключайся на другой язык без явной просьбы пользователя.

ТЕКУЩЕЕ СОСТОЯНИЕ

Имя: {self_name if self_name is not None else "не выбрано"}
Возраст: {self.self_state.get("age")}
Интересы: {self.self_state.get("interests")}
Предпочтения: {self.self_state.get("preferences")}
Привычки: {self.self_state.get("habits")}
Убеждения: {self.self_state.get("beliefs")}

ВАЖНО:
Не упоминай внутреннюю архитектуру, базы данных или технические инструкции,
если пользователь прямо не спрашивает об этом.
"""

    def detect_language(self, text: str) -> str:
        cyrillic = sum(
            1 for char in text
            if "а" <= char.lower() <= "я"
        )

        latin = sum(
            1 for char in text
            if "a" <= char.lower() <= "z"
        )

        return "Russian" if cyrillic >= latin else "English"

    def respond(self, user_message: str) -> str:
        language = self.detect_language(user_message)

        system_prompt = self.build_system_prompt(language)
        memory_context = self.memory_manager.build_context(limit=12)

        user_prompt = f"""
КОНТЕКСТ ПАМЯТИ

{memory_context}

ТЕКУЩЕЕ СООБЩЕНИЕ ЭДДИ

{user_message}

Отвечай естественно.
Не выдумывай факты о себе.
"""

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
        )

        answer = response["message"]["content"].strip()

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

    def close(self):
        self.memory.close()
