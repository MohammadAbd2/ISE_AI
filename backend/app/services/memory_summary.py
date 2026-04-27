from dataclasses import dataclass
from functools import lru_cache

from app.services.codebase_map import CodebaseMapService, get_codebase_map_service
from app.services.profile import ProfileService, get_profile_service
from app.services.research_memory import ResearchMemoryService, get_research_memory_service
from app.services.self_learning import SelfLearningSystem, get_learning_system
from app.services.turn_diagnostics import TurnDiagnosticsService, get_turn_diagnostics_service


@dataclass(slots=True)
class MemorySummaryService:
    profile_service: ProfileService
    learning_system: SelfLearningSystem
    research_memory: ResearchMemoryService
    diagnostics: TurnDiagnosticsService
    codebase_map: CodebaseMapService

    async def build_summary(self) -> dict:
        profile = await self.profile_service.get_profile()
        learning = await self.learning_system.get_personalized_context("summarize memory")
        learning_stats = await self.learning_system.get_learning_stats()
        codebase = self.codebase_map.build_map()

        research_cache_size = len(self.research_memory._cache)
        research_topics = sorted(self.research_memory._research_facts.keys())[:10]
        recent_turns = self.diagnostics.recent()[:10]

        return {
            "user_memory": {
                "custom_instructions": profile.get("custom_instructions", ""),
                "saved_memory": profile.get("memory", []),
                "response_style": learning.get("user_preferences", {}).get("response_style", ""),
                "learned_preferences": learning_stats.get("preferences_learned", 0),
            },
            "project_memory": {
                "technologies": learning_stats.get("technologies", []),
                "backend_services": codebase["summary"]["backend_service_files"],
                "frontend_components": codebase["summary"]["frontend_component_files"],
                "docs_files": codebase["summary"]["docs_files"],
                "route_modules": codebase["backend"]["route_modules"][:10],
            },
            "research_memory": {
                "cached_queries": research_cache_size,
                "known_topics": research_topics,
            },
            "execution_memory": {
                "recent_turn_count": len(recent_turns),
                "recent_intents": [item["intent_kind"] for item in recent_turns[:6]],
                "recent_agents": sorted({agent for item in recent_turns for agent in item.get("used_agents", [])})[:10],
            },
        }


@lru_cache
def get_memory_summary_service() -> MemorySummaryService:
    return MemorySummaryService(
        profile_service=get_profile_service(),
        learning_system=get_learning_system(),
        research_memory=get_research_memory_service(),
        diagnostics=get_turn_diagnostics_service(),
        codebase_map=get_codebase_map_service(),
    )
