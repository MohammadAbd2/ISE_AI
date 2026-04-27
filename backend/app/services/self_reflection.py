from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Any

from app.services.capability_registry import CapabilityRegistry
from app.services.memory_summary import MemorySummaryService, get_memory_summary_service
from app.services.self_improvement_planner import (
    SelfImprovementPlanner,
    get_self_improvement_planner,
)
from app.services.turn_diagnostics import (
    TurnDiagnosticsService,
    get_turn_diagnostics_service,
)


@dataclass(slots=True)
class SelfReflectionService:
    planner: SelfImprovementPlanner
    memory_summary: MemorySummaryService
    diagnostics: TurnDiagnosticsService
    capability_registry: CapabilityRegistry | None = None

    def __post_init__(self) -> None:
        if self.capability_registry is None:
            self.capability_registry = CapabilityRegistry()

    async def build_guidance(self) -> dict:
        plan = await self.planner.build_plan()
        memory = await self.memory_summary.build_summary()
        diagnostics = self.diagnostics.recent()[:8]
        capabilities = self.capability_registry.list_capabilities()

        top_proposals = plan.get("proposals", [])[:3]
        unstable_cases = plan.get("signals", {}).get("unstable_eval_cases", [])[:3]
        prioritized_instability = plan.get("signals", {}).get("prioritized_instability", [])[:3]
        subsystem_hotspots = plan.get("signals", {}).get("subsystem_hotspots", [])[:3]
        remediation_targets = plan.get("signals", {}).get("remediation_targets", [])
        remediation_brief = plan.get("signals", {}).get("remediation_brief", {})
        execution_packet = plan.get("signals", {}).get("execution_packet", {})
        recent_launches = plan.get("signals", {}).get("recent_remediation_launches", [])[:3]
        execution_summary = plan.get("signals", {}).get("remediation_execution_summary", {})
        remediation_map = {item["subsystem"]: item["targets"] for item in remediation_targets}
        recent_intents = [item.get("intent_kind", "") for item in diagnostics if item.get("intent_kind")]
        active_agents = sorted(
            {
                agent
                for item in diagnostics
                for agent in item.get("used_agents", [])
                if agent
            }
        )
        available_capabilities = len(
            [item for item in capabilities if item.get("status") == "available"]
        )

        summary = (
            f"I can improve myself through the live architecture that already exists in this repo: "
            f"{available_capabilities} registered capabilities, an internal eval score of "
            f"{plan['overview']['eval_score']}/10, and a planner that ranks the next upgrades from codebase and runtime signals."
        )

        highlights = [
            f"Top priorities: {', '.join(item['title'] for item in top_proposals) or 'none'}",
            f"Most unstable eval cases: {', '.join(item['name'] for item in unstable_cases) or 'none identified'}",
            f"Highest impact instability: {', '.join(item['name'] for item in prioritized_instability) or 'none identified'}",
            f"Subsystem hotspots: {', '.join(item['subsystem'] for item in subsystem_hotspots) or 'none identified'}",
            f"Likely fix targets: {', '.join(remediation_map.get(subsystem_hotspots[0]['subsystem'], [])[:3]) if subsystem_hotspots else 'none mapped yet'}",
            f"Remediation brief: {remediation_brief.get('summary') or 'not ready yet'}",
            f"Recent remediation launches: {', '.join(item.get('packet_id', '') for item in recent_launches) or 'none recorded'}",
            "Launch outcomes: "
            f"{execution_summary.get('improved', 0)} improved, "
            f"{execution_summary.get('pending_verification', 0)} pending, "
            f"{execution_summary.get('regressed', 0)} regressed",
            f"Recent intent mix: {', '.join(recent_intents[:5]) or 'no recent turns'}",
            f"Active agents seen recently: {', '.join(active_agents[:5]) or 'none'}",
            f"Learned response style: {memory['user_memory'].get('response_style') or 'not set'}",
            f"Project technologies: {', '.join(memory['project_memory'].get('technologies', [])) or 'not learned yet'}",
        ]

        reply = (
            f"{summary}\n\n"
            "The highest-value next step is to keep tightening execution quality: use eval failures and runtime traces "
            "to drive changes, then promote successful upgrades into first-class capabilities and dashboard surfaces."
        )

        render_blocks = [
            {
                "type": "report",
                "payload": {
                    "title": "Self-development status",
                    "summary": summary,
                    "highlights": highlights,
                },
            },
            {
                "type": "plan_result",
                "payload": {
                    "title": "Top improvement queue",
                    "status": "ready",
                    "steps": [
                        {
                            "step_number": index + 1,
                            "description": proposal["title"],
                            "target": proposal["category"],
                            "status": proposal["priority"],
                            "output": proposal["summary"],
                            "error": "",
                        }
                        for index, proposal in enumerate(top_proposals)
                    ],
                },
            },
            {
                "type": "reply_options",
                "payload": {
                    "title": "Tune future replies",
                    "options": [
                        {
                            "label": "Shorter like this",
                            "style": "concise",
                            "description": "Prefer tighter answers with less filler.",
                        },
                        {
                            "label": "More structured like this",
                            "style": "structured",
                            "description": "Prefer stronger hierarchy and scanability.",
                        },
                    ],
                },
            },
            {
                "type": "report",
                "payload": {
                    "title": "Remediation brief",
                    "summary": remediation_brief.get("summary", ""),
                    "highlights": [
                        f"Subsystem: {remediation_brief.get('subsystem') or 'unknown'}",
                        f"Targets: {', '.join(remediation_brief.get('targets', [])[:3]) or 'none'}",
                        f"Checks: {', '.join(remediation_brief.get('checks', [])[:2]) or 'none'}",
                    ],
                },
            },
            {
                "type": "execution_packet",
                "payload": execution_packet,
            },
        ]
        return {
            "reply": reply,
            "render_blocks": render_blocks,
        }

    def extract_execution_packet(self, guidance: dict) -> dict:
        for block in guidance.get("render_blocks", []):
            if isinstance(block, dict) and block.get("type") == "execution_packet":
                payload = block.get("payload", {})
                if isinstance(payload, dict):
                    return payload
        return {}

    def should_activate(self, user_message: str) -> bool:
        """Activate self-reflection only for explicit self-improvement requests.

        Normal product work often includes words like roadmap, debug, fix, and analyze.
        Those should not divert the assistant into self-upgrade mode unless the user is
        clearly asking the assistant to inspect or improve *itself*.
        """
        lower = user_message.lower().strip()
        explicit_phrases = [
            "how can you develop yourself",
            "how can you develop your self",
            "develop yourself",
            "develop your self",
            "improve yourself",
            "improve your self",
            "self improve",
            "self-improvement",
            "what should you improve about yourself",
            "what can you improve about yourself",
            "how can you improve yourself",
            "how are you built",
            "improve your own code",
            "fix your own code",
            "fix yourself",
            "debug yourself",
            "analyze your own errors",
            "diagnose your own issues",
            "work on your roadmap",
            "execute the remediation",
            "start remediation",
            "self-upgrade",
            "upgrade yourself",
        ]
        if any(phrase in lower for phrase in explicit_phrases):
            return True
        return bool(
            re.search(
                r"\b(?:develop|improve|debug|fix|analyze|diagnose|upgrade)\s+(?:your\s*self|yourself|your own code|your own issues)\b",
                lower,
            )
        )

    def should_execute(self, user_message: str) -> bool:
        lower = user_message.lower().strip()
        question_phrases = (
            "how can you develop yourself",
            "how can you develop your self",
            "how can you improve",
            "what can you improve",
            "what should you improve",
            "how are you built",
            "analyze error",
            "diagnose problem",
        )
        if any(phrase in lower for phrase in question_phrases):
            return False
        if lower.startswith(("how ", "what ", "why ", "which ")):
            return False

        execution_phrases = (
            "develop yourself",
            "develop your self",
            "improve yourself",
            "improve your self",
            "start improving yourself",
            "work on your roadmap",
            "execute the remediation",
            "start remediation",
            "fix your own issues",
            "improve your own code",
            "debug yourself",
            "upgrade yourself",
            "self-upgrade",
        )
        if any(phrase in lower for phrase in execution_phrases):
            return True
        return bool(
            re.search(
                r"\b(?:develop|improve|fix|debug|upgrade)\s+(?:your\s*self|yourself|your own code|your own issues)\b",
                lower,
            )
        )

    async def analyze_error(self, error_message: str, context: str) -> dict[str, Any]:
        """Analyze an error message and provide a diagnosis and suggested fix."""
        if "can only concatenate list" in error_message and "dict" in error_message:
            return {
                "diagnosis": "Data Structure Mismatch: can only concatenate list (not \"dict\") to list",
                "suggested_fix": "Ensure all log objects are wrapped in a list [] or converted using list() before concatenation."
            }
            
        # This is a placeholder for a more sophisticated LLM-driven error analysis
        diagnosis = f"The system encountered an error: {error_message}.\nBased on the context, it appears to be related to: {context}."
        suggested_fix = "Please review the relevant code and logs. Consider breaking down the problem into smaller parts and testing each component individually."
        
        return {"diagnosis": diagnosis, "suggested_fix": suggested_fix}


@lru_cache
def get_self_reflection_service() -> SelfReflectionService:
    return SelfReflectionService(
        planner=get_self_improvement_planner(),
        memory_summary=get_memory_summary_service(),
        diagnostics=get_turn_diagnostics_service(),
    )
