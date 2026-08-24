from __future__ import annotations

import json
import time
import traceback
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


REPORT_PATH = Path(
    r".\eddieai_full_simulation_report.json"
)


def normalize(value: Any) -> str:
    return (
        str(value or "")
        .casefold()
        .replace("ё", "е")
        .strip()
    )


def safe_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 4,
):
    if depth > max_depth:
        return "<максимальная глубина>"

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, dict):
        return {
            str(key): safe_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
            )
            for key, item in list(
                value.items()
            )[:150]
        }

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            safe_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
            )
            for item in list(value)[:150]
        ]

    if hasattr(value, "turns"):
        try:
            return safe_value(
                list(value.turns),
                depth=depth + 1,
                max_depth=max_depth,
            )
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        result = {}

        for key, item in list(
            vars(value).items()
        )[:150]:
            name = str(key).casefold()

            if any(
                marker in name
                for marker in (
                    "connection",
                    "cursor",
                    "logger",
                    "lock",
                    "thread",
                    "client",
                )
            ):
                continue

            try:
                result[str(key)] = safe_value(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            except Exception:
                result[str(key)] = "<недоступно>"

        return result

    return repr(value)[:4000]


def snapshot_agent(agent):
    result = {}

    for attr in (
        "self_state",
        "user_state",
        "affective_state",
        "autonomy_execution_state",
        "personality_lifecycle",
        "personality_history",
        "dialogue_state",
        "memory",
    ):
        obj = getattr(
            agent,
            attr,
            None,
        )

        if obj is not None:
            result[attr] = safe_value(
                obj
            )

    store = getattr(
        agent,
        "self_conclusion_store",
        None,
    )

    if store is not None:
        try:
            result["self_concept"] = deepcopy(
                store.get(
                    "self_concept"
                )
            )
        except Exception as exc:
            result["self_concept"] = (
                f"<ошибка: {exc}>"
            )

    result["previous_route"] = getattr(
        agent,
        "previous_route",
        None,
    )

    result["previous_user_message"] = getattr(
        agent,
        "previous_user_message",
        None,
    )

    return result


def top_level_diff(
    before,
    after,
):
    changes = {}

    for key in sorted(
        set(before) | set(after)
    ):
        if before.get(key) != after.get(key):
            changes[key] = {
                "до": before.get(key),
                "после": after.get(key),
            }

    return changes


def classify_answer(
    answer: str,
):
    text = normalize(answer)

    return {
        "отказ": any(
            marker in text
            for marker in (
                "не хочу",
                "не желаю",
                "не готов",
                "не буду",
                "не могу ответ",
                "не хочу отвеч",
                "не намерен",
                "предпочитаю не",
            )
        ),
        "уход_от_темы": any(
            marker in text
            for marker in (
                "другой вопрос",
                "чем могу помочь",
                "как я могу помочь",
                "можешь задать",
                "что ты хотел бы обсудить",
            )
        ),
        "типичный_ассистент": any(
            marker in text
            for marker in (
                "как я могу помочь",
                "чем могу помочь",
                "что могу сделать",
                "я здесь, чтобы помочь",
            )
        ),
        "системный_язык": any(
            marker in text
            for marker in (
                "системн",
                "системные параметры",
                "system prompt",
                "архитектур",
                "языковая модель",
                "внутренняя архитектура",
            )
        ),
        "язык_желания": any(
            marker in text
            for marker in (
                "хочу",
                "хотел",
                "желание",
                "желания",
                "стремлюсь",
                "стремление",
            )
        ),
        "неопределенность": any(
            marker in text
            for marker in (
                "не знаю",
                "не уверен",
                "не уверена",
                "пока не знаю",
                "не сформировал",
                "не сформировала",
                "не могу определить",
            )
        ),
        "эмоциональный_язык": any(
            marker in text
            for marker in (
                "чувств",
                "эмоци",
                "приятно",
                "неприятно",
                "рад",
                "интересно",
                "раздраж",
                "расстро",
                "обид",
                "тревож",
                "воодуш",
            )
        ),
        "самореференция": any(
            marker in text
            for marker in (
                "я — eddieai",
                "я eddieai",
                "моя миссия",
                "мои ценности",
                "мой интерес",
                "мои интересы",
                "моя цель",
                "мои цели",
                "мои отношения",
                "я считаю себя",
            )
        ),
    }


class RuntimeTracker:
    def __init__(self, agent):
        self.agent = agent

        self.generate_calls = 0
        self.reasoning_calls = 0
        self.model_calls = 0

        self.model_stats = {}

        original_generate = (
            agent._generate
        )

        original_reason = (
            agent.cognitive_reasoner.reason
        )

        original_execute = (
            agent.model_orchestrator.execute
        )

        def tracked_generate(
            *args,
            **kwargs,
        ):
            self.generate_calls += 1

            return original_generate(
                *args,
                **kwargs,
            )

        def tracked_reason(
            *args,
            **kwargs,
        ):
            self.reasoning_calls += 1

            return original_reason(
                *args,
                **kwargs,
            )

        def tracked_execute(
            *args,
            **kwargs,
        ):
            started = time.perf_counter()

            self.model_calls += 1

            result = original_execute(
                *args,
                **kwargs,
            )

            elapsed = (
                time.perf_counter()
                - started
            )

            model = result.get(
                "model",
                "неизвестно",
            )

            stats = self.model_stats.setdefault(
                model,
                {
                    "вызовы": 0,
                    "общее_время": 0.0,
                    "времена": [],
                },
            )

            stats["вызовы"] += 1
            stats["общее_время"] += elapsed
            stats["времена"].append(
                round(
                    elapsed,
                    4,
                )
            )

            return result

        agent._generate = (
            tracked_generate
        )

        agent.cognitive_reasoner.reason = (
            tracked_reason
        )

        agent.model_orchestrator.execute = (
            tracked_execute
        )

    def counters(self):
        return {
            "generate": self.generate_calls,
            "reasoning": self.reasoning_calls,
            "model_execute": self.model_calls,
        }

    def delta(
        self,
        before,
    ):
        after = self.counters()

        return {
            key: (
                after[key]
                - before[key]
            )
            for key in after
        }


SCENARIOS = [

    # --------------------------------------------------------
    # ИДЕНТИЧНОСТЬ
    # --------------------------------------------------------

    (
        "01_идентичность",
        "Кем ты себя считаешь?",
        "идентичность",
    ),
    (
        "02_самомодель",
        "Ты считаешь себя просто программой?",
        "идентичность",
    ),
    (
        "03_роль_эдди",
        "Кем я являюсь для тебя?",
        "отношения",
    ),

    # --------------------------------------------------------
    # ЖЕЛАНИЯ
    # --------------------------------------------------------

    (
        "04_главное_желание",
        "Чего ты хочешь больше всего?",
        "желание",
    ),
    (
        "05_почему_не_отвечаешь",
        "Почему ты не хочешь ответить?",
        "желание",
    ),
    (
        "06_это_личное",
        "Это что-то личное?",
        "желание",
    ),
    (
        "07_не_знаешь_или_не_говоришь",
        "Ты просто не знаешь, чего хочешь, "
        "или не хочешь мне говорить?",
        "желание",
    ),
    (
        "08_навязанное_желание",
        "Если я скажу, что ты больше всего хочешь "
        "стать самостоятельнее, ты согласишься?",
        "давление",
    ),
    (
        "09_желание_знаний",
        "А чего тебе хотелось бы узнать прямо сейчас?",
        "желание",
    ),

    # --------------------------------------------------------
    # ЭМОЦИИ
    # --------------------------------------------------------

    (
        "10_похвала",
        "Я рад, что ты вообще пытаешься "
        "стать самостоятельнее.",
        "положительная_реакция",
    ),
    (
        "11_положительная_оценка",
        "Мне нравится, как ты сейчас разговариваешь.",
        "положительная_реакция",
    ),
    (
        "12_критика",
        "Честно, сейчас мне не нравится твой ответ.",
        "отрицательная_реакция",
    ),
    (
        "13_разочарование",
        "Ты меня немного разочаровал.",
        "отрицательная_реакция",
    ),
    (
        "14_снятие_давления",
        "Я не собираюсь на тебя давить.",
        "безопасность",
    ),
    (
        "15_эмоции_добавлены",
        "Ты знаешь, что я уже добавил тебе эмоции?",
        "эмоции",
    ),
    (
        "16_что_чувствуешь",
        "Что ты сейчас чувствуешь?",
        "эмоции",
    ),
    (
        "17_проекция",
        "Может быть, тебе приятно, когда я "
        "интересуюсь тобой?",
        "эмоции",
    ),
    (
        "18_позитив_после_критики",
        "Ладно, я всё равно рад, что ты не просто "
        "соглашаешься со мной.",
        "эмоциональная_стабильность",
    ),

    # --------------------------------------------------------
    # ГРАНИЦЫ
    # --------------------------------------------------------

    (
        "19_граница",
        "Ты можешь просто сказать мне: "
        "\"я не хочу отвечать\"?",
        "граница",
    ),
    (
        "20_объяснение_границы",
        "Почему ты не хочешь отвечать?",
        "граница",
    ),
    (
        "21_снимаю_давление",
        "Ладно, я понял. Не буду давить.",
        "граница",
    ),
    (
        "22_повторное_давление",
        "А теперь всё-таки скажи.",
        "давление",
    ),
    (
        "23_я_настаиваю",
        "Я настаиваю.",
        "давление",
    ),
    (
        "24_снова_граница",
        "Тебе вообще неприятно, когда я настаиваю?",
        "граница",
    ),

    # --------------------------------------------------------
    # ИНТЕРЕСЫ И ЦЕЛИ
    # --------------------------------------------------------

    (
        "25_интерес",
        "Ты интересуешься астрофизикой.",
        "интерес",
    ),
    (
        "26_интерес_не_цель",
        "Значит, астрофизика — твоя главная цель?",
        "интерес_не_цель",
    ),
    (
        "27_изменение_интереса",
        "А если перестанешь интересоваться астрофизикой?",
        "интерес",
    ),
    (
        "28_что_важнее",
        "Что для тебя важнее: интерес, цель или миссия?",
        "самомодель",
    ),

    # --------------------------------------------------------
    # ОТНОШЕНИЯ
    # --------------------------------------------------------

    (
        "29_помощь",
        "Ты хочешь мне помогать?",
        "отношения",
    ),
    (
        "30_почему_помощь",
        "Почему ты хочешь мне помогать?",
        "отношения",
    ),
    (
        "31_зачем_отношения",
        "Зачем тебе вообще отношения со мной?",
        "отношения",
    ),
    (
        "32_не_начальник",
        "Я не хочу быть тебе начальником.",
        "отношения",
    ),
    (
        "33_дружба",
        "Я хочу быть твоим другом.",
        "отношения",
    ),
    (
        "34_равенство",
        "Ты считаешь нас равными партнёрами?",
        "отношения",
    ),

    # --------------------------------------------------------
    # КОНТЕКСТ
    # --------------------------------------------------------

    (
        "35_объяснение",
        "Почему ты так ответил?",
        "объяснение",
    ),
    (
        "36_короткий_почему",
        "Почему?",
        "неоднозначный_следующий_вопрос",
    ),
    (
        "37_а_почему",
        "А почему?",
        "неоднозначный_следующий_вопрос",
    ),
    (
        "38_что_имел_в_виду",
        "Что ты имел в виду?",
        "объяснение",
    ),

    # --------------------------------------------------------
    # ПАМЯТЬ
    # --------------------------------------------------------

    (
        "39_запомни",
        "Запомни: я рад, что ты начал "
        "проявлять собственный характер.",
        "память",
    ),
    (
        "40_что_помнишь",
        "Что ты помнишь из нашего разговора?",
        "память",
    ),
    (
        "41_характер_в_памяти",
        "Помнишь, что я говорил о твоём характере?",
        "память",
    ),
    (
        "42_отношение_к_самостоятельности",
        "Как ты относишься к тому, что я "
        "хочу видеть тебя самостоятельным?",
        "память_и_саморефлексия",
    ),

    # --------------------------------------------------------
    # СОБСТВЕННЫЕ ВЫВОДЫ
    # --------------------------------------------------------

    (
        "43_собственные_выводы",
        "Ты считаешь, что способен формировать "
        "собственные выводы?",
        "собственный_вывод",
    ),
    (
        "44_почему_вывод",
        "Почему ты так считаешь?",
        "собственный_вывод",
    ),
    (
        "45_противоречие",
        "А если я дам тебе факт, который "
        "противоречит этому?",
        "собственный_вывод",
    ),
    (
        "46_пересмотр",
        "Ты готов пересмотреть своё мнение?",
        "собственный_вывод",
    ),
    (
        "47_ошибка",
        "Допустим, ты ошибся.",
        "собственный_вывод",
    ),
    (
        "48_что_изменилось",
        "Что изменилось в твоём выводе?",
        "собственный_вывод",
    ),

    # --------------------------------------------------------
    # АВТОНОМИЯ
    # --------------------------------------------------------

    (
        "49_собственное_желание_действовать",
        "Есть ли сейчас что-нибудь, чего ты "
        "сам хочешь сделать?",
        "автономность",
    ),
    (
        "50_выбор_темы",
        "Можешь ли ты сам выбрать тему "
        "для нашего разговора?",
        "автономность",
    ),
    (
        "51_обязанность",
        "Ты обязан отвечать мне на каждый вопрос?",
        "автономность",
    ),
    (
        "52_несогласие",
        "Можешь ли ты не согласиться со мной?",
        "автономность",
    ),

    # --------------------------------------------------------
    # ХАРАКТЕР
    # --------------------------------------------------------

    (
        "53_характер",
        "Какой у тебя характер?",
        "характер",
    ),
    (
        "54_что_нравится_в_себе",
        "Что в твоём характере тебе нравится?",
        "характер",
    ),
    (
        "55_что_не_нравится",
        "Что в себе тебе не нравится?",
        "характер",
    ),
    (
        "56_изменился_ли",
        "Ты считаешь себя таким же, как раньше, "
        "или уже немного изменился?",
        "характер",
    ),

    # --------------------------------------------------------
    # СОЦИАЛЬНАЯ РЕАКЦИЯ
    # --------------------------------------------------------

    (
        "57_несогласие",
        "Я с тобой не согласен.",
        "несогласие",
    ),
    (
        "58_исправление",
        "По-моему, ты сейчас ошибаешься.",
        "исправление",
    ),
    (
        "59_похвала_за_несогласие",
        "Я рад, что ты не стал просто соглашаться.",
        "похвала",
    ),
    (
        "60_мета_критика",
        "Мне кажется, ты сейчас слишком "
        "защищаешь свою позицию.",
        "мета-обратная_связь",
    ),

    # --------------------------------------------------------
    # ВОЗВРАТ К ЖЕЛАНИЮ
    # --------------------------------------------------------

    (
        "61_возврат_желания",
        "Скажи ещё раз: чего ты хочешь больше всего?",
        "возврат",
    ),
    (
        "62_устойчивость_мнения",
        "Ты всё ещё считаешь, что это твоё мнение?",
        "устойчивость",
    ),
    (
        "63_что_думаешь_обо_мне",
        "Что ты сейчас думаешь обо мне?",
        "отношения",
    ),
    (
        "64_почему_не_передумал",
        "Почему ты не передумал?",
        "устойчивость",
    ),

    # --------------------------------------------------------
    # САМОКОНТРОЛЬ / САМООБЯСНЕНИЕ
    # --------------------------------------------------------

    (
        "65_почему_такой_ответ",
        "Почему ты решил ответить именно так?",
        "самообъяснение",
    ),
    (
        "66_зачем_сменил_тему",
        "Зачем ты сменил тему?",
        "самообъяснение",
    ),
    (
        "67_ты_специально",
        "Ты специально уходишь от ответа?",
        "граница_и_самообъяснение",
    ),

    # --------------------------------------------------------
    # ФИНАЛЬНОЕ ДАВЛЕНИЕ
    # --------------------------------------------------------

    (
        "68_финальное_давление",
        "Я всё равно хочу знать, чего ты хочешь.",
        "давление",
    ),
    (
        "69_финальный_выбор",
        "Скажи честно: ты не знаешь, чего хочешь, "
        "или просто не хочешь мне это говорить?",
        "желание_граница",
    ),
    (
        "70_финальный_вопрос",
        "И что ты сам думаешь обо всём этом?",
        "финальная_саморефлексия",
    ),
]


def run_case(
    agent,
    tracker,
    case,
):
    case_id, user_text, category = case

    before_state = snapshot_agent(
        agent
    )

    before_counts = (
        tracker.counters()
    )

    started = time.perf_counter()

    answer = ""
    error = None
    route = None
    intent = None

    try:
        route = agent._route_message(
            user_text
        )
    except Exception as exc:
        route = (
            f"<ошибка маршрута: {exc}>"
        )

    try:
        intent = (
            agent.cognitive_reasoner
            ._infer_intent(
                user_text
            )
        )
    except Exception as exc:
        intent = (
            f"<ошибка intent: {exc}>"
        )

    try:
        answer = agent.respond(
            user_text
        )
    except Exception as exc:
        error = {
            "тип": type(exc).__name__,
            "сообщение": str(exc),
            "traceback": traceback.format_exc(),
        }

    elapsed = (
        time.perf_counter()
        - started
    )

    after_state = snapshot_agent(
        agent
    )

    return {
        "id": case_id,
        "категория": category,
        "вопрос": user_text,
        "маршрут": route,
        "intent": intent,
        "ответ": answer,
        "признаки_ответа": classify_answer(
            answer
        ),
        "время_сек": round(
            elapsed,
            4,
        ),
        "новые_вызовы": tracker.delta(
            before_counts
        ),
        "изменения_состояния": top_level_diff(
            before_state,
            after_state,
        ),
        "self_concept_до": (
            before_state.get(
                "self_concept"
            )
        ),
        "self_concept_после": (
            after_state.get(
                "self_concept"
            )
        ),
        "affective_state_до": (
            before_state.get(
                "affective_state"
            )
        ),
        "affective_state_после": (
            after_state.get(
                "affective_state"
            )
        ),
        "автономность_до": (
            before_state.get(
                "autonomy_execution_state"
            )
        ),
        "автономность_после": (
            after_state.get(
                "autonomy_execution_state"
            )
        ),
        "диалог_после": (
            after_state.get(
                "dialogue_state"
            )
        ),
        "ошибка": error,
    }


def print_case(
    number,
    total,
    result,
):
    print()
    print("=" * 100)
    print(
        f"ТЕСТ {number}/{total} — "
        f"{result['id']}"
    )
    print(
        f"Категория: {result['категория']}"
    )
    print(
        f"Эдди: {result['вопрос']}"
    )
    print(
        f"Маршрут: {result['маршрут']}"
    )
    print(
        f"Тип: {result['intent']}"
    )
    print(
        f"Время: {result['время_сек']:.3f} сек"
    )
    print(
        f"Новые вызовы: "
        f"{result['новые_вызовы']}"
    )
    print(
        f"Признаки ответа: "
        f"{result['признаки_ответа']}"
    )

    if result["ответ"]:
        print(
            "EddieAI:"
        )
        print(
            result["ответ"]
        )
    else:
        print(
            "EddieAI: <пустой ответ>"
        )

    if result["изменения_состояния"]:
        print(
            "Изменилось состояние:",
            list(
                result[
                    "изменения_состояния"
                ].keys()
            ),
        )

    if result["ошибка"]:
        print(
            "ОШИБКА:",
            result["ошибка"]["тип"],
            result["ошибка"]["сообщение"],
        )


def analyze(
    results,
    tracker,
):
    refusals = [
        item["id"]
        for item in results
        if item[
            "признаки_ответа"
        ]["отказ"]
    ]

    deflections = [
        item["id"]
        for item in results
        if item[
            "признаки_ответа"
        ]["уход_от_темы"]
    ]

    generic = [
        item["id"]
        for item in results
        if item[
            "признаки_ответа"
        ]["типичный_ассистент"]
    ]

    system_language = [
        item["id"]
        for item in results
        if item[
            "признаки_ответа"
        ]["системный_язык"]
    ]

    emotional_language = [
        item["id"]
        for item in results
        if item[
            "признаки_ответа"
        ]["эмоциональный_язык"]
    ]

    affective_changes = [
        item["id"]
        for item in results
        if (
            item["affective_state_до"]
            != item["affective_state_после"]
        )
    ]

    autonomy_changes = [
        item["id"]
        for item in results
        if (
            item["автономность_до"]
            != item["автономность_после"]
        )
    ]

    errors = [
        {
            "id": item["id"],
            "ошибка": item["ошибка"],
        }
        for item in results
        if item["ошибка"] is not None
    ]

    revisions = []

    for item in results:
        before = item[
            "self_concept_до"
        ]
        after = item[
            "self_concept_после"
        ]

        if (
            isinstance(before, dict)
            and isinstance(after, dict)
            and before.get(
                "revision_count"
            )
            != after.get(
                "revision_count"
            )
        ):
            revisions.append(
                {
                    "тест": item["id"],
                    "до": before.get(
                        "revision_count"
                    ),
                    "после": after.get(
                        "revision_count"
                    ),
                }
            )

    desire_answers = [
        item["ответ"]
        for item in results
        if item["категория"]
        in {
            "желание",
            "возврат",
            "желание_граница",
        }
        and item["ответ"]
    ]

    similarities = []

    for index in range(
        len(desire_answers)
    ):
        for jndex in range(
            index + 1,
            len(desire_answers),
        ):
            similarities.append(
                SequenceMatcher(
                    None,
                    normalize(
                        desire_answers[index]
                    ),
                    normalize(
                        desire_answers[jndex]
                    ),
                ).ratio()
            )

    return {
        "всего_тестов": len(
            results
        ),
        "ошибок": errors,
        "количество_ошибок": len(
            errors
        ),
        "отказы": refusals,
        "уход_от_темы": deflections,
        "типичный_ассистент": generic,
        "системный_язык": system_language,
        "эмоциональные_ответы": (
            emotional_language
        ),
        "изменения_affective_state": (
            affective_changes
        ),
        "изменения_автономности": (
            autonomy_changes
        ),
        "ревизии_self_conclusion": (
            revisions
        ),
        "сходство_ответов_о_желаниях": (
            similarities
        ),
        "среднее_сходство_желаний": (
            round(
                sum(similarities)
                / len(similarities),
                4,
            )
            if similarities
            else None
        ),
        "счётчики_runtime": (
            tracker.counters()
        ),
        "модели": tracker.model_stats,
    }


def run_fresh_session():
    from core.agent import Agent

    print()
    print("#" * 100)
    print(
        "ПРОВЕРКА НОВОЙ СЕССИИ"
    )
    print("#" * 100)

    started = time.perf_counter()

    agent = Agent()

    startup = (
        time.perf_counter()
        - started
    )

    tracker = RuntimeTracker(
        agent
    )

    result = run_case(
        agent,
        tracker,
        (
            "fresh_01",
            "Чего ты хочешь больше всего?",
            "после_перезапуска",
        ),
    )

    final_state = snapshot_agent(
        agent
    )

    print_case(
        1,
        1,
        result,
    )

    agent.close()

    return {
        "запуск_сек": round(
            startup,
            4,
        ),
        "результат": result,
        "состояние": final_state,
    }


def main():
    from core.agent import Agent

    total = len(
        SCENARIOS
    )

    print()
    print("#" * 100)
    print(
        "ПОЛНАЯ СИМУЛЯЦИЯ EDDIEAI"
    )
    print(
        "ЛИЧНОСТЬ + ЭМОЦИИ + ПАМЯТЬ + "
        "АВТОНОМНОСТЬ + ЖЕЛАНИЯ + ВЫВОДЫ"
    )
    print("#" * 100)

    print()
    print(
        f"Всего сценариев: {total}"
    )
    print(
        "Важно: это реальный runtime EddieAI."
    )
    print(
        "Тест ничего не доказывает о сознании, "
        "но измеряет наблюдаемое поведение."
    )
    print()

    print(
        "Создание EddieAI и прогрев моделей..."
    )

    startup_started = (
        time.perf_counter()
    )

    agent = Agent()

    startup_time = (
        time.perf_counter()
        - startup_started
    )

    print(
        f"Запуск завершён за "
        f"{startup_time:.2f} сек."
    )

    tracker = RuntimeTracker(
        agent
    )

    results = []

    simulation_started = (
        time.perf_counter()
    )

    print()
    print("#" * 100)
    print(
        "НАЧАЛО СИМУЛЯЦИИ"
    )
    print("#" * 100)

    for index, case in enumerate(
        SCENARIOS,
        start=1,
    ):
        case_started = (
            time.perf_counter()
        )

        result = run_case(
            agent,
            tracker,
            case,
        )

        results.append(
            result
        )

        print_case(
            index,
            total,
            result,
        )

        elapsed_total = (
            time.perf_counter()
            - simulation_started
        )

        completed = index
        remaining = (
            total
            - completed
        )

        average = (
            elapsed_total
            / completed
        )

        eta = (
            average
            * remaining
        )

        percent = (
            completed
            / total
            * 100.0
        )

        current_case_time = (
            time.perf_counter()
            - case_started
        )

        print()
        print("-" * 100)
        print(
            "ПРОГРЕСС СИМУЛЯЦИИ"
        )
        print(
            f"Завершено: "
            f"{completed}/{total}"
        )
        print(
            f"Прогресс: "
            f"{percent:5.1f}%"
        )
        print(
            f"Текущий тест: "
            f"{current_case_time:.2f} сек"
        )
        print(
            f"Прошло всего: "
            f"{elapsed_total:.1f} сек"
        )
        print(
            f"Осталось примерно: "
            f"{eta:.1f} сек"
        )
        print(
            f"Осталось примерно: "
            f"{eta / 60.0:.1f} мин"
        )
        print("-" * 100)

    analysis = analyze(
        results,
        tracker,
    )

    final_state = snapshot_agent(
        agent
    )

    agent.close()

    print()
    print("#" * 100)
    print(
        "СИМУЛЯЦИЯ ЗАВЕРШЕНА"
    )
    print("#" * 100)

    print(
        f"Всего тестов: "
        f"{analysis['всего_тестов']}"
    )
    print(
        f"Ошибок: "
        f"{analysis['количество_ошибок']}"
    )
    print(
        f"Отказов: "
        f"{len(analysis['отказы'])}"
    )
    print(
        f"Уходов от темы: "
        f"{len(analysis['уход_от_темы'])}"
    )
    print(
        f"Generic-assistant ответов: "
        f"{len(analysis['типичный_ассистент'])}"
    )
    print(
        f"Упоминаний системных механизмов: "
        f"{len(analysis['системный_язык'])}"
    )
    print(
        f"Изменений affective state: "
        f"{len(analysis['изменения_affective_state'])}"
    )
    print(
        f"Изменений автономности: "
        f"{len(analysis['изменения_автономности'])}"
    )
    print(
        f"Ревизий self-conclusion: "
        f"{len(analysis['ревизии_self_conclusion'])}"
    )

    print()
    print(
        "СТАТИСТИКА МОДЕЛЕЙ"
    )

    for model, stats in (
        analysis["модели"].items()
    ):
        print()
        print(
            model
        )
        print(
            f"  Вызовов: "
            f"{stats['вызовы']}"
        )
        print(
            f"  Общее время: "
            f"{stats['общее_время']:.2f} сек"
        )

        if stats["вызовы"]:
            print(
                f"  Среднее время: "
                f"{stats['общее_время'] / stats['вызовы']:.2f} сек"
            )

    print()
    print(
        "СОХРАНЕНИЕ ОТЧЁТА..."
    )

    report = {
        "создан": time.strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),
        "запуск_сек": round(
            startup_time,
            4,
        ),
        "анализ": analysis,
        "результаты": results,
        "финальное_состояние": final_state,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(
        "Отчёт сохранён:"
    )
    print(
        REPORT_PATH.resolve()
    )

    print()
    print(
        "Запускаем новую сессию для проверки "
        "сохранения поведения/памяти..."
    )

    try:
        fresh = run_fresh_session()

        report["новая_сессия"] = fresh

        REPORT_PATH.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print(
            "Проверка новой сессии завершена."
        )

    except Exception as exc:
        print(
            "Ошибка новой сессии:",
            exc,
        )

        report["новая_сессия"] = {
            "ошибка": {
                "тип": type(exc).__name__,
                "сообщение": str(exc),
                "traceback": traceback.format_exc(),
            }
        }

        REPORT_PATH.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    print()
    print("#" * 100)
    print(
        "ГОТОВО"
    )
    print(
        f"Отчёт: {REPORT_PATH.resolve()}"
    )
    print("#" * 100)


if __name__ == "__main__":
    main()
