from collections import Counter
import re


FILLER_WORDS = [
    "ну",
    "вот",
    "как бы",
    "типа",
    "значит",
    "короче",
    "понимаешь",
    "понимаете",
    "ага",
    "угу",
    "так",
    "скажем",
    "наверное",
    "в общем",
    "короче говоря",
    "это самое",
    "кстати",
    "вообще",
]


STYLE_STOPWORDS = {
    "это", "что", "как", "все", "она", "они", "был", "была",
    "было", "были", "его", "ее", "её", "их", "наш", "ваш",
    "мой", "моя", "моё", "только", "ещё", "уже", "потом",
    "сейчас", "когда", "если", "чтобы", "потому", "поэтому",
    "здесь", "там", "тут", "очень", "совсем", "просто", "даже",
    "может", "нужно", "надо", "можно", "своя", "свой", "своё",
    "себя", "тебя", "меня", "него", "нее", "них", "который",
    "которая", "которое", "которые", "этот", "эта", "это",
    "такой", "такая", "такое", "какой", "какая", "какое",
    "будет", "быть", "стать", "стала", "стало", "делать",
    "сделать", "сказать", "говорить", "подумать", "думаю",
}


class SpeechHabits:
    def __init__(
        self,
        memory,
    ):
        self.memory = memory
        self._last_event_id = 0

    def observe_text(self, text):
        if not text:
            return

        text = str(text)
        lowered = text.lower()

        for word in FILLER_WORDS:
            if word in lowered:
                self.memory.speech_bump(
                    word,
                    "filler",
                )

        tokens = re.findall(
            r"[\u0430-\u044f\u0451a-z0-9]+",
            lowered,
        )

        words = [
            token
            for token in tokens
            if (
                token not in STYLE_STOPWORDS
                and len(token) >= 4
            )
        ]

        counts = Counter(words)

        for word, count in counts.items():
            if count >= 2:
                self.memory.speech_bump(
                    word,
                    "favorite_word",
                )

    def learn_from_memory(
        self,
        limit: int = 40,
    ):
        rows = self.memory.connection.execute("""
            SELECT id, content
            FROM events
            WHERE event_type = 'CONVERSATION'
              AND source = 'self'
              AND id > ?
            ORDER BY id ASC
            LIMIT ?
        """, (self._last_event_id, limit)).fetchall()

        processed = 0

        for row in rows:
            self.observe_text(row["content"])
            self._last_event_id = max(
                self._last_event_id,
                int(row["id"]),
            )
            processed += 1

        return processed

    def profile(
        self,
        limit: int = 8,
    ):
        fillers = [
            record["marker"]
            for record in self.memory.speech_top(
                "filler",
                limit,
            )
        ]

        favorites = [
            record["marker"]
            for record in self.memory.speech_top(
                "favorite_word",
                limit,
            )
        ]

        return {
            "filler_words": fillers,
            "favorite_words": favorites,
        }
