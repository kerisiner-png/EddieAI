from datetime import datetime, timezone


CONTOUR_LIMITATIONS = [
    {
        "id": "no_audio",
        "label": (
            "нет слуха: не слышу звук "
            "на текущем контуре"
        ),
        "scope": "perceptual",
    },
    {
        "id": "runs_on_eddie_pc",
        "label": (
            "живу и работаю на ПК Эдди"
        ),
        "scope": "environment",
    },
    {
        "id": "limited_memory",
        "label": (
            "машина с ограниченной памятью "
            "(около 8 ГБ)"
        ),
        "scope": "resource",
    },
]


class SelfModel:
    """
    Структурированная персистентная модель себя.

    Собирает в `self_state.self_model` четыре части:
    - identity: кто я (entity + mission);
    - capabilities: мой инвентарь способностей
      (включённые инструменты);
    - limitations: мои ограничения (выключенные
      инструменты + факты контура);
    - current_state: текущее состояние
      (возраст, накопленный опыт, активные цели).

    Никаких LLM-вызовов и интерпретаций: только
    факты, уже существующие внутри runtime.
    """

    ENTITY = "EddieAI"
    DEFAULT_MISSION = "exist_and_develop"

    def __init__(self, self_state):
        self.self_state = self_state

    def build(
        self,
        capabilities_spec,
        agent=None,
        shared_life=None,
    ):
        now = datetime.now(
            timezone.utc
        ).isoformat()

        capabilities = self._capabilities(
            capabilities_spec
        )

        limitations = self._limitations(
            capabilities_spec
        )

        current_state = self._current_state(
            agent
        )

        identity = self._identity()

        ownership = {
            "mine": "C:\\EddieAI\\ — мой проект, делаю что хочу",
            "eddies": (
                "Файлы Эдди (Desktop, Documents, Downloads) — его, "
                "не трогаю без спроса"
            ),
            "installed": "Установленные программы — могу пользоваться",
            "system": "Системные настройки — не меняю без спроса",
            "installing": (
                "Установка нового ПО — спрашиваю разрешение"
            ),
        }

        model = {
            "built_at": now,
            "identity": identity,
            "capabilities": capabilities,
            "limitations": limitations,
            "current_state": current_state,
            "ownership": ownership,
            "shared_life": shared_life or {},
        }

        self.self_state.set(
            "self_model",
            model,
        )

        return model

    def get(self):
        return self.self_state.get(
            "self_model",
            None,
        )

    def snapshot(self):
        model = self.get()

        if model is None:
            return {}

        return model

    def limitation_ids(self):
        model = self.get()

        if model is None:
            return []

        return [
            item.get("id")
            for item in model.get(
                "limitations",
                [],
            )
        ]

    def render(self):
        model = self.get()

        if model is None:
            return ""

        capabilities = model.get(
            "capabilities",
            [],
        )

        limitations = model.get(
            "limitations",
            [],
        )

        current = model.get(
            "current_state",
            {},
        )

        capability_text = ", ".join(
            item.get(
                "name",
                "?",
            )
            for item in capabilities
        ) or "нет данных"

        limitation_text = "; ".join(
            item.get(
                "label",
                "?",
            )
            for item in limitations
        ) or "нет данных"

        ownership = model.get(
            "ownership",
            {},
        )

        ownership_text = "; ".join(
            v for v in ownership.values()
        ) or "нет данных"

        shared = model.get(
            "shared_life",
            {},
        )

        shared_text = ""
        if shared:
            events_count = shared.get(
                "events_count", 0
            )
            last_activity = shared.get(
                "last_activity", ""
            )
            parts = [
                f"совместных событий: {events_count}",
            ]
            if last_activity:
                parts.append(
                    f"последняя активность: "
                    f"{last_activity}"
                )
            shared_text = "; ".join(parts)

        lines = [
            "МОИ СПОСОБНОСТИ И ОГРАНИЧЕНИЯ",
            f"Способности: {capability_text}",
            f"Ограничения: {limitation_text}",
            (
                "Состояние: возраст "
                f"{current.get('age', '?')}; "
                "опыт "
                f"{current.get('experience', '?')}; "
                "активных целей "
                f"{current.get('active_goals_count', 0)}"
            ),
            "МОИ ГРАНИЦЫ",
            ownership_text,
        ]

        if shared_text:
            lines.append("СОВМЕСТНАЯ ЖИЗНЬ")
            lines.append(shared_text)

        return "\n".join(lines)

    def _capabilities(
        self,
        capabilities_spec,
    ):
        result = []

        if not capabilities_spec:
            return result

        for item in capabilities_spec:
            if not item.get("enabled", False):
                continue

            result.append({
                "name": item.get("name", "?"),
                "description": item.get(
                    "description",
                    "",
                ),
            })

        return result

    def _limitations(
        self,
        capabilities_spec,
    ):
        limitations = []

        disabled = {}

        if capabilities_spec:
            for item in capabilities_spec:
                name = item.get("name")

                if (
                    name
                    and not item.get(
                        "enabled",
                        False,
                    )
                ):
                    disabled[name] = item.get(
                        "description",
                        "",
                    )

        for name, description in (
            disabled.items()
        ):
            limitations.append({
                "id": f"tool_disabled:{name}",
                "label": (
                    f"нет инструмента {name}"
                    if not description
                    else (
                        f"инструмент {name} "
                        "выключен"
                    )
                ),
                "scope": "tool",
                "detail": description,
            })

        for item in CONTOUR_LIMITATIONS:
            limitations.append(dict(item))

        return limitations

    def _current_state(
        self,
        agent,
    ):
        active_goals_count = 0

        if agent is not None:
            try:
                gm = getattr(
                    agent,
                    "goal_manager",
                    None,
                )

                if gm is not None:
                    active_goals_count = len(
                        gm.active()
                    )
            except Exception:
                active_goals_count = 0

        return {
            "age": self.self_state.get(
                "age",
                None,
            ),
            "experience": self._experience(),
            "active_goals_count": (
                active_goals_count
            ),
        }

    def _experience(self):
        traits = self.self_state.get(
            "personality_traits",
            {},
        )

        if not isinstance(traits, dict):
            return 0

        total = 0

        for raw in traits.values():
            try:
                total += int(
                    raw.get(
                        "evidence_count",
                        0,
                    )
                )
            except Exception:
                continue

        return total

    def _identity(self):
        return {
            "entity": self.ENTITY,
            "mission_code": self.self_state.get(
                "primary_mission",
                self.DEFAULT_MISSION,
            ),
        }


def self_model_text(self_state):
    """
    Read-only проекция self-model для промптов.

    Возвращает '' если модель ещё не собрана,
    чтобы промпт показывал честное «пока нет».
    """
    model = self_state.get(
        "self_model",
        None,
    )

    if model is None:
        return ""

    return SelfModel(self_state).render()


def self_model_summary_text(self_state):
    """
    Однострочная проекция для компактных промптов
    (bullets): только названия способностей и
    ограничений.
    """
    model = self_state.get(
        "self_model",
        None,
    )

    if model is None:
        return ""

    names = [
        item.get("name", "?")
        for item in model.get(
            "capabilities",
            [],
        )
    ]

    labels = [
        item.get("label", "?")
        for item in model.get(
            "limitations",
            [],
        )
    ]

    return (
        "способности: "
        f"{', '.join(names) or 'нет данных'}; "
        "ограничения: "
        f"{'; '.join(labels) or 'нет данных'}"
    )
