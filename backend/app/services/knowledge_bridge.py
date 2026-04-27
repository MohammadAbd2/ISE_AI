"""
Knowledge Bridge - Connect real-time web data to agent reasoning and decision-making.
Enables agents to augment their knowledge with current internet information.
"""

import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

from web_access_module import (
    WebAccessManager, SearchResult, ScrapedContent, SearchProvider
)

logger = logging.getLogger(__name__)


@dataclass
class WebDataSource:
    """Represents a web data source for agents"""
    title: str
    url: str
    snippet: str
    source_type: str  # 'search_result' or 'scraped_content'
    freshness: str
    relevance_score: float
    timestamp: str


@dataclass
class EnrichedKnowledge:
    """Knowledge enriched with web data"""
    query: str
    base_knowledge: str
    web_sources: List[WebDataSource]
    synthesized_answer: str
    confidence: float
    timestamp: str


class WebDataValidator:
    """Validate and score web data for quality and relevance"""
    
    def __init__(self):
        self.trustworthy_domains = {
            'wikipedia.org', 'github.com', 'github.io',
            'arxiv.org', 'research.google', 'scholar.google.com',
            'medium.com', 'dev.to', 'stackoverflow.com'
        }
        self.low_quality_domains = {
            'random-spam.com', 'advertisement.com'
        }
    
    def score_source(self, url: str, snippet: str, title: str) -> float:
        """Score source credibility (0-1)"""
        score = 0.5  # Base score
        
        # Domain reputation
        for domain in self.trustworthy_domains:
            if domain in url:
                score += 0.3
                break
        
        for domain in self.low_quality_domains:
            if domain in url:
                score -= 0.2
                break
        
        # Content quality indicators
        if len(snippet) > 100:
            score += 0.1
        if len(title) > 10:
            score += 0.05
        
        return max(0, min(1, score))
    
    def validate_relevance(self, query: str, snippet: str) -> float:
        """Score relevance of snippet to query (0-1)"""
        query_words = set(query.lower().split())
        snippet_words = set(snippet.lower().split())
        
        if not query_words:
            return 0.5
        
        matches = len(query_words & snippet_words)
        relevance = matches / len(query_words)
        
        return min(1, relevance)
    
    def filter_and_rank(self, results: List[SearchResult], query: str) -> List[WebDataSource]:
        """Filter and rank search results by quality and relevance"""
        sources = []
        
        for result in results:
            credibility = self.score_source(result.url, result.snippet, result.title)
            relevance = self.validate_relevance(query, result.snippet)
            
            # Only include if reasonable quality
            if credibility > 0.3 and relevance > 0.2:
                source = WebDataSource(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    source_type='search_result',
                    freshness=result.freshness or 'unknown',
                    relevance_score=(credibility + relevance) / 2,
                    timestamp=datetime.now().isoformat()
                )
                sources.append(source)
        
        # Sort by relevance score (highest first)
        sources.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return sources


class ReasoningEnhancer:
    """Enhance agent reasoning with web data"""
    
    def __init__(self):
        self.validator = WebDataValidator()
    
    def enhance_decision(self, decision: str, web_sources: List[WebDataSource]) -> Dict[str, Any]:
        """Enhance a decision with web-sourced information"""
        if not web_sources:
            return {
                'original_decision': decision,
                'enhanced': False,
                'web_sources': []
            }
        
        # Synthesize web information
        synthesis = self._synthesize_information(web_sources)
        
        return {
            'original_decision': decision,
            'enhanced': True,
            'web_sources': [asdict(s) for s in web_sources],
            'synthesized_info': synthesis,
            'confidence_lift': len(web_sources) * 0.05,  # Each source adds 5% confidence
        }
    
    def _synthesize_information(self, sources: List[WebDataSource]) -> str:
        """Synthesize multiple web sources into coherent information"""
        if not sources:
            return ""
        
        synthesis = "Based on current web information:\n"
        for i, source in enumerate(sources[:3], 1):  # Top 3 sources
            synthesis += f"\n{i}. {source.title}\n"
            synthesis += f"   Source: {source.url}\n"
            synthesis += f"   Key info: {source.snippet[:200]}...\n"
        
        return synthesis
    
    def create_reasoning_chain(self, task: str, web_results: Dict[str, List[SearchResult]]) -> Dict[str, Any]:
        """Create a reasoning chain augmented with web data"""
        reasoning_steps = []
        
        # Step 1: Analyze task
        reasoning_steps.append({
            'step': 'Task Analysis',
            'description': f'Understanding: {task}',
            'type': 'internal'
        })
        
        # Step 2: Web search
        all_sources = []
        for provider, results in web_results.items():
            validated = self.validator.filter_and_rank(results, task)
            all_sources.extend(validated)
            reasoning_steps.append({
                'step': f'Web Search ({provider})',
                'description': f'Found {len(results)} results',
                'type': 'external',
                'sources': [asdict(s) for s in validated[:2]]
            })
        
        # Step 3: Synthesize
        synthesis = self._synthesize_information(all_sources)
        reasoning_steps.append({
            'step': 'Information Synthesis',
            'description': 'Combining web sources into coherent information',
            'type': 'synthesis',
            'synthesis': synthesis
        })
        
        return {
            'task': task,
            'reasoning_chain': reasoning_steps,
            'primary_sources': [asdict(s) for s in all_sources[:5]],
            'total_sources': len(all_sources)
        }


class KnowledgeBridge:
    """Main bridge between web access and agent reasoning"""
    
    def __init__(self, web_access_manager: Optional[WebAccessManager] = None):
        if web_access_manager is None:
            from web_access_module import get_web_access
            web_access_manager = get_web_access()
        
        self.web_access = web_access_manager
        self.enhancer = ReasoningEnhancer()
        self.integration_log = []
    
    def enrich_knowledge(self, query: str, base_knowledge: str = "",
                        providers: List[str] = None) -> EnrichedKnowledge:
        """Enrich base knowledge with current web information"""
        
        # Parse providers
        if providers is None:
            providers = ['duckduckgo', 'google']
        
        provider_enums = []
        for p in providers:
            try:
                provider_enums.append(SearchProvider(p))
            except ValueError:
                logger.warning(f"Unknown provider: {p}")
        
        # Perform web search
        search_results = self.web_access.search_engine.multi_provider_search(
            query, providers=provider_enums, max_results=5
        )
        
        # Validate and rank sources
        validated_sources = []
        for provider, results in search_results.items():
            ranked = self.enhancer.validator.filter_and_rank(results, query)
            validated_sources.extend(ranked)
        
        # Synthesize enhanced knowledge
        synthesis = self.enhancer._synthesize_information(validated_sources)
        
        enriched = EnrichedKnowledge(
            query=query,
            base_knowledge=base_knowledge,
            web_sources=validated_sources,
            synthesized_answer=synthesis,
            confidence=min(1.0, 0.5 + len(validated_sources) * 0.1),
            timestamp=datetime.now().isoformat()
        )
        
        # Log integration
        self.integration_log.append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'sources_found': len(validated_sources)
        })
        
        logger.info(f"Knowledge enriched: {query} ({len(validated_sources)} sources)")
        
        return enriched
    
    def enhance_agent_decision(self, decision: str, query: str = "",
                              fetch_web_data: bool = True) -> Dict[str, Any]:
        """Enhance an agent decision with web context"""
        
        web_sources = []
        if fetch_web_data and query:
            results = self.web_access.search(query, max_results=3)
            web_sources = self.enhancer.validator.filter_and_rank(results, query)
        
        return self.enhancer.enhance_decision(decision, web_sources)
    
    def augment_reasoning(self, task: str, fetch_fresh_data: bool = True) -> Dict[str, Any]:
        """Create a reasoning chain augmented with fresh web data"""
        
        if fetch_fresh_data:
            web_results = self.web_access.search_engine.multi_provider_search(
                task, max_results=3
            )
        else:
            web_results = {}
        
        return self.enhancer.create_reasoning_chain(task, web_results)
    
    def get_current_facts(self, topic: str, num_sources: int = 3) -> Dict[str, Any]:
        """Get current factual information about a topic"""
        
        search_results = self.web_access.search(topic, max_results=num_sources)
        validated_sources = self.enhancer.validator.filter_and_rank(search_results, topic)
        
        return {
            'topic': topic,
            'timestamp': datetime.now().isoformat(),
            'sources': [asdict(s) for s in validated_sources],
            'synthesis': self.enhancer._synthesize_information(validated_sources),
            'freshness_guarantee': 'Real-time web search'
        }
    
    def compare_with_training_knowledge(self, statement: str, training_date: str = "2021-01-01") -> Dict[str, Any]:
        """Compare a statement with current web knowledge"""
        
        # Get current web information
        web_info = self.get_current_facts(statement, num_sources=3)
        
        return {
            'statement': statement,
            'training_knowledge_date': training_date,
            'training_knowledge': f'Knowledge cut off at {training_date}',
            'current_web_knowledge': web_info,
            'may_be_outdated': True,
            'recommendation': 'Use current web knowledge for decision-making'
        }
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get statistics about knowledge bridge integration"""
        
        total_queries = len(self.integration_log)
        total_sources = sum(log.get('sources_found', 0) for log in self.integration_log)
        avg_sources = total_sources / total_queries if total_queries > 0 else 0
        
        return {
            'total_queries': total_queries,
            'total_sources_integrated': total_sources,
            'average_sources_per_query': avg_sources,
            'recent_queries': self.integration_log[-10:],
            'status': 'Active - Real-time knowledge enabled'
        }


# Convenience instance
_global_bridge = None


def get_knowledge_bridge() -> KnowledgeBridge:
    """Get or create global knowledge bridge"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = KnowledgeBridge()
    return _global_bridge


def enrich_knowledge(query: str, base_knowledge: str = "") -> Dict[str, Any]:
    """Convenience function to enrich knowledge"""
    bridge = get_knowledge_bridge()
    enriched = bridge.enrich_knowledge(query, base_knowledge)
    return {
        'query': enriched.query,
        'base_knowledge': enriched.base_knowledge,
        'web_sources': [asdict(s) for s in enriched.web_sources],
        'synthesized_answer': enriched.synthesized_answer,
        'confidence': enriched.confidence,
        'timestamp': enriched.timestamp
    }


def enhance_agent_decision(decision: str, query: str = "") -> Dict[str, Any]:
    """Convenience function to enhance decisions"""
    bridge = get_knowledge_bridge()
    return bridge.enhance_agent_decision(decision, query)
