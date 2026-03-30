from datetime import UTC, datetime
from functools import lru_cache
import html
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, unquote
import xml.etree.ElementTree as ET

import httpx

from backend.app.schemas.chat import SearchSource, WebSearchLog
from backend.app.services.artifacts import ArtifactService, get_artifact_service


class _DuckDuckGoResultParser(HTMLParser):
    """Extract result titles and snippets from DuckDuckGo HTML search pages."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._result_depth = 0
        self._capture_title = False
        self._capture_snippet = False
        self._current: dict[str, str] | None = None
        self._snippet_parts: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""

        if tag in {"div", "article"} and "result" in classes.split():
            self._in_result = True
            self._result_depth = 1
            self._current = {"title": "", "url": "", "snippet": ""}
            self._snippet_parts = []
            self._title_parts = []
            return

        if self._in_result and tag in {"div", "article"}:
            self._result_depth += 1

        if not self._in_result or self._current is None:
            return

        href = attributes.get("href", "") or ""
        if tag == "a" and "result__a" in classes and href:
            self._capture_title = True
            self._current["url"] = href
            self._title_parts = []
            return

        if "result__snippet" in classes:
            self._capture_snippet = True
            self._snippet_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture_title and tag == "a":
            self._capture_title = False
            if self._current is not None:
                self._current["title"] = html.unescape(" ".join(self._title_parts)).strip()
            self._title_parts = []
            return

        if self._capture_snippet and tag in {"a", "div", "span"}:
            self._capture_snippet = False
            if self._current is not None:
                self._current["snippet"] = html.unescape(" ".join(self._snippet_parts)).strip()
            self._snippet_parts = []

        if self._in_result and tag in {"div", "article"}:
            self._result_depth -= 1
            if self._result_depth <= 0:
                self._flush_current()

    def handle_data(self, data: str) -> None:
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self._capture_title:
            self._title_parts.append(cleaned)
        if self._capture_snippet:
            self._snippet_parts.append(cleaned)

    def _flush_current(self) -> None:
        if self._current and self._current.get("title") and self._current.get("url"):
            self.results.append(self._current)
        self._in_result = False
        self._result_depth = 0
        self._capture_title = False
        self._capture_snippet = False
        self._current = None
        self._snippet_parts = []
        self._title_parts = []


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
    """Web search adapter with multi-engine fallback and grounded source extraction."""

    def __init__(self, artifact_service: ArtifactService) -> None:
        self.artifact_service = artifact_service

    def should_search(self, user_message: str) -> bool:
        lower = user_message.lower()
        explicit_triggers = [
            "search",
            "seach",
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
        freshness_triggers = [
            "price",
            "stock",
            "market cap",
            "btc",
            "bitcoin",
            "ethereum",
            "eth",
            "gold",
            "silver",
            "exchange rate",
            "weather",
            "forecast",
            "traffic",
            "score",
            "standings",
            "earnings",
            "ceo",
            "president",
            "prime minister",
            "version",
            "release",
        ]
        if any(trigger in lower for trigger in explicit_triggers):
            return True
        if any(trigger in lower for trigger in freshness_triggers):
            return True
        return bool(re.search(r"\b(price of|how much is|worth right now|trading at)\b", lower))

    async def search(self, session_id: str, query: str, limit: int = 5) -> WebSearchLog:
        prepared_query = self._prepare_query(query)
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            instant_data = await self._duckduckgo_instant_answer(client, prepared_query)
            ddg_results = await self._duckduckgo_html_results(client, prepared_query, limit * 2)
            bing_results = await self._bing_rss_results(client, prepared_query, limit * 2)

            sources = await self._merge_sources(
                client=client,
                instant_data=instant_data,
                result_sets=[("duckduckgo", ddg_results), ("bing", bing_results)],
                limit=limit,
            )

        provider = self._provider_label(ddg_results, bing_results)
        summary = self._build_summary(prepared_query, sources)
        log = WebSearchLog(
            query=query,
            provider=provider,
            searched_at=self._timestamp(),
            summary=summary,
            sources=sources,
        )

        content = self.build_prompt_context(log)
        await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="search",
            title=query,
            content=content,
            metadata={
                "query": query,
                "prepared_query": prepared_query,
                "provider": log.provider,
                "status": log.status,
                "source_count": len(log.sources),
                "sources": [source.model_dump() for source in log.sources],
            },
        )
        return log

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

    def build_prompt_context(self, log: WebSearchLog) -> str:
        if log.status == "failed":
            return (
                f"Web search attempt for `{log.query}` failed.\n"
                f"Error: {log.error or 'Unknown search error.'}"
            )

        lines = [
            f"Web search results for `{log.query}`.",
            f"Searched at: {log.searched_at}",
            f"Search provider: {log.provider}",
            (
                "Instruction: Answer strictly from these retrieved results. "
                "Do not invent numbers or claim an exact value unless a source below supports it."
            ),
        ]
        if log.summary:
            lines.append(f"Summary: {log.summary}")
        if not log.sources:
            lines.append("- No search results were available for this query.")
            return "\n".join(lines)

        for source in log.sources:
            source_line = f"- {source.title} ({source.url})"
            if source.snippet:
                source_line += f"\n  {source.snippet}"
            lines.append(source_line)
        return "\n".join(lines)

    def failed_log(self, query: str, error: str) -> WebSearchLog:
        return WebSearchLog(
            query=query,
            searched_at=self._timestamp(),
            status="failed",
            summary="The web search request failed.",
            error=error,
        )

    async def _merge_sources(
        self,
        client: httpx.AsyncClient,
        instant_data: dict,
        result_sets: list[tuple[str, list[dict[str, str]]]],
        limit: int,
    ) -> list[SearchSource]:
        sources: list[SearchSource] = []
        seen_urls: set[str] = set()

        instant_url = self._normalize_result_url(instant_data.get("AbstractURL", ""))
        instant_text = (instant_data.get("AbstractText") or "").strip()
        if instant_url and instant_text:
            seen_urls.add(instant_url)
            sources.append(
                SearchSource(
                    title=(instant_data.get("Heading") or "Answer").strip(),
                    url=instant_url,
                    snippet=instant_text,
                    domain=self._extract_domain(instant_url),
                )
            )

        for _, results in result_sets:
            for result in results:
                normalized_url = self._normalize_result_url(result.get("url", ""))
                if not normalized_url or normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                snippet = (result.get("snippet") or "").strip()
                if not snippet:
                    snippet = await self._fetch_result_excerpt(client, normalized_url)
                sources.append(
                    SearchSource(
                        title=(result.get("title") or normalized_url).strip(),
                        url=normalized_url,
                        snippet=snippet,
                        domain=self._extract_domain(normalized_url),
                    )
                )
                if len(sources) >= limit:
                    return sources[:limit]
        return sources[:limit]

    async def _duckduckgo_instant_answer(self, client: httpx.AsyncClient, query: str) -> dict:
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
        parser = _DuckDuckGoResultParser()
        parser.feed(response.text)
        return parser.results[:limit]

    async def _bing_rss_results(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
    ) -> list[dict[str, str]]:
        try:
            response = await client.get(
                "https://www.bing.com/search",
                params={"q": query, "format": "rss"},
                headers={"User-Agent": "ISE-AI/1.0"},
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception:
            return []

        results: list[dict[str, str]] = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            if title and link:
                results.append(
                    {
                        "title": html.unescape(title),
                        "url": link,
                        "snippet": html.unescape(description),
                    }
                )
            if len(results) >= limit:
                break
        return results

    async def _fetch_result_excerpt(self, client: httpx.AsyncClient, url: str) -> str:
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

    def _build_summary(self, prepared_query: str, sources: list[SearchSource]) -> str:
        if not sources:
            return "No search results were available for this query."

        price_summary = self._extract_price_summary(prepared_query, sources)
        if price_summary:
            return price_summary

        summaries = [source.snippet for source in sources if source.snippet]
        if not summaries:
            return f"Collected {len(sources)} sources from the web."
        joined = " ".join(summaries)
        compact = re.sub(r"\s+", " ", joined).strip()
        return compact[:320] + ("..." if len(compact) > 320 else "")

    def _extract_price_summary(self, prepared_query: str, sources: list[SearchSource]) -> str:
        lower_query = prepared_query.lower()
        if not any(keyword in lower_query for keyword in ["gold", "bitcoin", "btc", "price", "usd"]):
            return ""

        candidates: list[tuple[float, str, str]] = []
        pattern = re.compile(
            r"(?<!\d)(?:usd\s*)?\$?\s*([1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?|[1-9]\d{2,6}(?:\.\d+)?)(?!\d)"
        )
        for source in sources:
            haystack = " ".join(part for part in [source.title, source.snippet] if part)
            for match in pattern.findall(haystack):
                value = float(match.replace(",", ""))
                if "gold" in lower_query and not 2000 <= value <= 10000:
                    continue
                if any(keyword in lower_query for keyword in ["bitcoin", "btc"]) and not 10000 <= value <= 1000000:
                    continue
                candidates.append((value, source.title, source.domain or source.url))

        if not candidates:
            return ""

        candidates.sort(key=lambda item: item[0])
        median_value, _, _ = candidates[len(candidates) // 2]
        supporting = [
            f"{source_name} ({domain})"
            for value, source_name, domain in candidates
            if abs(value - median_value) / median_value < 0.03
        ][:3]
        return (
            f"Observed price candidates from retrieved sources cluster around ${median_value:,.2f}. "
            f"Supporting sources: {', '.join(supporting)}."
        )

    def _normalize_result_url(self, url: str) -> str:
        if not url:
            return ""
        decoded = html.unescape(url).strip()
        parsed = urlparse(decoded)

        if "duckduckgo.com" in parsed.netloc:
            query = parse_qs(parsed.query)
            uddg_values = query.get("uddg")
            if uddg_values:
                return unquote(uddg_values[0])
            if parsed.path.startswith("/l/"):
                match = re.search(r"uddg=([^&]+)", decoded)
                if match:
                    return unquote(match.group(1))

        if decoded.startswith("//"):
            return f"https:{decoded}"
        if decoded.startswith("/"):
            return urljoin("https://duckduckgo.com", decoded)
        return decoded

    def _provider_label(
        self,
        ddg_results: list[dict[str, str]],
        bing_results: list[dict[str, str]],
    ) -> str:
        providers: list[str] = []
        if ddg_results:
            providers.append("duckduckgo")
        if bing_results:
            providers.append("bing")
        return "+".join(providers) if providers else "duckduckgo"

    def _extract_domain(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        return parsed.netloc.removeprefix("www.")

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()

    def _prepare_query(self, query: str) -> str:
        normalized = query.strip()
        cleanup_patterns = [
            r"\bsearch (?:on|the)?\s*(?:internet|web)\b",
            r"\bseach (?:on|the)?\s*(?:internet|web)\b",
            r"\bsearch online\b",
            r"\bgoogle\b",
            r"\blook up\b",
            r"\bfind information about\b",
            r"\bcan you\b",
            r"\btry to\b",
            r"\bplease\b",
        ]
        lowered = normalized.lower()
        for pattern in cleanup_patterns:
            lowered = re.sub(pattern, " ", lowered)
        lowered = re.sub(r"[?!.]+", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered).strip()

        if any(keyword in lowered for keyword in ["bitcoin", "btc"]) and any(
            marker in lowered for marker in ["price", "worth", "trading", "value"]
        ):
            return "bitcoin price usd"
        if "gold" in lowered and "price" in lowered:
            return "gold price usd ounce"
        if lowered.startswith("what is "):
            lowered = lowered.removeprefix("what is ").strip()
        if lowered.startswith("what's "):
            lowered = lowered.removeprefix("what's ").strip()
        if lowered.startswith("tell me "):
            lowered = lowered.removeprefix("tell me ").strip()
        return lowered or normalized

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
