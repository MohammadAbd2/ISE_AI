from datetime import UTC, datetime
from functools import lru_cache
import asyncio
import html
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, unquote
import xml.etree.ElementTree as ET

import httpx

from app.schemas.chat import SearchSource, WebSearchLog
from app.services.artifacts import ArtifactService, get_artifact_service
from app.services.url_content import UrlContentService, get_url_content_service


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

    _ENRICH_TOP_N = 3
    _DEEP_PAGE_CHARS = 2800
    _SHALLOW_PAGE_CHARS = 560
    _SNIPPET_FALLBACK_CHARS = 520
    _MAX_QUERY_VARIANTS = 3

    def __init__(
        self,
        artifact_service: ArtifactService,
        url_content_service: UrlContentService | None = None,
    ) -> None:
        self.artifact_service = artifact_service
        self._url_content = url_content_service

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
        query_variants = self._build_query_variants(query, prepared_query)
        async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
            instant_data = await self._duckduckgo_instant_answer(client, prepared_query)
            fetch_n = max(limit * 4, 12)
            search_batches = await asyncio.gather(
                *[
                    self._run_query_variant(client, variant, fetch_n)
                    for variant in query_variants
                ],
                return_exceptions=True,
            )
            ddg_results: list[dict[str, str]] = []
            bing_results: list[dict[str, str]] = []
            for batch in search_batches:
                if isinstance(batch, BaseException):
                    continue
                ddg_results.extend(batch[0])
                bing_results.extend(batch[1])
            ddg_results = self._filter_engine_results(ddg_results, prepared_query)
            bing_results = self._filter_engine_results(bing_results, prepared_query)

            sources = await self._merge_sources(
                client=client,
                instant_data=instant_data,
                result_sets=[("duckduckgo", ddg_results), ("bing", bing_results)],
                limit=limit,
                prepared_query=prepared_query,
                original_query=query,
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
        research_metadata = self._build_research_metadata(log, query_variants)
        await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="search",
            title=query,
            content=content,
            metadata=research_metadata,
        )
        await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="research",
            title=f"Research: {query}",
            content=self._build_research_artifact_content(log, query_variants),
            metadata=research_metadata,
        )
        return log

    async def recent_context(self, session_id: str, user_message: str) -> list[str]:
        if not self._should_load_recent(user_message):
            return []
        artifacts = await self.artifact_service.list_artifacts(
            session_id=session_id,
            kinds=["research", "search"],
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
                "Instruction: Answer strictly from these retrieved results (snippet and any page excerpt). "
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
                source_line += f"\n  Snippet: {source.snippet}"
            if source.page_excerpt:
                clip = source.page_excerpt[:3200]
                if len(source.page_excerpt) > 3200:
                    clip += "…"
                source_line += f"\n  Page excerpt: {clip}"
            lines.append(source_line)
        return "\n".join(lines)

    def _build_research_metadata(self, log: WebSearchLog, query_variants: list[str]) -> dict:
        conflict = self._detect_numeric_conflict(log.sources)
        freshness = self._estimate_freshness(log.sources)
        confidence = self._estimate_confidence(log.sources, conflict)
        preview = log.summary or f"Collected {len(log.sources)} sources for `{log.query}`."
        return {
            "query": log.query,
            "prepared_query": self._prepare_query(log.query),
            "query_variants": query_variants,
            "provider": log.provider,
            "status": log.status,
            "source_count": len(log.sources),
            "sources": [source.model_dump() for source in log.sources],
            "conflict": conflict,
            "freshness": freshness,
            "confidence": confidence,
            "preview": preview[:240],
        }

    def _build_research_artifact_content(self, log: WebSearchLog, query_variants: list[str]) -> str:
        lines = [
            f"Research query: {log.query}",
            f"Provider: {log.provider}",
            f"Status: {log.status}",
        ]
        if query_variants:
            lines.append("Query plan:")
            lines.extend(f"- {item}" for item in query_variants)
        freshness = self._estimate_freshness(log.sources)
        confidence = self._estimate_confidence(log.sources, self._detect_numeric_conflict(log.sources))
        if freshness:
            lines.append(f"Freshness: {freshness}")
        lines.append(f"Confidence: {confidence}")
        if log.summary:
            lines.append(f"Summary: {log.summary}")
        conflict = self._detect_numeric_conflict(log.sources)
        if conflict:
            lines.append(f"Conflict: {conflict}")
        if log.sources:
            lines.append("Sources:")
            for source in log.sources:
                lines.append(f"- {source.title} ({source.url})")
                if source.snippet:
                    lines.append(f"  Snippet: {source.snippet[:320]}")
        return "\n".join(lines)

    def build_render_blocks(self, log: WebSearchLog) -> list[dict]:
        query_plan = self._build_query_variants(log.query, self._prepare_query(log.query))
        conflict = self._detect_numeric_conflict(log.sources)
        freshness = self._estimate_freshness(log.sources)
        confidence = self._estimate_confidence(log.sources, conflict)
        if log.status == "failed":
            return [
                {
                    "type": "research_result",
                    "payload": {
                        "query": log.query,
                        "provider": log.provider,
                        "status": log.status,
                        "query_plan": query_plan,
                        "freshness": "",
                        "confidence": "low",
                        "conflict": "",
                        "sources": [],
                    },
                },
                {
                    "type": "report",
                    "payload": {
                        "title": "Research task failed",
                        "summary": log.error or "The web search request failed.",
                        "highlights": [log.query],
                    },
                }
            ]

        domains = [source.domain or self._extract_domain(source.url) for source in log.sources if source.url]
        highlights = [f"{len(log.sources)} sources", *[domain for domain in dict.fromkeys(domains) if domain][:4]]
        if conflict:
            highlights.append(conflict)

        return [
                {
                    "type": "research_result",
                    "payload": {
                        "query": log.query,
                        "provider": log.provider,
                        "status": log.status,
                        "query_plan": query_plan,
                        "freshness": freshness,
                        "confidence": confidence,
                        "conflict": conflict,
                        "sources": [
                            {
                                "title": source.title,
                                "url": source.url,
                                "domain": source.domain or self._extract_domain(source.url),
                                "snippet": source.snippet,
                                "freshness": self._extract_source_date_text(source),
                                "authority": self._authority_label(source.domain or self._extract_domain(source.url)),
                            }
                            for source in log.sources[:6]
                        ],
                    },
                },
            {
                "type": "report",
                "payload": {
                    "title": "Research summary",
                    "summary": log.summary or f"Collected {len(log.sources)} sources for `{log.query}`.",
                    "highlights": highlights or [log.query],
                },
            },
            {
                "type": "file_result",
                "payload": {
                    "title": "Research sources",
                    "files": [
                        {
                            "path": source.url,
                            "summary": self._source_summary(source),
                        }
                        for source in log.sources[:8]
                    ],
                },
            },
        ]

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
        prepared_query: str = "",
        original_query: str = "",
    ) -> list[SearchSource]:
        sources: list[SearchSource] = []
        seen_urls: set[str] = set()
        collected: list[tuple[float, SearchSource]] = []
        preferred_domains = self._extract_requested_domains(original_query or prepared_query)
        prefer_freshness = self._should_prioritize_freshness(original_query or prepared_query)

        instant_url = self._normalize_result_url(instant_data.get("AbstractURL", ""))
        instant_text = (instant_data.get("AbstractText") or "").strip()
        instant_heading = (instant_data.get("Heading") or "Answer").strip()
        if instant_url and instant_text and not self._is_junk_search_result(
            instant_url, instant_heading, instant_text, prepared_query
        ):
            source = SearchSource(
                title=instant_heading,
                url=instant_url,
                snippet=instant_text,
                domain=self._extract_domain(instant_url),
            )
            seen_urls.add(instant_url)
            collected.append(
                (
                    self._score_result(
                        source.title,
                        source.url,
                        source.snippet,
                        prepared_query,
                        preferred_domains,
                        prefer_freshness,
                    )
                    + 0.75,
                    source,
                )
            )

        for _, results in result_sets:
            for result in results:
                normalized_url = self._normalize_result_url(result.get("url", ""))
                if not normalized_url or normalized_url in seen_urls:
                    continue
                title = (result.get("title") or normalized_url).strip()
                snippet = (result.get("snippet") or "").strip()
                if self._is_junk_search_result(normalized_url, title, snippet, prepared_query):
                    continue
                seen_urls.add(normalized_url)
                source = SearchSource(
                    title=title,
                    url=normalized_url,
                    snippet=snippet,
                    domain=self._extract_domain(normalized_url),
                )
                collected.append(
                    (
                        self._score_result(
                            title,
                            normalized_url,
                            snippet,
                            prepared_query,
                            preferred_domains,
                            prefer_freshness,
                        ),
                        source,
                    )
                )

        collected.sort(key=lambda item: item[0], reverse=True)
        for _, source in collected:
            if source.url in {item.url for item in sources}:
                continue
            sources.append(source)
            if len(sources) >= limit:
                break

        trimmed = sources[:limit]
        await self._parallel_enrich_sources(client, trimmed)
        return trimmed

    async def _run_query_variant(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        ddg_results, bing_results = await asyncio.gather(
            self._duckduckgo_html_results(client, query, limit),
            self._bing_rss_results(client, query, limit),
            return_exceptions=True,
        )
        return (
            [] if isinstance(ddg_results, BaseException) else ddg_results,
            [] if isinstance(bing_results, BaseException) else bing_results,
        )

    def _should_skip_enrich_url(self, url: str) -> bool:
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            return True
        if not host:
            return True
        for block in ("facebook.", "instagram.", "linkedin.", "twitter.", "x.com"):
            if block in host:
                return True
        return False

    async def _parallel_enrich_sources(
        self,
        client: httpx.AsyncClient,
        sources: list[SearchSource],
    ) -> None:
        if not sources:
            return
        coros = []
        indices: list[int] = []
        for i, src in enumerate(sources):
            if self._should_skip_enrich_url(src.url):
                continue
            deep = i < self._ENRICH_TOP_N
            needs_snippet = not (src.snippet or "").strip()
            if not deep and not needs_snippet:
                continue
            indices.append(i)
            coros.append(
                self._enrich_one_source(
                    client,
                    src.url,
                    deep=deep,
                    needs_snippet=needs_snippet,
                )
            )
        if not coros:
            return
        outcomes = await asyncio.gather(*coros, return_exceptions=True)
        for index, outcome in zip(indices, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                continue
            page_ex, snippet_fb = outcome
            target = sources[index]
            if page_ex:
                target.page_excerpt = page_ex
            if not (target.snippet or "").strip() and snippet_fb:
                target.snippet = snippet_fb[: self._SNIPPET_FALLBACK_CHARS]

    async def _enrich_one_source(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        deep: bool,
        needs_snippet: bool,
    ) -> tuple[str, str]:
        if self._url_content:
            if deep:
                text = await self._url_content.summarize_url_for_search(
                    url, client, max_chars=self._DEEP_PAGE_CHARS
                )
                snippet_fb = (
                    text[: self._SHALLOW_PAGE_CHARS].strip() if needs_snippet and text else ""
                )
                return (text, snippet_fb)
            if needs_snippet:
                host = urlparse(url).netloc.lower()
                cap = 900 if ("youtube.com" in host or "youtu.be" in host) else self._SHALLOW_PAGE_CHARS + 240
                text = await self._url_content.summarize_url_for_search(url, client, max_chars=cap)
                return ("", (text[: self._SNIPPET_FALLBACK_CHARS].strip() if text else ""))
            return ("", "")

        if deep:
            text = await self._fetch_visible_text(client, url, self._DEEP_PAGE_CHARS)
            snippet_fb = text[: self._SHALLOW_PAGE_CHARS].strip() if needs_snippet and text else ""
            return (text, snippet_fb)
        if needs_snippet:
            text = await self._fetch_visible_text(client, url, self._SHALLOW_PAGE_CHARS)
            return ("", (text[: self._SNIPPET_FALLBACK_CHARS].strip() if text else ""))
        return ("", "")

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

    async def _fetch_visible_text(self, client: httpx.AsyncClient, url: str, max_chars: int) -> str:
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
        title = html.unescape(" ".join(parser.title_parts)).strip()
        body = html.unescape(" ".join(parser.text_parts)).strip()
        body = re.sub(r"\s+", " ", body)
        if not body:
            return title[:max_chars] if title else ""
        combined = f"{title}: {body}" if title else body
        return combined[:max_chars]

    def _build_summary(self, prepared_query: str, sources: list[SearchSource]) -> str:
        if not sources:
            return "No search results were available for this query."

        price_summary = self._extract_price_summary(prepared_query, sources)
        if price_summary:
            return price_summary

        summaries: list[str] = []
        for source in sources:
            if source.page_excerpt:
                summaries.append(source.page_excerpt[:420])
            elif source.snippet:
                summaries.append(source.snippet)
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
            haystack = " ".join(
                part for part in [source.title, source.snippet, source.page_excerpt] if part
            )
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

    def _detect_numeric_conflict(self, sources: list[SearchSource]) -> str:
        pattern = re.compile(
            r"(?<!\d)(?:usd\s*)?\$?\s*([1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?|[1-9]\d{2,6}(?:\.\d+)?)(?!\d)"
        )
        values: list[float] = []
        for source in sources[:6]:
            haystack = " ".join(part for part in [source.title, source.snippet, source.page_excerpt] if part)
            for match in pattern.findall(haystack):
                values.append(float(match.replace(",", "")))
                break
        if len(values) < 2:
            return ""
        low = min(values)
        high = max(values)
        if low <= 0:
            return ""
        spread = (high - low) / low
        if spread >= 0.1:
            return f"Potential source conflict: numeric signals vary from {low:,.2f} to {high:,.2f}"
        return ""

    def _source_summary(self, source: SearchSource) -> str:
        pieces = []
        if source.domain:
            pieces.append(source.domain)
        if source.snippet:
            pieces.append(source.snippet[:280])
        elif source.page_excerpt:
            pieces.append(source.page_excerpt[:280])
        return " | ".join(piece for piece in pieces if piece)

    def _estimate_freshness(self, sources: list[SearchSource]) -> str:
        years: list[int] = []
        for source in sources[:6]:
            parsed = self._extract_source_datetime(source)
            if parsed is not None and 2020 <= parsed.year <= 2035:
                years.append(parsed.year)
        if not years:
            return ""
        latest = max(years)
        if latest >= 2026:
            return f"Signals suggest very recent coverage ({latest})."
        if latest >= 2024:
            return f"Signals suggest recent coverage ({latest})."
        return f"Newest visible date signal is {latest}."

    def _estimate_confidence(self, sources: list[SearchSource], conflict: str) -> str:
        if not sources:
            return "low"
        score = 0.0
        for source in sources[:4]:
            domain = source.domain or self._extract_domain(source.url)
            authority = self._authority_score(domain)
            score += authority
            if source.page_excerpt:
                score += 0.4
            elif source.snippet:
                score += 0.2
        if conflict:
            score -= 1.0
        average = score / max(min(len(sources), 4), 1)
        if average >= 1.6:
            return "high"
        if average >= 0.9:
            return "medium"
        return "low"

    def _authority_score(self, domain: str) -> float:
        if not domain:
            return 0.0
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return 2.0
        if any(token in domain for token in ("docs.", "developer.", "support.", "api.")):
            return 1.5
        if domain.count(".") >= 1:
            return 1.0
        return 0.5

    def _authority_label(self, domain: str) -> str:
        score = self._authority_score(domain)
        if score >= 1.8:
            return "official"
        if score >= 1.3:
            return "documentation"
        if score >= 1.0:
            return "standard"
        return "unknown"

    def _extract_source_date_text(self, source: SearchSource) -> str:
        text = " ".join(part for part in [source.title, source.snippet, source.page_excerpt] if part)
        candidates = re.findall(r"\b(?:20\d{2}|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b", text)
        if not candidates:
            return ""
        return " ".join(candidates[:3])

    def _extract_source_datetime(self, source: SearchSource) -> datetime | None:
        text = " ".join(part for part in [source.title, source.snippet, source.page_excerpt] if part)
        month_map = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }

        full_date = re.search(
            r"\b(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(20\d{2})|(20\d{2})-(\d{2})-(\d{2}))\b",
            text,
            re.IGNORECASE,
        )
        if full_date:
            if full_date.group(4):
                try:
                    return datetime(
                        int(full_date.group(4)),
                        int(full_date.group(5)),
                        int(full_date.group(6)),
                        tzinfo=UTC,
                    )
                except ValueError:
                    return None
            month_name = (full_date.group(1) or "").lower()
            day = int(full_date.group(2))
            year = int(full_date.group(3))
            month = month_map.get(month_name)
            if month:
                try:
                    return datetime(year, month, day, tzinfo=UTC)
                except ValueError:
                    return None

        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            return datetime(int(year_match.group(1)), 1, 1, tzinfo=UTC)
        return None

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

    def _wants_google_search_help_docs(self, lowered: str) -> bool:
        if "google" not in lowered:
            return False
        hints = (
            "google search help",
            "how to search on google",
            "google search history",
            "search history",
            "web & app activity",
            "delete google search",
            "google search settings",
            "change google search",
            "safe search",
        )
        return any(h in lowered for h in hints)

    def _is_junk_search_result(
        self,
        url: str,
        title: str,
        snippet: str,
        prepared_query: str,
    ) -> bool:
        if self._wants_google_search_help_docs(prepared_query.lower()):
            return False
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower().removeprefix("www.")
            path_l = (parsed.path or "").lower()
        except Exception:
            return False
        blob = f"{title} {snippet}".lower()
        if host == "support.google.com":
            if "/websearch" in path_l:
                return True
            if "google search help" in blob:
                return True
        return False

    def _filter_engine_results(
        self,
        results: list[dict[str, str]],
        prepared_query: str,
    ) -> list[dict[str, str]]:
        filtered: list[dict[str, str]] = []
        for row in results:
            url = self._normalize_result_url(row.get("url", ""))
            title = (row.get("title") or "").strip()
            snippet = (row.get("snippet") or "").strip()
            if self._is_junk_search_result(url, title, snippet, prepared_query):
                continue
            filtered.append(row)
        return filtered

    def _prepare_query(self, query: str) -> str:
        normalized = query.strip()
        lowered = normalized.lower()

        lowered = re.sub(
            r"^\s*(?:copy\s+)?(?:please\s+|can you\s+)?"
            r"(?:(?:web|bing|duckduckgo|ddg|google)\s+)?"
            r"search\s+(?:on\s+(?:the\s+)?(?:web|internet)\s+)?(?:for\s+)?",
            " ",
            lowered,
            count=1,
        )
        lowered = re.sub(
            r"\b(?:web|bing|google)\s+search\s+for\b",
            " ",
            lowered,
        )
        cleanup_patterns = [
            r"\bsearch (?:on|the)?\s*(?:internet|web)\b",
            r"\bseach (?:on|the)?\s*(?:internet|web)\b",
            r"\bsearch online\b",
            r"\bgoogle\s+search\s+for\b",
            r"\bsearch\s+google\s+for\b",
            r"\bon\s+google\s+for\b",
            r"\blook up\b",
            r"\bfind information about\b",
            r"\bcan you\b",
            r"\btry to\b",
            r"\bplease\b",
        ]
        for pattern in cleanup_patterns:
            lowered = re.sub(pattern, " ", lowered)
        # Do not strip "." — it breaks hostnames (e.g. krak.dk) and phone formatting.
        lowered = re.sub(r"[?!]+", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered).strip()

        site_match = re.search(
            r"\bon\s+([a-z0-9][a-z0-9.-]*\.[a-z]{2,})\b",
            lowered,
        )
        if site_match:
            site = site_match.group(1).lower()
            noise_domains = frozenset(
                {
                    "google.com",
                    "google.dk",
                    "gmail.com",
                    "youtube.com",
                    "youtu.be",
                }
            )
            if site not in noise_domains and f"site:{site}" not in lowered:
                lowered = f"{lowered} site:{site}"

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

    def _build_query_variants(self, original_query: str, prepared_query: str) -> list[str]:
        variants: list[str] = []
        preferred_domains = self._extract_requested_domains(original_query)
        prefer_freshness = self._should_prioritize_freshness(original_query)

        def add_variant(value: str) -> None:
            candidate = re.sub(r"\s+", " ", value.strip())
            if candidate and candidate not in variants:
                variants.append(candidate)

        add_variant(prepared_query)

        if preferred_domains:
            for domain in preferred_domains[:2]:
                if f"site:{domain}" not in prepared_query:
                    add_variant(f"{prepared_query} site:{domain}")

        if prefer_freshness:
            add_variant(f"{prepared_query} latest")
            add_variant(f"{prepared_query} current")

        return variants[: self._MAX_QUERY_VARIANTS]

    def _extract_requested_domains(self, text: str) -> list[str]:
        matches = re.findall(r"\bsite:([a-z0-9][a-z0-9.-]*\.[a-z]{2,})\b", text.lower())
        return list(dict.fromkeys(matches))

    def _should_prioritize_freshness(self, text: str) -> bool:
        lower = text.lower()
        freshness_markers = (
            "latest",
            "recent",
            "today",
            "current",
            "news",
            "this year",
            "right now",
            "new",
            "update",
            "updated",
        )
        return any(marker in lower for marker in freshness_markers)

    def _score_result(
        self,
        title: str,
        url: str,
        snippet: str,
        prepared_query: str,
        preferred_domains: list[str],
        prefer_freshness: bool,
    ) -> float:
        haystack = f"{title} {snippet}".lower()
        tokens = [token for token in re.findall(r"[a-z0-9]{3,}", prepared_query.lower()) if token not in {"latest", "current"}]
        overlap = sum(1 for token in tokens if token in haystack)
        score = float(overlap)
        domain = self._extract_domain(url)
        if preferred_domains and any(domain.endswith(preferred) for preferred in preferred_domains):
            score += 4.0
        if any(domain.endswith(official) for official in (".gov", ".edu")):
            score += 1.0
        if any(marker in domain for marker in ("docs.", "developer.", "support.")):
            score += 0.75
        if prefer_freshness:
            if any(marker in haystack for marker in ("today", "latest", "updated", "current")):
                score += 1.0
            parsed = self._extract_source_datetime(
                SearchSource(title=title, url=url, snippet=snippet, domain=domain)
            )
            if parsed is not None:
                age_days = max((datetime.now(UTC) - parsed).days, 0)
                if age_days <= 30:
                    score += 2.0
                elif age_days <= 180:
                    score += 1.5
                elif age_days <= 365:
                    score += 1.0
                elif parsed.year >= 2024:
                    score += 0.5
        return score

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
    return SearchService(
        artifact_service=get_artifact_service(),
        url_content_service=get_url_content_service(),
    )
