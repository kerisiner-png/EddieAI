"""Контур «слово → дело»: речь EddieAI связывается с волей ядра.

Три правила (решение Эдди 06.09, «все 3»):
1. Обещание действия, которое mapping способен исполнить
   (инструмент/цель), превращается в цель детерминированного
   ядра — слова становятся планом.
2. Обещание без реальной способности вырезается из речи —
   он не говорит того, что не может сделать.
3. Заявления о СВЕРШИВШЕМСЯ («уже запустил», «нашёл») сверяются
   с фактами инструментов за последние 15 минут; без факта —
   вырезаются.
"""
import re
import time

PROMISE_VERBS = {
    "запуск": (
        r"\b(запускаю|запущу|запускаю)\b",
        "запустить {object}",
    ),
    "open": (
        r"\b(открываю|открою)\b",
        "открыть {object}",
    ),
    "enable": (
        r"\b(включаю|включу)\b",
        "включить {object}",
    ),
    "find": (
        r"\b(найду|ищу)\b",
        "изучить: {object}",
    ),
    "look": (
        r"\b(посмотрю|смотрю)\b",
        "изучить: {object}",
    ),
    "check": (
        r"\b(проверю|проверяю)\b",
        "проверить {object}",
    ),
    "make": (
        r"\b(сделаю|делаю)\b",
        "сделать: {object}",
    ),
    "study": (
        r"\b(изучу|изучаю)\b",
        "изучить: {object}",
    ),
    "write": (
        r"\b(напишу|пишу)\b",
        "написать {object}",
    ),
    "install": (
        r"\b(установлю|ставлю)\b",
        "установить {object}",
    ),
}

VERB_TO_TOOL = {
    "запуск": "programs",
    "open": "programs",
    "enable": "programs",
    "find": "research",
    "look": "perceive",
    "check": "research",
    "make": None,
    "study": "research",
    "write": "filesystem",
    "install": "install",
}

PAST_CLAIM_VERBS = (
    r"\b(уже\s+)?(запустил|открыл|нашёл|нашла|"
    r"сделал|проверил|посмотрел|написал|"
    r"установил|изучил)\b"
)

PROMISE_RE = {
    key: re.compile(pattern, re.IGNORECASE)
    for key, (pattern, _) in PROMISE_VERBS.items()
}

PAST_CLAIM_RE = re.compile(
    PAST_CLAIM_VERBS, re.IGNORECASE
)

OBJECT_RE = re.compile(
    r"(?:%s)\s+([^.,!?;]{2,60})" % "|".join(
        pattern.pattern.strip("\\b()|")
        for pattern in PROMISE_RE.values()
    ),
    re.IGNORECASE,
)


def detect_promises(text):
    """
    Обещания первого лица: [(verb_key,
    capability|None, phrase)].
    """
    text = text or ""
    found = []

    for key, regex in PROMISE_RE.items():
        match = regex.search(text)

        if match is None:
            continue

        found.append({
            "verb": key,
            "capability": VERB_TO_TOOL.get(key),
            "phrase": match.group(0).lower(),
        })

    return found


def promise_goal_value(
    verb_key,
    text,
):
    template = PROMISE_VERBS.get(
        verb_key, (None, None)
    )[1]

    if template is None:
        return None

    match = OBJECT_RE.search(text or "")

    obj = match.group(1).strip() if match else ""

    value = template.format(
        object=obj.strip()
    )

    return value.strip(": ").strip()


def strip_promise_phrase(text, phrase):
    if not phrase:
        return text
    return re.sub(
        re.escape(phrase),
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,;-")


def _promise_span(text, verb_match):
    tail = text[verb_match.start():]

    obj = OBJECT_RE.search(tail)

    end = (
        verb_match.start() + obj.end()
        if obj
        else verb_match.end()
    )

    return verb_match.start(), end


def strip_unmapped_promises(text):
    """
    Правило 2: обещания без реальной
    способности удаляются из речи
    вместе с объектом.
    """
    text = text or ""

    for promise in detect_promises(text):
        if promise["capability"] is not None:
            continue

        match = PROMISE_RE[
            promise["verb"]
        ].search(text)

        if match is None:
            continue

        start, end = _promise_span(
            text, match
        )

        text = (
            text[:start]
            + text[end:]
        ).strip(" ,;-")

    return text.strip()


def has_recent_evidence(
    verb_regex_match,
    recent_texts,
):
    needle = (
        verb_regex_match.group(0)
        .lower()
        .replace("уже ", "")
    )
    stem = needle[: max(4, len(needle) - 2)]

    for line in recent_texts:
        if stem and stem in str(line).lower():
            return True

    return False


def strip_unverified_past_claims(
    text,
    recent_texts,
):
    """
    Правило 3: «уже сделал» без факта
    инструментов за окно — вырезается.
    """
    text = text or ""

    match = PAST_CLAIM_RE.search(text)

    if match is None:
        return text

    if has_recent_evidence(
        match, recent_texts or []
    ):
        return text

    sentence_match = re.search(
        r"([^.!?]*%s[^.!?]*[.!?]?)" % (
            match.group(0)
        ),
        text,
        flags=re.IGNORECASE,
    )

    if sentence_match is None:
        return text

    return text.replace(
        sentence_match.group(1), ""
    ).strip()


PROMISE_GOAL_COOLDOWN_SEC = 300.0


def _recent_action_texts(memory, window_sec=900):
    try:
        cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.gmtime(
                time.time() - window_sec
            ),
        )
        rows = memory.connection.execute(
            "SELECT content FROM events "
            "WHERE event_type IN "
            "('SELF_EXPERIENCE','TOOL_RESULT') "
            "AND timestamp >= ? "
            "ORDER BY id DESC LIMIT 40",
            (cutoff,),
        ).fetchall()
        return [str(r["content"]) for r in rows]
    except Exception:
        return []


def process_speech_promises(agent, text):
    """
    Единая обработка исходящей речи:
    обещание с реальной способностью →
    цель ядра; без способности → вырезано;
    «уже сделал» без факта → вырезано.
    """
    text = text or ""

    if not text.strip():
        return text

    goal_manager = getattr(
        agent, "goal_manager", None
    )

    promises = detect_promises(text)

    if promises and goal_manager is not None:
        now = time.time()
        last = getattr(
            agent,
            "_last_promise_goal_ts",
            0.0,
        )

        first = promises[0]

        if (
            first["capability"] is not None
            and now - last
            >= PROMISE_GOAL_COOLDOWN_SEC
        ):
            value = promise_goal_value(
                first["verb"], text
            )

            if value:
                try:
                    goal_manager.add_candidate(
                        value=value,
                        motivation=0.75,
                        priority=0.6,
                        confidence=0.7,
                        source="speech_promise",
                    )
                    goal_manager.activate_with_preemption(
                        value
                    )
                    agent._last_promise_goal_ts = (
                        now
                    )
                except Exception:
                    pass

    text = strip_unmapped_promises(text)

    memory = getattr(agent, "memory", None)

    if memory is not None:
        try:
            text = strip_unverified_past_claims(
                text,
                _recent_action_texts(memory),
            )
        except Exception:
            pass

    return text
