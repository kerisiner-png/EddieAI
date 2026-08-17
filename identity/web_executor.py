from html.parser import HTMLParser
from urllib.parse import (
    parse_qs,
    quote_plus,
    unquote,
    urlparse,
)
from urllib.request import (
    Request,
    urlopen,
)


class SearchResultParser(HTMLParser):
    """
    Минимальный HTML parser для DuckDuckGo HTML results.
    """

    def __init__(self, limit: int = 5):
        super().__init__()

        self.limit = limit
        self.results = []

        self._current = None
        self._capture_title = False

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(attrs)

        if (
            tag == "a"
            and "result__a" in attrs.get(
                "class",
                "",
            )
        ):
            href = attrs.get(
                "href",
                "",
            )

            if len(self.results) < self.limit:
                self._current = {
                    "url": self._clean_url(
                        href
                    ),
                    "title": "",
                }

                self._capture_title = True

    def handle_data(self, data):
        if (
            self._current is not None
            and self._capture_title
        ):
            self._current["title"] += data

    def handle_endtag(self, tag):
        if (
            tag == "a"
            and self._current is not None
            and self._capture_title
        ):
            self._current["title"] = (
                " ".join(
                    self._current["title"]
                    .split()
                )
            )

            if self._current["title"]:
                self.results.append(
                    self._current
                )

            self._current = None
            self._capture_title = False

    def _clean_url(self, url: str):
        url = url.strip()

        # Markdown link:
        # [https://example.com](https://example.com)
        if (
            url.startswith("[")
            and "](" in url
            and url.endswith(")")
        ):
            close_bracket = url.find("](")

            if close_bracket > 0:
                target = url[
                    close_bracket + 2:
                    -1
                ].strip()

                if target:
                    url = target

        # DuckDuckGo redirect:
        # /l/?uddg=https%3A%2F%2Fexample.com
        if "uddg=" in url:
            parsed = urlparse(url)

            value = parse_qs(
                parsed.query
            ).get(
                "uddg",
                [url],
            )[0]

            url = unquote(value).strip()

        return url


class WebExecutor:
    """
    Реальный внешний поиск.

    Сейчас разрешён только WEB_SEARCH.
    Произвольное открытие URL не реализовано.
    """

    SEARCH_URL = (
        "https://html.duckduckgo.com/html/"
    )

    def __init__(
        self,
        timeout: int = 10,
        default_limit: int = 5,
    ):
        self.timeout = max(
            1,
            int(timeout),
        )

        self.default_limit = max(
            1,
            min(10, int(default_limit)),
        )

    def search(
        self,
        query: str,
        limit: int | None = None,
    ):
        query = query.strip()

        if not query:
            return {
                "status": "INVALID",
                "error": (
                    "Search query cannot be empty."
                ),
            }

        limit = (
            self.default_limit
            if limit is None
            else max(
                1,
                min(10, int(limit)),
            )
        )

        url = (
            f"{self.SEARCH_URL}"
            f"?q={quote_plus(query)}"
        )

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/131.0 Safari/537.36"
                ),
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                html = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

        except Exception as exc:
            return {
                "status": "ERROR",
                "query": query,
                "error": str(exc),
            }

        parser = SearchResultParser(
            limit=limit
        )

        parser.feed(html)

        results = parser.results

        return {
            "status": "OK",
            "query": query,
            "results": results,
            "count": len(results),
        }

