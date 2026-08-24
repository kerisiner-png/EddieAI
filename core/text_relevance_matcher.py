import re


class TextRelevanceMatcher:
    """
    Универсальный лёгкий matcher для определения,
    относятся ли два коротких текста к одной теме.

    Не является полноценным лемматизатором.
    Использует:
    - точное совпадение;
    - нормализацию;
    - близость словоформ по общей основе.

    Не зависит от конкретных терминов.
    """

    STOPWORDS = {
        "что", "это", "как", "где", "когда", "почему",
        "зачем", "ты", "я", "мне", "тебе", "у", "в",
        "на", "из", "о", "об", "про", "для", "и",
        "или", "но", "не", "да", "нет", "быть",
        "есть", "был", "была", "были", "быть",
        "мой", "моя", "мои", "моё", "твой", "твоя",
        "твои", "твоё", "свой", "своя", "свои",
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join(
            str(text or "")
            .casefold()
            .split()
        )

    @classmethod
    def tokens(cls, text: str) -> set[str]:
        text = cls.normalize_text(text)

        raw = re.findall(
            r"[a-zа-яё0-9]{4,}",
            text,
        )

        return {
            token
            for token in raw
            if token not in cls.STOPWORDS
        }

    @staticmethod
    def common_prefix_length(
        a: str,
        b: str,
    ) -> int:
        limit = min(
            len(a),
            len(b),
        )

        i = 0

        while (
            i < limit
            and a[i] == b[i]
        ):
            i += 1

        return i

    @classmethod
    def token_related(
        cls,
        a: str,
        b: str,
    ) -> bool:
        a = a.casefold()
        b = b.casefold()

        if a == b:
            return True

        # Для коротких слов общего префикса
        # недостаточно.
        minimum_length = min(
            len(a),
            len(b),
        )

        if minimum_length < 6:
            return False

        prefix = cls.common_prefix_length(
            a,
            b,
        )

        ratio = (
            prefix
            / minimum_length
        )

        # Требуем одновременно:
        # - минимум 6 общих символов;
        # - не менее 75% общей основы.
        return (
            prefix >= 6
            and ratio >= 0.75
        )

    @classmethod
    def related_tokens(
        cls,
        left: set[str],
        right: set[str],
    ) -> set[tuple[str, str]]:
        matches = set()

        for a in left:
            for b in right:
                if cls.token_related(
                    a,
                    b,
                ):
                    matches.add(
                        (a, b)
                    )

        return matches

    @classmethod
    def relevance(
        cls,
        query: str,
        document: str,
    ) -> dict:
        query_tokens = cls.tokens(
            query
        )

        document_tokens = cls.tokens(
            document
        )

        matches = cls.related_tokens(
            query_tokens,
            document_tokens,
        )

        if not query_tokens:
            return {
                "relevant": False,
                "score": 0.0,
                "matches": [],
            }

        score = min(
            1.0,
            len(matches)
            / max(
                2,
                min(
                    len(query_tokens),
                    5,
                ),
            ),
        )

        return {
            "relevant": bool(matches),
            "score": score,
            "matches": sorted(
                matches
            ),
        }
