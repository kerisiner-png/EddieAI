from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class EvaluatedSource:
    title: str
    url: str
    score: float
    accepted: bool
    source_class: str
    reasons: list[str]


class SourceEvaluator:
    """
    Предварительно оценивает результаты поиска.

    Это не проверка истинности утверждений.
    Это фильтр качества/релевантности источника.

    Он не доверяет источнику автоматически.
    Он только определяет, стоит ли передавать
    его дальше на интерпретацию.
    """

    HIGH_TRUST_DOMAINS = {
        "nasa.gov",
        "esa.int",
        "noaa.gov",
        "nih.gov",
        "nasa.gov",
        "science.org",
        "nature.com",
        "aps.org",
        "cern.ch",
    }

    MEDIUM_TRUST_DOMAINS = {
        "wikipedia.org",
        "britannica.com",
        "smithsonianmag.com",
        "nationalgeographic.com",
        "skyandtelescope.org",
        "space.com",
        "habr.com",
        "stackoverflow.com",
        "stackoverflow.blog",
        "github.com",
        "python.org",
        "docs.python.org",
        "developer.mozilla.org",
        "arxiv.org",
        "ieee.org",
        "acm.org",
    }

    LOW_TRUST_DOMAINS = {
        "youtube.com",
        "youtu.be",
        "yandex.ru",
        "rutube.ru",
        "mirkosmosa.ru",
        "nsportal.ru",
        "infourok.ru",
        "obuchonok.ru",
    }

    LOW_QUALITY_TERMS = {
        "гороскоп",
        "зодиак",
        "лунный календарь",
        "астрология",
        "гадание",
        "предсказание",
    }

    SCIENCE_TERMS = {
        "science",
        "research",
        "study",
        "mission",
        "space",
        "astronomy",
        "cosmology",
        "physics",
        "космос",
        "астроном",
        "исследован",
        "мисси",
        "наук",
        "физик",
        "орбит",
        "планет",
    }

    def __init__(
        self,
        acceptance_threshold: float = 0.45,
    ):
        self.acceptance_threshold = max(
            0.0,
            min(
                1.0,
                float(
                    acceptance_threshold
                ),
            ),
        )

    def evaluate(
        self,
        results: list[dict],
        query: str,
    ):
        evaluated = []

        for item in results:
            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip()

            url = str(
                item.get(
                    "url",
                    "",
                )
            ).strip()

            if not url:
                continue

            evaluated.append(
                self._evaluate_one(
                    title=title,
                    url=url,
                    query=query,
                )
            )

        return evaluated

    def accepted(
        self,
        results: list[dict],
        query: str,
    ):
        return [
            item
            for item in self.evaluate(
                results,
                query,
            )
            if item.accepted
        ]

    def _evaluate_one(
        self,
        title: str,
        url: str,
        query: str,
    ):
        score = 0.5
        reasons = []

        domain = self._domain(
            url
        )

        title_lower = title.lower()
        query_lower = query.lower()

        source_class = (
            "unknown"
        )

        # -----------------------------------------
        # DOMAIN QUALITY
        # -----------------------------------------

        if self._matches_domain(
            domain,
            self.HIGH_TRUST_DOMAINS,
        ):
            score += 0.35
            source_class = "high_trust"
            reasons.append(
                "Высокоавторитетный домен."
            )

        elif self._matches_domain(
            domain,
            self.MEDIUM_TRUST_DOMAINS,
        ):
            score += 0.15
            source_class = "medium_trust"
            reasons.append(
                "Средний уровень авторитетности."
            )

        elif self._matches_domain(
            domain,
            self.LOW_TRUST_DOMAINS,
        ):
            score -= 0.20
            source_class = "low_trust"
            reasons.append(
                "Источник требует осторожной оценки."
            )

        # -----------------------------------------
        # RELEVANCE
        # -----------------------------------------

        query_terms = self._terms(
            query_lower
        )

        title_terms = self._terms(
            title_lower
        )

        overlap = (
            len(
                query_terms
                & title_terms
            )
            / max(
                1,
                len(query_terms),
            )
        )

        if overlap >= 0.5:
            score += 0.15
            reasons.append(
                "Заголовок хорошо соответствует запросу."
            )

        elif overlap == 0:
            score -= 0.15
            reasons.append(
                "В заголовке нет явного соответствия запросу."
            )

        else:
            score += 0.05

        # -----------------------------------------
        # SCIENTIFIC SIGNAL
        # -----------------------------------------

        if any(
            term in title_lower
            for term in self.SCIENCE_TERMS
        ):
            score += 0.10
            reasons.append(
                "Есть научная/исследовательская лексика."
            )

        # -----------------------------------------
        # LOW QUALITY CONTENT
        # -----------------------------------------

        for term in self.LOW_QUALITY_TERMS:
            if term in title_lower:
                score -= 0.55
                reasons.append(
                    f"Обнаружен низкокачественный "
                    f"смысловой сигнал: {term}."
                )

        # -----------------------------------------
        # VIDEO SIGNAL
        # -----------------------------------------

        if (
            "youtube.com" in domain
            or "youtu.be" in domain
            or "video" in url.lower()
        ):
            score -= 0.10
            reasons.append(
                "Видео является вторичным источником."
            )

        score = max(
            0.0,
            min(
                1.0,
                round(
                    score,
                    3,
                ),
            ),
        )

        accepted = (
            score
            >= self.acceptance_threshold
        )

        return EvaluatedSource(
            title=title,
            url=url,
            score=score,
            accepted=accepted,
            source_class=source_class,
            reasons=reasons,
        )

    def _domain(
        self,
        url: str,
    ):
        try:
            parsed = urlparse(
                url
            )

            domain = (
                parsed.netloc
                or ""
            ).lower()

            if domain.startswith(
                "www."
            ):
                domain = domain[
                    4:
                ]

            return domain

        except Exception:
            return ""

    def _matches_domain(
        self,
        domain: str,
        domains: set[str],
    ):
        return any(
            domain == allowed
            or domain.endswith(
                "." + allowed
            )
            for allowed in domains
        )

    def _terms(
        self,
        text: str,
    ):
        normalized = (
            text.lower()
            .replace(
                ":",
                " ",
            )
            .replace(
                ",",
                " ",
            )
            .replace(
                ".",
                " ",
            )
        )

        return {
            token
            for token in normalized.split()
            if len(token) >= 4
        }
