from functools import lru_cache
import html
from html.parser import HTMLParser
import re
from urllib.parse import urlencode

import httpx

from backend.app.services.artifacts import ArtifactService, get_artifact_service


class _SearchResultParser(HTMLParser):
    """Extract title links from DuckDuckGo's HTML search page."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._capture_title = False
        self._current_url = ""
        self._current_title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""
        href = attributes.get("href", "") or ""
        if "result__a" in classes and href:
            self._capture_title = True
            self._current_url = href
            self._current_title = []

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._capture_title:
            return
        title = html.unescape(" ".join(self._current_title)).strip()
        if title and self._current_url:
            self.results.append({"title": title, "url": self._current_url})
        self._capture_title = False
        self._current_url = ""
        self._current_title = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self._current_title.append(cleaned)


class _VisibleTextParser(HTMLParser):
    """Turn fetched HTML into readable text snippets."""

    def __init__(self) -> None:
        super().__init__()
        self._ignored_tags: list[str] = []
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_tags.append(tag)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_tags and self._ignored_tags[-1] == tag:
            self._ignored_tags.pop()
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_tags:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        else:
            self.text_parts.append(cleaned)


class SearchService:
    """Web search adapter with result-page fetching for fresher answers."""

    def __init__(self, artifact_service: ArtifactService) -> None:
        self.artifact_service = artifact_service

    def should_search(self, user_message: str) -> bool:
        lower = user_message.lower()
        triggers = [
            "search",
            "google",
            "internet",
            "web",
            "look up",
            "lookup",
            "latest",
            "today",
            "current",
            "recent",
            "news",
            "what happened",
            "find information",
        ]
        return any(trigger in lower for trigger in triggers)

    async def search(self, session_id: str, query: str, limit: int = 5) -> str:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            instant_data = await self._duckduckgo_instant_answer(client, query)
            html_results = await self._duckduckgo_html_results(client, query, limit)

            lines: list[str] = []
            if instant_data.get("AbstractText"):
                lines.append(
                    f"- {instant_data.get('Heading') or 'Answer'}: "
                    f"{instant_data['AbstractText']} ({instant_data.get('AbstractURL', '')})"
                )

            for result in html_results[:limit]:
                excerpt = await self._fetch_result_excerpt(client, result["url"])
                if excerpt:
                    lines.append(f"- {result['title']} ({result['url']})\n  {excerpt}")
                else:
                    lines.append(f"- {result['title']} ({result['url']})")

        if not lines:
            lines.append("- No search results were available for this query.")

        content = f"Web search results for `{query}`:\n" + "\n".join(lines[:limit])
        await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="search",
            title=query,
            content=content,
            metadata={"query": query},
        )
        return content

    async def recent_context(self, session_id: str, user_message: str) -> list[str]:
        if not self._should_load_recent(user_message):
            return []
        artifacts = await self.artifact_service.list_artifacts(
            session_id=session_id,
            kinds=["search"],
            limit=2,
        )
        context = []
        for artifact in artifacts:
            excerpt = artifact.get("content", "")[:2400]
            if excerpt.strip():
                context.append(f"Recent web search:\n{excerpt}")
        return context

    async def _duckduckgo_instant_answer(
        self,
        client: httpx.AsyncClient,
        query: str,
    ) -> dict:
        params = urlencode(
            {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
            }
        )
        url = f"https://api.duckduckgo.com/?{params}"
        response = await client.get(url, headers={"User-Agent": "ISE-AI/1.0"})
        response.raise_for_status()
        return response.json()

    async def _duckduckgo_html_results(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
    ) -> list[dict[str, str]]:
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "ISE-AI/1.0"},
        )
        response.raise_for_status()
        parser = _SearchResultParser()
        parser.feed(response.text)
        return parser.results[:limit]

    async def _fetch_result_excerpt(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> str:
        try:
            response = await client.get(url, headers={"User-Agent": "ISE-AI/1.0"})
            response.raise_for_status()
        except Exception:
            return ""

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        if not content_type.startswith("text/html"):
            return ""

        parser = _VisibleTextParser()
        parser.feed(response.text)
        title = " ".join(parser.title_parts).strip()
        body = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
        if not body:
            return title[:280]
        excerpt = body[:480]
        if title:
            return f"{title}: {excerpt}"
        return excerpt

    def _should_load_recent(self, user_message: str) -> bool:
        lower = user_message.lower()
        phrases = [
            "search result",
            "what did you find",
            "what did you search",
            "that search",
            "latest update",
            "current update",
            "news",
        ]
        return any(phrase in lower for phrase in phrases)


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(artifact_service=get_artifact_service())
