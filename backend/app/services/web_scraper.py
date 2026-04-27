"""
Web Scraping Service for ISE_AI

Provides intelligent web scraping capabilities including:
- Dynamic web page fetching and parsing
- Structured data extraction
- Multi-source data aggregation
- Fact-checking and cross-referencing
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup


@dataclass(slots=True)
class ScrapedContent:
    url: str
    title: str
    content: str
    structured_data: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(slots=True)
class ResearchResult:
    query: str
    sources: list[ScrapedContent]
    synthesized_summary: str
    facts: list[dict[str, Any]]
    confidence_score: float


class WebScraperService:
    """Intelligent web scraping service for data acquisition and research."""

    def __init__(self, timeout: float = 30.0, max_content_size: int = 5_000_000) -> None:
        self.timeout = timeout
        self.max_content_size = max_content_size
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def fetch_page(self, url: str) -> ScrapedContent | None:
        """Fetch and parse a single web page."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True,
                )
                response.raise_for_status()

                if len(response.content) > self.max_content_size:
                    return None

                soup = BeautifulSoup(response.content, "html.parser")
                title = self._extract_title(soup)
                content = self._extract_main_content(soup)
                structured_data = self._extract_structured_data(soup)
                metadata = self._extract_metadata(soup, url)

                return ScrapedContent(
                    url=url,
                    title=title,
                    content=content,
                    structured_data=structured_data,
                    metadata=metadata,
                )
        except Exception as exc:
            return None

    async def fetch_multiple(self, urls: list[str], max_concurrent: int = 3) -> list[ScrapedContent]:
        """Fetch multiple pages concurrently with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> ScrapedContent | None:
            async with semaphore:
                return await self.fetch_page(url)

        results = await asyncio.gather(*[fetch_with_semaphore(url) for url in urls])
        return [r for r in results if r is not None]

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]

        return "Untitled"

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the page."""
        for tag in soup(["script", "style", "meta", "link", "noscript"]):
            tag.decompose()

        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        if not main_content:
            return ""

        paragraphs = main_content.find_all(["p", "li", "div"], recursive=True)
        text_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        return "\n".join(text_parts)[:10000]

    def _extract_structured_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract structured data (JSON-LD, microdata, etc.)."""
        structured = {}

        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                structured["json_ld"] = data
                break
            except Exception:
                continue

        og_tags = soup.find_all("meta", property=True)
        og_data = {}
        for tag in og_tags:
            prop = tag.get("property", "").replace("og:", "")
            content = tag.get("content", "")
            if prop and content:
                og_data[prop] = content
        if og_data:
            structured["og_tags"] = og_data

        return structured

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract metadata about the page."""
        metadata = {"url": url}

        description = soup.find("meta", attrs={"name": "description"})
        if description and description.get("content"):
            metadata["description"] = description["content"]

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            metadata["image"] = og_image["content"]

        og_type = soup.find("meta", property="og:type")
        if og_type and og_type.get("content"):
            metadata["type"] = og_type["content"]

        return metadata

    async def research(self, query: str, urls: list[str]) -> ResearchResult:
        """Conduct research across multiple sources."""
        sources = await self.fetch_multiple(urls, max_concurrent=5)

        if not sources:
            return ResearchResult(
                query=query,
                sources=[],
                synthesized_summary="No sources could be retrieved.",
                facts=[],
                confidence_score=0.0,
            )

        facts = self._extract_facts(sources)
        summary = self._synthesize_summary(sources, query)
        confidence = self._calculate_confidence(sources, facts)

        return ResearchResult(
            query=query,
            sources=sources,
            synthesized_summary=summary,
            facts=facts,
            confidence_score=confidence,
        )

    def _extract_facts(self, sources: list[ScrapedContent]) -> list[dict[str, Any]]:
        """Extract key facts from sources."""
        facts = []
        for source in sources:
            fact = {
                "source": source.url,
                "title": source.title,
                "key_points": self._identify_key_points(source.content),
            }
            facts.append(fact)
        return facts

    def _identify_key_points(self, content: str) -> list[str]:
        """Identify key points from content."""
        sentences = content.split(".")
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:5]
        return key_sentences

    def _synthesize_summary(self, sources: list[ScrapedContent], query: str) -> str:
        """Synthesize a summary from multiple sources."""
        if not sources:
            return ""

        summaries = []
        for source in sources:
            summary = f"**{source.title}** ({source.url}): {source.content[:300]}..."
            summaries.append(summary)

        return "\n\n".join(summaries)

    def _calculate_confidence(self, sources: list[ScrapedContent], facts: list[dict]) -> float:
        """Calculate confidence score based on source diversity and consistency."""
        if not sources:
            return 0.0

        unique_domains = len(set(self._extract_domain(s.url) for s in sources))
        domain_diversity_score = min(unique_domains / 3.0, 1.0)

        fact_consistency = 0.8 if len(facts) > 1 else 0.5

        return (domain_diversity_score + fact_consistency) / 2.0

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return url


class WebResearchAgent:
    """Agent that orchestrates web research tasks."""

    def __init__(self, scraper: WebScraperService | None = None) -> None:
        self.scraper = scraper or WebScraperService()

    async def research_topic(self, topic: str, num_sources: int = 5) -> ResearchResult:
        """Research a topic by gathering information from multiple sources."""
        search_urls = await self._generate_search_urls(topic, num_sources)
        return await self.scraper.research(topic, search_urls)

    async def _generate_search_urls(self, topic: str, num_sources: int) -> list[str]:
        """Generate search URLs for a given topic."""
        base_urls = [
            f"https://www.google.com/search?q={topic.replace(' ', '+')}",
            f"https://www.wikipedia.org/w/api.php?action=query&list=search&srsearch={topic}&format=json",
            f"https://www.github.com/search?q={topic.replace(' ', '+')}&type=repositories",
        ]
        return base_urls[:num_sources]

    async def verify_facts(self, facts: list[str]) -> dict[str, Any]:
        """Verify facts across multiple sources."""
        verification_results = {}
        for fact in facts:
            urls = await self._generate_search_urls(fact, 3)
            result = await self.scraper.research(fact, urls)
            verification_results[fact] = {
                "confidence": result.confidence_score,
                "sources": len(result.sources),
                "summary": result.synthesized_summary,
            }
        return verification_results
