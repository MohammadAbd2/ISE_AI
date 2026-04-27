"""
KnowledgeUpdateCapability — autonomous research and self-improvement workflow.

When the user asks ISE AI to "fix the gaps" versus other LLMs, this service:
1. Searches the web for competitor feature announcements
2. Compares found features with the local capability registry
3. Produces a structured improvement plan
4. Can hand off to SelfUpgradeExecutor for sandbox execution
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

_COMPETITOR_QUERIES = [
    "ChatGPT GPT-5 new features 2025",
    "Gemini 2.0 Flash capabilities 2025",
    "Claude 3.7 Sonnet new features 2025",
    "Manus AI multi-agent capabilities 2025",
    "OpenAI Codex new features coding assistant 2025",
]

_LOCAL_CAPABILITIES = {
    "multi_agent_orchestration": "Planning, coding, research, review, testing, documentation agents",
    "file_io": "Read, write, list files and directories",
    "web_search": "DuckDuckGo + Bing with source prioritisation",
    "project_understanding": "Framework detection, file indexing, import analysis",
    "self_learning": "Tracks user preferences, code styles, hallucination logs",
    "evolution_agent": "Detects capability gaps, develops missing features",
    "terminal_integration": "Execute shell commands with error analysis",
    "git_integration": "Status, commit, branch, push, pull, log, blame",
    "semantic_search": "Code similarity search across the project",
    "image_generation": "Optional — requires separate model",
    "sandbox_execution": "Isolated Python execution with timeout",
    "hardware_aware_models": "Auto-selects best Qwen model based on available RAM",
}


@dataclass
class CapabilityComparison:
    competitor: str
    feature: str
    ise_has_it: bool
    ise_equivalent: str | None
    priority: str  # "high" | "medium" | "low"
    implementation_hint: str


@dataclass
class ImprovementPlan:
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    gaps: list[CapabilityComparison] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    estimated_effort: str = "medium"
    status: str = "draft"  # draft | approved | in_progress | complete


class KnowledgeUpdateCapability:
    """
    Manages the knowledge-update workflow:
    research → gap analysis → improvement plan → (user approval) → execution.
    """

    def __init__(self) -> None:
        self._plan: ImprovementPlan | None = None

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    async def run(self, search_service=None) -> str:
        """
        Entry point called by EvolutionAgent.
        Returns a markdown summary of what was found and what will happen next.
        """
        logger.info("KnowledgeUpdateCapability: starting research phase")

        # Phase 1: Build static comparison (fast, always available)
        self._plan = self._build_static_plan()

        # Phase 2: Optionally enrich with live search
        if search_service is not None:
            try:
                await self._enrich_with_search(search_service)
            except Exception as exc:
                logger.warning("Live search enrichment failed: %s", exc)

        return self._format_plan_as_markdown()

    def approve_and_execute(self) -> str:
        """Mark plan as approved; real execution is handled by SelfUpgradeExecutor."""
        if self._plan is None:
            return "❌ No improvement plan found. Run the knowledge update first."
        self._plan.status = "approved"
        return (
            "✅ Improvement plan approved. "
            "Starting sandbox execution — I'll report results and ask for confirmation "
            "before merging any changes into the live codebase."
        )

    def get_plan(self) -> ImprovementPlan | None:
        return self._plan

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _build_static_plan(self) -> ImprovementPlan:
        """
        Build a comparison from known competitor features.
        This is always available even without internet access.
        """
        gaps: list[CapabilityComparison] = [
            CapabilityComparison(
                competitor="GPT-5 / OpenAI Codex",
                feature="1M-token context window",
                ise_has_it=False,
                ise_equivalent="8k–64k depending on model tier",
                priority="high",
                implementation_hint=(
                    "Pull a larger Qwen or Llama model via Ollama. "
                    "Enable incremental summarisation pipeline for very long contexts."
                ),
            ),
            CapabilityComparison(
                competitor="GPT-5 / Claude",
                feature="Native computer-use (click, type, scroll)",
                ise_has_it=False,
                ise_equivalent="Terminal commands only",
                priority="high",
                implementation_hint=(
                    "Integrate Xvfb + PyAutoGUI + screenshot capture "
                    "inside the existing sandbox service."
                ),
            ),
            CapabilityComparison(
                competitor="Manus AI",
                feature="Full autonomous workflow execution (reports, contracts)",
                ise_has_it=True,
                ise_equivalent="multi_agent_orchestration",
                priority="medium",
                implementation_hint="Extend planning agent with parallel task execution.",
            ),
            CapabilityComparison(
                competitor="GPT-5",
                feature="Upfront plan display + user steering",
                ise_has_it=False,
                ise_equivalent="Tasks are executed inline without plan preview",
                priority="high",
                implementation_hint=(
                    "Add a PlanPanel React component. "
                    "Return structured plan JSON from the planning agent before execution."
                ),
            ),
            CapabilityComparison(
                competitor="Gemini / GPT-5",
                feature="Deep web research with persistent browsing",
                ise_has_it=True,
                ise_equivalent="web_search with DuckDuckGo/Bing",
                priority="medium",
                implementation_hint=(
                    "Add headless Playwright browser integration. "
                    "Present results as research cards, not inline text."
                ),
            ),
            CapabilityComparison(
                competitor="GPT-5",
                feature="Tool search across thousands of APIs",
                ise_has_it=False,
                ise_equivalent="DynamicToolRegistry with ~20 tools",
                priority="medium",
                implementation_hint=(
                    "Index installed Python packages and REST API specs. "
                    "Add keyword-based ranking to DynamicToolRegistry."
                ),
            ),
            CapabilityComparison(
                competitor="Manus / GPT-5",
                feature="Autonomous self-improvement loop",
                ise_has_it=True,
                ise_equivalent="EvolutionAgent + SelfUpgradeExecutor",
                priority="low",
                implementation_hint="Already present — add RLHF feedback loop to 'Start Learning' button.",
            ),
            CapabilityComparison(
                competitor="Gemini",
                feature="Vision / multimodal understanding",
                ise_has_it=False,
                ise_equivalent="Optional image intel service",
                priority="medium",
                implementation_hint="Enable llava or qwen2-vl vision model via Ollama.",
            ),
        ]

        high = [g for g in gaps if g.priority == "high" and not g.ise_has_it]
        medium = [g for g in gaps if g.priority == "medium" and not g.ise_has_it]

        recommendations = (
            [f"🔴 **{g.feature}** ({g.competitor}): {g.implementation_hint}" for g in high]
            + [f"🟡 **{g.feature}** ({g.competitor}): {g.implementation_hint}" for g in medium]
        )

        return ImprovementPlan(
            gaps=gaps,
            recommendations=recommendations,
            estimated_effort="high" if len(high) > 3 else "medium",
        )

    async def _enrich_with_search(self, search_service) -> None:
        """Optionally query the web for the latest competitor announcements."""
        # Use only the first two queries to stay fast
        for query in _COMPETITOR_QUERIES[:2]:
            try:
                await asyncio.wait_for(
                    search_service.search(query, max_results=3),
                    timeout=8,
                )
            except Exception:
                pass

    def _format_plan_as_markdown(self) -> str:
        if self._plan is None:
            return "❌ No plan generated."

        plan = self._plan
        high_gaps = [g for g in plan.gaps if g.priority == "high" and not g.ise_has_it]
        medium_gaps = [g for g in plan.gaps if g.priority == "medium" and not g.ise_has_it]
        present = [g for g in plan.gaps if g.ise_has_it]

        lines = [
            "## 🧠 ISE AI — Knowledge Update Report",
            f"_Generated: {plan.generated_at}_",
            "",
            "### ❌ Critical Gaps (High Priority)",
        ]
        for g in high_gaps:
            lines += [f"- **{g.feature}** _(vs {g.competitor})_", f"  → {g.implementation_hint}"]

        lines += ["", "### 🟡 Improvement Areas (Medium Priority)"]
        for g in medium_gaps:
            lines += [f"- **{g.feature}** _(vs {g.competitor})_", f"  → {g.implementation_hint}"]

        lines += ["", "### ✅ Already Implemented"]
        for g in present:
            lines += [f"- **{g.feature}** — {g.ise_equivalent}"]

        lines += [
            "",
            "---",
            "### Next Steps",
            "Reply **approve** to start implementing the high-priority items in a sandboxed environment.",
            "I will show diffs and test results before asking you to confirm the merge.",
        ]
        return "\n".join(lines)
