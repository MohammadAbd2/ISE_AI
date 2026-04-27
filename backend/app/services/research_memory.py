"""
Research Memory Service

Caches search results to avoid redundant internet searches.
Automatically stores researched information for future retrieval.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

import aiofiles

from app.schemas.chat import SearchSource, WebSearchLog


@dataclass
class CachedResearch:
    """A cached research result."""
    query: str
    query_hash: str
    summary: str
    sources: list[dict]
    content: str
    created_at: str
    last_accessed: str
    access_count: int = 1
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "query_hash": self.query_hash,
            "summary": self.summary,
            "sources": self.sources,
            "content": self.content,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CachedResearch":
        return cls(
            query=data["query"],
            query_hash=data["query_hash"],
            summary=data.get("summary", ""),
            sources=data.get("sources", []),
            content=data.get("content", ""),
            created_at=data["created_at"],
            last_accessed=data.get("last_accessed", data["created_at"]),
            access_count=data.get("access_count", 1),
            tags=data.get("tags", []),
        )


class ResearchMemoryService:
    """
    Service for caching research results and managing research memory.
    
    Features:
    1. Caches search results to avoid redundant internet searches
    2. Automatically extracts and stores key facts from research
    3. Provides context for future similar queries
    4. Tracks research freshness and relevance
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path.cwd() / ".ise_ai_learning" / "research_memory"
        
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.storage_path / "research_cache.json"
        self.facts_file = self.storage_path / "research_facts.json"
        
        # In-memory cache
        self._cache: dict[str, CachedResearch] = {}
        self._research_facts: dict[str, list[str]] = {}  # topic -> list of facts
        
        # Load from disk
        self._load_cache()
        self._load_facts()

    def _compute_query_hash(self, query: str) -> str:
        """Compute a hash for a query to use as cache key."""
        # Normalize query for better cache hits
        normalized = query.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?!.]+$', '', normalized)  # Remove trailing punctuation
        return hashlib.md5(normalized.encode()).hexdigest()

    def _normalize_query_for_matching(self, query: str) -> str:
        """Normalize query for semantic matching."""
        normalized = query.lower().strip()
        # Remove common filler words
        stop_words = ['what', 'is', 'are', 'the', 'a', 'an', 'can', 'you', 'tell', 'me', 'about', 'do', 'know']
        words = normalized.split()
        words = [w for w in words if w not in stop_words]
        return ' '.join(words)

    def find_cached_research(self, query: str, similarity_threshold: float = 0.8) -> Optional[CachedResearch]:
        """
        Find cached research results similar to the query.
        
        Returns cached result if found, None otherwise.
        """
        query_hash = self._compute_query_hash(query)
        
        # Exact match
        if query_hash in self._cache:
            cached = self._cache[query_hash]
            cached.last_accessed = datetime.now(UTC).isoformat()
            cached.access_count += 1
            return cached
        
        # Semantic match - check if we have similar research
        normalized_query = self._normalize_query_for_matching(query)
        query_words = set(normalized_query.split())
        
        best_match = None
        best_score = 0.0
        
        for hash_key, cached in self._cache.items():
            cached_normalized = self._normalize_query_for_matching(cached.query)
            cached_words = set(cached_normalized.split())
            
            if not query_words or not cached_words:
                continue
            
            # Calculate similarity
            intersection = query_words & cached_words
            union = query_words | cached_words
            similarity = len(intersection) / len(union) if union else 0
            
            if similarity > best_score and similarity >= similarity_threshold:
                best_score = similarity
                best_match = cached
        
        if best_match:
            best_match.last_accessed = datetime.now(UTC).isoformat()
            best_match.access_count += 1
            return best_match
        
        return None

    async def cache_research(self, search_log: WebSearchLog, content: str = ""):
        """Cache research results for future use."""
        query_hash = self._compute_query_hash(search_log.query)
        
        cached = CachedResearch(
            query=search_log.query,
            query_hash=query_hash,
            summary=search_log.summary or "",
            sources=[source.model_dump() for source in search_log.sources],
            content=content or search_log.summary or "",
            created_at=datetime.now(UTC).isoformat(),
            last_accessed=datetime.now(UTC).isoformat(),
            access_count=1,
            tags=self._extract_tags(search_log.query),
        )
        
        self._cache[query_hash] = cached
        
        # Extract and store key facts
        await self._extract_and_store_facts(search_log)
        
        # Save to disk
        self._save_cache()

    async def _extract_and_store_facts(self, search_log: WebSearchLog):
        """Extract key facts from search results and store them."""
        facts = []
        
        # Extract facts from summary
        if search_log.summary:
            # Split summary into sentences
            sentences = re.split(r'(?<=[.!?])\s+', search_log.summary)
            facts.extend([s.strip() for s in sentences if len(s.strip()) > 20])
        
        # Extract facts from sources
        for source in search_log.sources[:3]:  # Top 3 sources
            if source.snippet and len(source.snippet) > 30:
                # Take first sentence or meaningful chunk
                first_sentence = source.snippet.split('.')[0].strip()
                if len(first_sentence) > 20:
                    facts.append(first_sentence)
        
        if facts:
            # Store under query topic
            topic = self._extract_topic(search_log.query)
            if topic not in self._research_facts:
                self._research_facts[topic] = []
            
            # Add new facts (avoid duplicates)
            existing = set(self._research_facts[topic])
            for fact in facts:
                if fact not in existing:
                    self._research_facts[topic].append(fact)
                    existing.add(fact)
            
            # Save facts to disk
            self._save_facts()

    def _extract_topic(self, query: str) -> str:
        """Extract main topic from query."""
        # Simple topic extraction - take key nouns/phrases
        query_lower = query.lower()
        
        # Remove question words and common prefixes
        prefixes = ['what is', 'what are', 'who is', 'who are', 'when did', 'where is', 'how does', 'why is', 'tell me about', 'explain']
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                query_lower = query_lower[len(prefix):].strip()
                break
        
        # Take first few words as topic
        words = query_lower.split()[:5]
        topic = ' '.join(words)
        
        return topic if topic else query_lower

    def _extract_tags(self, query: str) -> list[str]:
        """Extract tags from query for better categorization."""
        tags = []
        query_lower = query.lower()
        
        # Technology tags
        tech_keywords = ['python', 'javascript', 'react', 'node', 'fastapi', 'django', 'flask', 'typescript', 'vue', 'angular']
        for tech in tech_keywords:
            if tech in query_lower:
                tags.append(tech)
        
        # Topic type tags
        if any(word in query_lower for word in ['price', 'cost', 'market', 'stock']):
            tags.append('finance')
        if any(word in query_lower for word in ['weather', 'temperature', 'forecast']):
            tags.append('weather')
        if any(word in query_lower for word in ['news', 'latest', 'recent', 'today']):
            tags.append('news')
        if any(word in query_lower for word in ['how to', 'tutorial', 'guide', 'learn']):
            tags.append('tutorial')
        
        return tags

    def get_research_context(self, query: str, max_facts: int = 10) -> list[str]:
        """Get research context for a query from stored facts."""
        topic = self._extract_topic(query)
        query_words = set(self._normalize_query_for_matching(query).split())
        
        context = []
        
        # Find related facts
        for fact_topic, facts in self._research_facts.items():
            topic_words = set(fact_topic.split())
            
            # Calculate relevance
            if topic_words and query_words:
                intersection = topic_words & query_words
                if intersection:
                    context.extend(facts[:max_facts])
        
        return context[:max_facts]

    def get_research_stats(self) -> dict:
        """Get statistics about cached research."""
        total_queries = len(self._cache)
        total_accesses = sum(c.access_count for c in self._cache.values())
        total_facts = sum(len(facts) for facts in self._research_facts.values())
        
        return {
            "cached_queries": total_queries,
            "total_accesses": total_accesses,
            "stored_facts": total_facts,
            "topics_covered": list(self._research_facts.keys())[:20],
        }

    def _load_cache(self):
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    for hash_key, item_data in data.items():
                        self._cache[hash_key] = CachedResearch.from_dict(item_data)
            except Exception as e:
                print(f"Error loading research cache: {e}")

    def _save_cache(self):
        """Save cache to disk."""
        try:
            data = {k: v.to_dict() for k, v in self._cache.items()}
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving research cache: {e}")

    def _load_facts(self):
        """Load facts from disk."""
        if self.facts_file.exists():
            try:
                with open(self.facts_file, 'r') as f:
                    self._research_facts = json.load(f)
            except Exception as e:
                print(f"Error loading research facts: {e}")

    def _save_facts(self):
        """Save facts to disk."""
        try:
            with open(self.facts_file, 'w') as f:
                json.dump(self._research_facts, f, indent=2)
        except Exception as e:
            print(f"Error saving research facts: {e}")

    def clear_cache(self):
        """Clear all cached research."""
        self._cache.clear()
        self._save_cache()

    def clear_facts(self):
        """Clear all stored facts."""
        self._research_facts.clear()
        self._save_facts()


@lru_cache
def get_research_memory_service() -> ResearchMemoryService:
    """Get or create research memory service instance."""
    return ResearchMemoryService()
