import json
from dataclasses import dataclass


@dataclass
class ActionSelection:
    selected: object
    options: list[object]
    reason: str


class ActionSelector:
    """
    Выбирает действие с controlled exploration.

    История берётся только из ACTION_CHOICE событий
    собственного опыта.

    Каждые EXPLORATION_INTERVAL выборов проверяется
    наименее использованный вариант.
    В остальные моменты выбирается наиболее
    использованный вариант.

    Это пока не personality preference.
    Это только механизм выбора и сбора наблюдаемого опыта.
    """

    EXPLORATION_INTERVAL = 3

    def __init__(
        self,
        memory,
    ):
        self.memory = memory

    def select(
        self,
        options,
        behavioral_biases=None,
    ) -> ActionSelection:

        options = list(options)

        if not options:
            raise ValueError(
                "No action options available."
            )

        if len(options) == 1:
            return ActionSelection(
                selected=options[0],
                options=options,
                reason=(
                    "Доступен только один "
                    "допустимый вариант."
                ),
            )

        counts = self._history_counts(
            options
        )

        total = sum(
            counts.get(
                option.action_type,
                0,
            )
            for option in options
        )

        biases = (
            behavioral_biases
            if isinstance(
                behavioral_biases,
                dict,
            )
            else {}
        )

        def bias_for(option):
            return float(
                biases.get(
                    option.action_type,
                    0.0,
                )
            )

        # -----------------------------------------
        # Нет истории
        # -----------------------------------------

        if total == 0:

            selected = max(
                options,
                key=lambda option: (
                    bias_for(option),
                    -options.index(option),
                ),
            )

            bias = bias_for(
                selected
            )

            if abs(bias) > 0.0:
                reason = (
                    "История выбора отсутствует; "
                    "выбор скорректирован текущим "
                    "affective state."
                )
            else:
                selected = options[0]
                reason = (
                    "История выбора отсутствует; "
                    "использован первый допустимый "
                    "вариант."
                )

            return ActionSelection(
                selected=selected,
                options=options,
                reason=reason,
            )

        # -----------------------------------------
        # Exploration
        #
        # Во время исследования сохраняем старую
        # механику, но bias становится tie-breaker.
        # -----------------------------------------

        exploration = (
            total
            % self.EXPLORATION_INTERVAL
            == 0
        )

        if exploration:
            selected = min(
                options,
                key=lambda option: (
                    counts.get(
                        option.action_type,
                        0,
                    ),
                    -bias_for(option),
                    option.action_type,
                ),
            )

            reason = (
                "Режим исследования: выбран "
                "наименее использованный "
                "допустимый вариант с учётом "
                "текущего affective state."
            )

        else:
            # -------------------------------------
            # Нормальный выбор
            #
            # Историческая частота остаётся основной
            # величиной; affective bias — небольшой
            # корректирующий фактор.
            # -------------------------------------

            selected = max(
                options,
                key=lambda option: (
                    counts.get(
                        option.action_type,
                        0,
                    )
                    + bias_for(option),
                    bias_for(option),
                    option.action_type,
                ),
            )

            reason = (
                "Режим эксплуатации: выбран "
                "наиболее подходящий по истории "
                "вариант с учётом текущего "
                "affective state."
            )

        return ActionSelection(
            selected=selected,
            options=options,
            reason=reason,
        )

    def _history_counts(
        self,
        options,
    ):
        option_types = {
            option.action_type
            for option in options
        }

        counts = {
            option_type: 0
            for option_type in option_types
        }

        rows = self.memory.connection.execute(
            """
            SELECT content
            FROM events
            WHERE event_type = 'ACTION_CHOICE'
              AND source_type = 'SELF_ACTION'
              AND personal_experience = 1
            ORDER BY id ASC
            """
        ).fetchall()

        for row in rows:
            try:
                payload = json.loads(
                    row["content"]
                )
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                continue

            if not isinstance(
                payload,
                dict,
            ):
                continue

            choice = payload.get(
                "choice"
            )

            if not isinstance(
                choice,
                dict,
            ):
                continue

            historical_options = choice.get(
                "options",
                [],
            )

            selected = choice.get(
                "selected"
            )

            if not isinstance(
                historical_options,
                list,
            ):
                continue

            historical_set = {
                str(value)
                for value
                in historical_options
            }

            current_set = {
                str(value)
                for value
                in option_types
            }

            if (
                historical_set
                != current_set
            ):
                continue

            if selected in counts:
                counts[selected] += 1

        return counts
