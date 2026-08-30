from dataclasses import dataclass


@dataclass
class ActionPlan:
    action_type: str
    target: str
    parameters: dict
    reason: str


class ActionPlanner:
    KEYWORD_RULES = [
        (
            (
                "провести исследование",
                "исследовать тему",
                "провести анализ",
                "исследовать",
            ),
            "RESEARCH",
        ),
        (
            (
                "найти информацию",
                "найти источник",
                "поискать",
                "найти материал",
                "найти данные",
            ),
            "WEB_SEARCH",
        ),
        (
            (
                "прочитать",
                "открыть файл",
                "посмотреть файл",
                "изучить исходник",
                "прочитать исходник",
                "проверить файл",
            ),
            "READ_FILE",
        ),
        (
            (
                "записать",
                "создать файл",
                "сохранить",
                "обновить файл",
            ),
            "WRITE_FILE",
        ),
        (
            (
                "посмотреть папку",
                "список файлов",
                "листинг",
                "что в каталоге",
            ),
            "LIST_DIR",
        ),
        (
            (
                "найти файл",
                "поиск по имени",
                "где лежит",
            ),
            "SEARCH_FILES",
        ),
        (
            (
                "запустить",
                "выполнить команду",
                "проверить git",
            ),
            "RUN_COMMAND",
        ),
        (
            (
                "подумать",
                "проанализировать",
                "разобраться",
                "сформулировать",
            ),
            "THINK",
        ),
    ]

    def plan(
        self,
        task,
        context: str = "",
    ) -> ActionPlan:
        text = task.title.strip().lower()

        for keywords, action_type in (
            self.KEYWORD_RULES
        ):
            if any(
                keyword in text
                for keyword in keywords
            ):
                return self._build(
                    action_type,
                    task,
                    context,
                )

        return self._build(
            "THINK",
            task,
            context,
        )

    def context_type(
        self,
        task,
    ) -> str:
        planned = self.plan(
            task,
            context="",
        )

        return {
            "RESEARCH": "research",
            "WEB_SEARCH": "research",
            "OPEN_URL": "research",
            "READ_FILE": "file_access",
            "WRITE_FILE": "writing",
            "WRITE": "writing",
            "RUN_COMMAND": "command",
            "THINK": "analysis",
            "WAIT": "general",
        }.get(
            planned.action_type,
            "general",
        )

    def alternatives(
        self,
        task,
        context: str = "",
    ):
        """
        Возвращает детальный план действий
        для заданной задачи.

        На каждый шаг добавляются необходимые
        параметры выполнения и причины.
        """

        base = self.plan(
            task,
            context=context,
        )

        action_type = base.action_type

        if action_type == "RESEARCH":
            return [
                self._build(
                    "RESEARCH",
                    task,
                    context,
                ),
                self._build(
                    "WEB_SEARCH",
                    task,
                    context,
                ),
            ]

        if action_type == "WEB_SEARCH":
            return [
                self._build(
                    "WEB_SEARCH",
                    task,
                    context,
                ),
                self._build(
                    "RESEARCH",
                    task,
                    context,
                ),
            ]

        return [base]

    def _build(
        self,
        action_type: str,
        task,
        context: str = "",
    ):
        if action_type == "RESEARCH":
            query = (
                self._extract_research_query(
                    task.title
                )
            )

            return ActionPlan(
                action_type="RESEARCH",
                target=task.title,
                parameters={
                    "query": query,
                    "limit": 5,
                    "context": context,
                },
                reason=(
                    "Задача требует "
                    "внешнего исследования."
                ),
            )

        if action_type == "WEB_SEARCH":
            query = (
                self._extract_research_query(
                    task.title
                )
            )

            return ActionPlan(
                action_type="WEB_SEARCH",
                target=task.title,
                parameters={
                    "query": query,
                    "limit": 5,
                },
                reason=(
                    "Задача требует "
                    "поиска внешней информации."
                ),
            )

        if action_type == "READ_FILE":
            return ActionPlan(
                action_type="READ_FILE",
                target=task.title,
                parameters={
                    "path": self._extract_path(
                        task.title
                    ),
                },
                reason=(
                    "Задача требует чтения файла."
                ),
            )

        if action_type == "WRITE_FILE":
            return ActionPlan(
                action_type="WRITE_FILE",
                target=task.title,
                parameters={
                    "path": self._extract_path(
                        task.title
                    ),
                    "content": "",
                },
                reason=(
                    "Задача требует записи файла."
                ),
            )

        if action_type == "RUN_COMMAND":
            return ActionPlan(
                action_type="RUN_COMMAND",
                target=task.title,
                parameters={
                    "command": self._extract_command(
                        task.title
                    ),
                },
                reason=(
                    "Задача требует "
                    "выполнения команды."
                ),
            )

        return ActionPlan(
            action_type="THINK",
            target=task.title,
            parameters={
                "context": context,
            },
            reason=(
                "Задача требует "
                "внутреннего анализа."
            ),
        )

    def _extract_research_query(
        self,
        text: str,
    ) -> str:
        query = text.strip()

        prefixes = [
            "Провести исследование:",
            "провести исследование:",
            "Исследовать тему:",
            "исследовать тему:",
            "Исследовать:",
            "исследовать:",
        ]

        changed = True

        while changed:
            changed = False

            for prefix in prefixes:
                if query.startswith(prefix):
                    query = query[
                        len(prefix):
                    ].strip()

                    changed = True
                    break

        if query.lower().startswith(
            "изучить тему:"
        ):
            query = query[
                len("изучить тему:"):
            ].strip()

        return query or text

    def _extract_path(
        self,
        text: str,
    ) -> str:
        lowered = text.lower()

        markers = [
            "c:\\",
            "d:\\",
            "core\\",
            "memory\\",
            "identity\\",
            "data\\",
        ]

        for marker in markers:
            index = lowered.find(marker)

            if index >= 0:
                return text[index:].strip(
                    " .,:;()[]"
                )

        return r"core\agent.py"

    def _extract_command(
        self,
        text: str,
    ) -> str:
        lowered = text.lower()

        if "проверить git" in lowered:
            return "git status"

        return text
