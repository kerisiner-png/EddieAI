from html.parser import HTMLParser
from urllib.parse import (
    parse_qs,
    quote,
    quote_plus,
    unquote,
    urlparse,
)
from urllib.request import (
    Request,
    urlopen,
)
import ipaddress
import json


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


class PageTextExtractor(HTMLParser):
    """
    Извлекает видимый текст страницы,
    пропуская script, style и служебные блоки.

    Если на странице есть semantic-контейнер
    (main/article), приоритетно собирается текст
    из него — это отсекает меню и боковые панели.
    """

    SKIP_TAGS = {
        "script",
        "style",
        "noscript",
        "head",
    }

    CONTENT_TAGS = {"main", "article"}

    def __init__(
        self,
        max_chars: int = 2500,
    ):
        super().__init__()

        self.max_chars = max_chars
        self._skip_depth = 0
        self._content_depth = 0
        self._chunks = []
        self._content_chunks = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

        if tag in self.CONTENT_TAGS:
            self._content_depth += 1

    def handle_endtag(
        self,
        tag,
    ):
        if (
            tag in self.SKIP_TAGS
            and self._skip_depth > 0
        ):
            self._skip_depth -= 1

        if (
            tag in self.CONTENT_TAGS
            and self._content_depth > 0
        ):
            self._content_depth -= 1

    def _append_text(self, data):
        text = " ".join(data.split())

        if len(text) < 3:
            return

        if self._content_depth > 0:
            self._content_chunks.append(
                text
            )
        else:
            self._chunks.append(text)

    def handle_data(self, data):
        if self._skip_depth:
            return

        self._append_text(data)

    def get_text(self) -> str:
        result = " ".join(self._chunks)

        content = " ".join(
            self._content_chunks
        )

        if len(content) >= min(
            400,
            self.max_chars // 4,
        ):
            result = content

        return result[: self.max_chars]


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

    def _is_safe_url(self, url: str) -> bool:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if not hostname:
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            return not (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
            )
        except ValueError:
            pass
        blocked = {"localhost", "127.0.0.1", "0.0.0.0"}
        if hostname in blocked:
            return False
        if hostname.endswith(".internal"):
            return False
        return True

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

    def read_page(
        self,
        url: str,
        max_chars: int = 2500,
    ):
        url = url.strip()

        if not url.lower().startswith(
            ("http://", "https://")
        ):
            return {
                "status": "INVALID",
                "url": url,
                "error": (
                    "Only http/https URLs "
                    "are supported."
                ),
            }

        if not self._is_safe_url(url):
            return {
                "status": "BLOCKED",
                "url": url,
                "error": (
                    "URL points to a private/reserved "
                    "network and is not allowed."
                ),
            }

        # Wikipedia: REST API отдаёт чистую
        # выжимку статьи без навигации.
        wiki = urlparse(url)

        if (
            "wikipedia.org" in wiki.netloc
            and "/wiki/" in wiki.path
        ):
            title = quote(
                wiki.path.split("/wiki/")[-1]
            )

            lang = wiki.netloc.split(".")[
                0
            ]

            api_url = (
                f"https://{lang}.wikipedia.org"
                f"/api/rest_v1/page/summary/"
                f"{title}"
            )

            try:
                request = Request(
                    api_url,
                    headers={
                        "User-Agent": (
                            "EddieAI/0.1 "
                            "(research agent)"
                        ),
                    },
                )

                with urlopen(
                    request,
                    timeout=self.timeout + 20,
                ) as response:
                    data = json.loads(
                        response.read().decode(
                            "utf-8",
                        )
                    )

                extract = str(
                    data.get("extract", "")
                ).strip()

                if len(extract) >= 150:
                    return {
                        "status": "OK",
                        "url": url,
                        "title": data.get(
                            "title",
                            "",
                        ),
                        "text": extract[
                            :max_chars
                        ],
                    }
            except Exception:
                pass

        safe_url = quote(
            url,
            safe="%/:=&?~#+!$,;'@()*[]",
        )

        request = Request(
            safe_url,
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
                timeout=self.timeout + 20,
            ) as response:
                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                )

                if (
                    "text/html" not in content_type
                    and "text/plain"
                    not in content_type
                ):
                    return {
                        "status": "SKIP",
                        "url": url,
                        "reason": (
                            f"content-type: "
                            f"{content_type[:60]}"
                        ),
                    }

                html = response.read(
                    300_000
                ).decode(
                    "utf-8",
                    errors="replace",
                )
        except Exception as exc:
            return {
                "status": "ERROR",
                "url": url,
                "error": str(exc)[:150],
            }

        extractor = PageTextExtractor(
            max_chars=max_chars
        )

        try:
            extractor.feed(html)
        except Exception:
            pass

        text = extractor.get_text().strip()

        if not text:
            return {
                "status": "EMPTY",
                "url": url,
            }

        return {
            "status": "OK",
            "url": url,
            "text": text,
        }

