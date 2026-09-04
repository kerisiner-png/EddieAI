from typing import Optional


VERB_COMMANDS = {
    "посмотрим": "movie",
    "посмотреть": "movie",
    "посмотреть": "movie",
    "включим": "movie",
    "поиграем": "game",
    "поиграть": "game",
    "поработаем": "coding",
    "поработать": "coding",
    "почитаем": "reading",
    "почитать": "reading",
    "поболтаем": "conversation",
    "поговорим": "conversation",
    "послушаем": "music",
    "послушать": "music",
}

GENERIC_VERBS = {
    "включи",
    "включить",
    "запусти",
    "запустить",
    "поставь",
    "поставить",
    "давай",
    "го",
    "хочу",
    "хотелось",
    "давайте",
}

NOUN_TYPES = {
    "фильм": "movie",
    "фильмы": "movie",
    "кино": "movie",
    "видео": "movie",
    "мульт": "movie",
    "музыку": "music",
    "музыка": "music",
    "музыки": "music",
    "песни": "music",
    "трек": "music",
    "плейлист": "music",
    "игру": "game",
    "игра": "game",
    "игры": "game",
    "код": "coding",
    "проект": "coding",
    "проектом": "coding",
    "книгу": "reading",
    "книга": "reading",
}

STOP_WORDS = {
    "давай",
    "в",
    "во",
    "над",
    "по",
    "на",
    "с",
    "со",
    "сегодня",
    "хватит",
    "давайте",
}

STOP_PATTERNS = [
    "выключи",
    "хватит",
    "стоп",
    "закончил",
    "останови",
    "всё, хватит",
]


def parse_activity_command(text):
    if not text:
        return None
    lower = text.lower().strip()

    for stop in STOP_PATTERNS:
        if stop in lower:
            return {"kind": "stop"}

    tokens = lower.split()
    if not tokens:
        return None

    activity_type = None
    title_tokens = []
    type_pos = None

    for idx, token in enumerate(tokens):
        if token in VERB_COMMANDS:
            activity_type = VERB_COMMANDS[token]
            type_pos = idx
            break
        if token in NOUN_TYPES:
            activity_type = NOUN_TYPES[token]
            type_pos = idx
            break

    if activity_type is None:
        for idx, token in enumerate(tokens):
            if token in GENERIC_VERBS:
                continue
            for noun, atype in NOUN_TYPES.items():
                if noun in token:
                    activity_type = atype
                    type_pos = idx
                    break
            if activity_type:
                break

    if activity_type is None:
        return None

    has_action = any(
        token in VERB_COMMANDS
        or token in GENERIC_VERBS
        for token in tokens
    )
    if not has_action:
        return None

    if type_pos is not None:
        for token in tokens[type_pos + 1:]:
            if token in STOP_WORDS or token in GENERIC_VERBS:
                continue
            if token in VERB_COMMANDS or token in NOUN_TYPES:
                continue
            title_tokens.append(token)
        title = " ".join(title_tokens).capitalize()
    else:
        title = ""

    return {
        "kind": "start",
        "activity_type": activity_type,
        "title": title,
    }