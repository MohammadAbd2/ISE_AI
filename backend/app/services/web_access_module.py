"""
Web Access Module - Enable AI agents to fetch real-time information from the internet.
Supports multiple search providers, caching, and source attribution.
"""

import requests
import json
import hashlib
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SearchProvider(Enum):
    """Supported search providers"""
    GOOGLE = "google"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    PERPLEXITY = "perplexity"


@dataclass
class SearchResult:
    """Represents a single search result"""
    title: str
    url: str
    snippet: str
    source: str
    freshness: str = ""
    confidence: float = 0.9
    
    def to_dict(self):
        return asdict(self)


@dataclass
class WebSearchQuery:
    """Represents a web search query"""
    query: str
    provider: SearchProvider = SearchProvider.GOOGLE
    max_results: int = 5
    include_news: bool = False
    language: str = "en"
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self):
        return {
            "query": self.query,
            "provider": self.provider.value,
            "max_results": self.max_results,
            "include_news": self.include_news,
            "language": self.language,
            "timestamp": self.timestamp
        }


@dataclass
class ScrapedContent:
    """Represents scraped web content"""
    url: str
    title: str
    content: str
    source: str
    last_updated: str = ""
    word_count: int = 0
    
    def to_dict(self):
        return asdict(self)


class CacheManager:
    """Manage cache of web search results and scraped content"""
    
    def __init__(self, cache_dir: str = ".web_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_expiry = timedelta(hours=24)
    
    def _get_cache_key(self, query: str, provider: str) -> str:
        """Generate cache key from query and provider"""
        key_str = f"{query}_{provider}".encode()
        return hashlib.sha256(key_str).hexdigest()
    
    def get_cached_results(self, query: str, provider: str) -> Optional[List[Dict]]:
        """Retrieve cached search results if still valid"""
        cache_key = self._get_cache_key(query, provider)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still fresh
            cached_time = datetime.fromisoformat(cached.get('timestamp', ''))
            if datetime.now() - cached_time < self.cache_expiry:
                logger.info(f"Using cached results for: {query}")
                return cached.get('results')
            else:
                cache_file.unlink()
                return None
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def cache_results(self, query: str, provider: str, results: List[Dict]):
        """Store search results in cache"""
        cache_key = self._get_cache_key(query, provider)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cached_data = {
                'query': query,
                'provider': provider,
                'timestamp': datetime.now().isoformat(),
                'results': results
            }
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def clear_old_cache(self):
        """Remove expired cache entries"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if not cache_file.is_file():
                    continue
                
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                
                cached_time = datetime.fromisoformat(cached.get('timestamp', ''))
                if datetime.now() - cached_time > self.cache_expiry:
                    cache_file.unlink()
                    logger.info(f"Removed expired cache: {cache_file.name}")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")


class WebSearchEngine:
    """Core web search engine with provider abstraction"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache = CacheManager() if cache_enabled else None
        self.rate_limit_delay = 0.5
        self.last_request_time = 0
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def search(self, query: WebSearchQuery) -> List[SearchResult]:
        """Execute web search with specified provider"""
        # Check cache first
        if self.cache:
            cached = self.cache.get_cached_results(query.query, query.provider.value)
            if cached:
                return [SearchResult(**result) for result in cached]
        
        self._apply_rate_limit()
        
        # Route to appropriate provider
        if query.provider == SearchProvider.GOOGLE:
            results = self._search_google(query)
        elif query.provider == SearchProvider.BRAVE:
            results = self._search_brave(query)
        elif query.provider == SearchProvider.DUCKDUCKGO:
            results = self._search_duckduckgo(query)
        elif query.provider == SearchProvider.PERPLEXITY:
            results = self._search_perplexity(query)
        else:
            results = []
        
        # Cache results
        if self.cache and results:
            self.cache.cache_results(
                query.query,
                query.provider.value,
                [r.to_dict() for r in results]
            )
        
        return results
    
    def _search_google(self, query: WebSearchQuery) -> List[SearchResult]:
        """Search using Google Custom Search API (requires API key)"""
        # This is a template - requires GOOGLE_API_KEY and SEARCH_ENGINE_ID
        api_key = "YOUR_GOOGLE_API_KEY"  # Set via environment
        engine_id = "YOUR_SEARCH_ENGINE_ID"
        
        if api_key == "YOUR_GOOGLE_API_KEY":
            logger.warning("Google API key not configured, using simulated results")
            return self._simulate_google_results(query)
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'q': query.query,
                'key': api_key,
                'cx': engine_id,
                'num': query.max_results,
                'lr': f'lang_{query.language}'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            results = []
            for item in response.json().get('items', [])[:query.max_results]:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source='Google Search'
                ))
            
            return results
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
    
    def _search_brave(self, query: WebSearchQuery) -> List[SearchResult]:
        """Search using Brave Search API"""
        api_key = "YOUR_BRAVE_API_KEY"  # Set via environment
        
        if api_key == "YOUR_BRAVE_API_KEY":
            logger.warning("Brave API key not configured, using simulated results")
            return self._simulate_brave_results(query)
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
            params = {"q": query.query, "count": query.max_results}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            results = []
            for item in response.json().get('web', {}).get('results', [])[:query.max_results]:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('description', ''),
                    source='Brave Search'
                ))
            
            return results
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []
    
    def _search_duckduckgo(self, query: WebSearchQuery) -> List[SearchResult]:
        """Search using DuckDuckGo (no API key required)"""
        try:
            # DuckDuckGo instant answer API (free)
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query.query,
                "format": "json",
                "pretty": 1,
                "no_redirect": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            results = []
            data = response.json()
            
            # Use related topics if available
            for topic in data.get('RelatedTopics', [])[:query.max_results]:
                if isinstance(topic, dict):
                    results.append(SearchResult(
                        title=topic.get('Text', ''),
                        url=topic.get('FirstURL', ''),
                        snippet=topic.get('Text', ''),
                        source='DuckDuckGo'
                    ))
            
            return results[:query.max_results]
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def _search_perplexity(self, query: WebSearchQuery) -> List[SearchResult]:
        """Search using Perplexity AI API"""
        api_key = "YOUR_PERPLEXITY_API_KEY"
        
        if api_key == "YOUR_PERPLEXITY_API_KEY":
            logger.warning("Perplexity API key not configured")
            return []
        
        try:
            # Perplexity API endpoint for search
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "pplx-7b-online",
                "messages": [{"role": "user", "content": query.query}],
                "max_tokens": 500
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Perplexity returns structured response with citations
            results = []
            content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            
            results.append(SearchResult(
                title="Perplexity AI Response",
                url="https://www.perplexity.ai",
                snippet=content,
                source='Perplexity AI'
            ))
            
            return results
        except Exception as e:
            logger.error(f"Perplexity search error: {e}")
            return []
    
    def _simulate_google_results(self, query: WebSearchQuery) -> List[SearchResult]:
        """Simulate Google search results for demonstration"""
        return [
            SearchResult(
                title=f"Results for '{query.query}' - Source 1",
                url=f"https://example.com/search?q={query.query}",
                snippet=f"Information about {query.query}. This is simulated content.",
                source='Google Search (Simulated)'
            ),
            SearchResult(
                title=f"More info: {query.query}",
                url=f"https://wiki.example.com/{query.query}",
                snippet=f"Additional details and insights about {query.query}.",
                source='Google Search (Simulated)'
            )
        ]
    
    def _simulate_brave_results(self, query: WebSearchQuery) -> List[SearchResult]:
        """Simulate Brave search results for demonstration"""
        return [
            SearchResult(
                title=f"Brave results for '{query.query}'",
                url=f"https://brave.com/search?q={query.query}",
                snippet=f"Privacy-focused results about {query.query}.",
                source='Brave Search (Simulated)'
            )
        ]
    
    def multi_provider_search(self, query: str, providers: List[SearchProvider] = None,
                            max_results: int = 3) -> Dict[str, List[SearchResult]]:
        """Search across multiple providers and combine results"""
        if providers is None:
            providers = [SearchProvider.DUCKDUCKGO, SearchProvider.GOOGLE]
        
        all_results = {}
        for provider in providers:
            search_query = WebSearchQuery(
                query=query,
                provider=provider,
                max_results=max_results
            )
            all_results[provider.value] = self.search(search_query)
        
        return all_results


class WebContentScraper:
    """Scrape and extract content from web pages"""
    
    def __init__(self):
        self.timeout = 10
        self.max_content_length = 50000
    
    def scrape(self, url: str) -> Optional[ScrapedContent]:
        """Scrape content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Simple text extraction (production would use BeautifulSoup)
            content = response.text[:self.max_content_length]
            
            return ScrapedContent(
                url=url,
                title=response.headers.get('title', 'Unknown'),
                content=content,
                source='Web Scraper',
                last_updated=datetime.now().isoformat(),
                word_count=len(content.split())
            )
        except Exception as e:
            logger.error(f"Scrape error for {url}: {e}")
            return None


class WebAccessManager:
    """Main manager for web access functionality"""
    
    def __init__(self, cache_enabled: bool = True):
        self.search_engine = WebSearchEngine(cache_enabled=cache_enabled)
        self.scraper = WebContentScraper()
        self.search_history = []
    
    def search(self, query: str, provider: SearchProvider = SearchProvider.DUCKDUCKGO,
              max_results: int = 5) -> List[SearchResult]:
        """Perform a web search"""
        search_query = WebSearchQuery(
            query=query,
            provider=provider,
            max_results=max_results
        )
        
        results = self.search_engine.search(search_query)
        
        # Record in history
        self.search_history.append({
            'query': query,
            'provider': provider.value,
            'timestamp': datetime.now().isoformat(),
            'result_count': len(results)
        })
        
        logger.info(f"Search completed: {query} ({len(results)} results)")
        return results
    
    def search_and_scrape(self, query: str, scrape_top: int = 2) -> Dict[str, Any]:
        """Search and scrape top results"""
        search_results = self.search(query, max_results=5)
        
        scraped_content = []
        for result in search_results[:scrape_top]:
            content = self.scraper.scrape(result.url)
            if content:
                scraped_content.append(content)
        
        return {
            'query': query,
            'search_results': [r.to_dict() for r in search_results],
            'scraped_content': [c.to_dict() for c in scraped_content],
            'timestamp': datetime.now().isoformat()
        }
    
    def get_search_history(self) -> List[Dict]:
        """Get search history"""
        return self.search_history
    
    def clear_cache(self):
        """Clear web access cache"""
        if self.search_engine.cache:
            self.search_engine.cache.clear_old_cache()
            logger.info("Web access cache cleared")


# Convenience functions
_global_manager = None


def get_web_access() -> WebAccessManager:
    """Get or create global web access manager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = WebAccessManager(cache_enabled=True)
    return _global_manager


def web_search(query: str, provider: str = "duckduckgo") -> List[Dict]:
    """Convenience function for web search"""
    try:
        provider_enum = SearchProvider(provider)
    except ValueError:
        provider_enum = SearchProvider.DUCKDUCKGO
    
    manager = get_web_access()
    results = manager.search(query, provider=provider_enum)
    return [r.to_dict() for r in results]


def web_search_and_scrape(query: str, scrape_top: int = 2) -> Dict:
    """Convenience function for search and scrape"""
    manager = get_web_access()
    return manager.search_and_scrape(query, scrape_top=scrape_top)
