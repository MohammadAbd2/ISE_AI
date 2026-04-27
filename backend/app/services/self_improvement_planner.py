from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from datetime import UTC, datetime

from app.services.capability_gap_detector import CapabilityGapDetector, get_capability_gap_detector
from app.services.capability_registry import CapabilityRegistry
from app.services.codebase_map import CodebaseMapService, get_codebase_map_service
from app.services.eval_history import EvalHistoryService, get_eval_history_service
from app.services.execution_packet_history import (
    ExecutionPacketHistoryService,
    get_execution_packet_history_service,
)
from app.services.evals import EvalService, get_eval_service


@dataclass(slots=True)
class ImprovementProposal:
    title: str
    category: str
    priority: str
    score: float
    summary: str
    rationale: list[str]
    actions: list[str]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "score": self.score,
            "summary": self.summary,
            "rationale": self.rationale,
            "actions": self.actions,
        }


class SelfImprovementPlanner:
    EXECUTION_PACKET_MAX_AGE_MINUTES = 5

    def __init__(
        self,
        eval_service: EvalService,
        codebase_map: CodebaseMapService,
        capability_registry: CapabilityRegistry | None = None,
        gap_detector: CapabilityGapDetector | None = None,
        eval_history: EvalHistoryService | None = None,
        execution_history: ExecutionPacketHistoryService | None = None,
    ) -> None:
        self.eval_service = eval_service
        self.codebase_map = codebase_map
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.gap_detector = gap_detector or get_capability_gap_detector(self.capability_registry)
        self.eval_history = eval_history or get_eval_history_service()
        self.execution_history = execution_history or get_execution_packet_history_service()

    async def build_plan(self) -> dict:
        eval_report = await self.eval_service.run_regression_suite()
        codebase = self.codebase_map.build_map()
        remediation_targets = self._build_remediation_targets(codebase)
        remediation_brief = self._build_remediation_brief(
            subsystem_hotspots=self.eval_history.subsystem_hotspots(limit=3),
            remediation_targets=remediation_targets,
        )
        proposals = self._build_proposals(eval_report, codebase)
        execution_packet = self._build_execution_packet(
            proposals=proposals,
            remediation_brief=remediation_brief,
            eval_score=eval_report["score"],
        )
        average_score = round(sum(item.score for item in proposals) / len(proposals), 2) if proposals else 0.0
        recent_launches = self.execution_history.list_history_with_outcomes(limit=5)
        return {
            "overview": {
                "eval_score": eval_report["score"],
                "proposal_count": len(proposals),
                "average_priority_score": average_score,
            },
            "signals": {
                "eval_failures": [
                    result["name"]
                    for result in eval_report["results"]
                    if not result["passed"]
                ],
                "backend_service_files": codebase["summary"]["backend_service_files"],
                "frontend_component_files": codebase["summary"]["frontend_component_files"],
                "test_files": codebase["summary"]["test_files"],
                "capability_count": len(self.capability_registry.list_capabilities()),
                "recent_eval_scores": [
                    item.get("score", 0.0)
                    for item in self.eval_history.list_history(limit=5)
                ],
                "eval_drift": self.eval_history.compare_recent_runs(),
                "unstable_eval_cases": self.eval_history.unstable_cases(limit=5),
                "prioritized_instability": self.eval_history.prioritized_instability(limit=5),
                "subsystem_hotspots": self.eval_history.subsystem_hotspots(limit=5),
                "remediation_targets": remediation_targets,
                "remediation_brief": remediation_brief,
                "execution_packet": execution_packet,
                "recent_remediation_launches": recent_launches,
                "remediation_execution_summary": self._build_execution_summary(recent_launches),
            },
            "proposals": [proposal.to_dict() for proposal in proposals],
        }

    def _build_execution_summary(self, launches: list[dict]) -> dict:
        summary = {
            "total_launches": len(launches),
            "pending_verification": 0,
            "improved": 0,
            "regressed": 0,
            "verified_no_change": 0,
        }
        for item in launches:
            status = item.get("status", "")
            if status in summary:
                summary[status] += 1
        return summary

    def _build_remediation_targets(self, codebase: dict) -> list[dict]:
        backend_services = codebase.get("backend", {}).get("service_files", [])
        backend_api = codebase.get("backend", {}).get("api_files", [])
        frontend_components = codebase.get("frontend", {}).get("component_files", [])

        def pick(*needles: str) -> list[str]:
            haystack = backend_services + backend_api + frontend_components
            matches = [
                path
                for path in haystack
                if any(needle in path.lower() for needle in needles)
            ]
            return matches[:6]

        return [
            {
                "subsystem": "routing",
                "targets": pick("intent_classifier", "agent.py", "orchestrator"),
            },
            {
                "subsystem": "visualization",
                "targets": pick("visualization", "messagelist", "app.jsx", "dashboardview"),
            },
            {
                "subsystem": "self_reflection_and_docs",
                "targets": pick("self_reflection", "documents.py", "learning_routes", "documentationview"),
            },
            {
                "subsystem": "research_and_search",
                "targets": pick("search.py", "documents.py", "orchestrator"),
            },
            {
                "subsystem": "project_context",
                "targets": pick("documents.py", "codebase_map", "project_routes"),
            },
            {
                "subsystem": "capability_contracts",
                "targets": pick("capability_registry", "evals.py", "evolution_routes"),
            },
            {
                "subsystem": "runtime_misc",
                "targets": pick("agent.py", "orchestrator", "dashboardview"),
            },
        ]

    def _build_remediation_brief(
        self,
        subsystem_hotspots: list[dict],
        remediation_targets: list[dict],
    ) -> dict:
        if not subsystem_hotspots:
            return {
                "ready": False,
                "summary": "No hotspot remediation brief is available yet.",
                "subsystem": "",
                "targets": [],
                "checks": [],
            }

        top_hotspot = subsystem_hotspots[0]
        target_map = {item["subsystem"]: item["targets"] for item in remediation_targets}
        subsystem = top_hotspot["subsystem"]
        targets = target_map.get(subsystem, [])[:4]

        checks = [
            f"Inspect files for subsystem `{subsystem}` first.",
            "Re-run the internal eval suite after each contained fix.",
            "Promote the discovered bug into a deterministic regression test.",
        ]
        if subsystem == "routing":
            checks.insert(1, "Check classifier and orchestrator decision boundaries before prompt tuning.")
        elif subsystem == "visualization":
            checks.insert(1, "Verify render blocks, visualization shortcuts, and chat component routing together.")
        elif subsystem == "self_reflection_and_docs":
            checks.insert(1, "Verify docs loading, reflection routing, and planner signals stay aligned.")
        elif subsystem == "capability_contracts":
            checks.insert(1, "Check capability registry metadata, eval contracts, and exposed routes as one unit.")

        return {
            "ready": True,
            "summary": f"Start with the `{subsystem}` hotspot and inspect the mapped files before broader changes.",
            "subsystem": subsystem,
            "targets": targets,
            "checks": checks[:4],
        }

    def _build_execution_packet(
        self,
        proposals: list[ImprovementProposal],
        remediation_brief: dict,
        eval_score: float,
    ) -> dict:
        if not remediation_brief.get("ready"):
            return {
                "ready": False,
                "summary": "No execution packet is available yet.",
                "subsystem": "",
                "steps": [],
                "verification": [],
                "targets": [],
                "agent_prompt": "",
                "generated_at": "",
                "packet_id": "",
                "eval_score": eval_score,
                "max_age_minutes": self.EXECUTION_PACKET_MAX_AGE_MINUTES,
                "is_stale": False,
                "stale_reason": "",
            }

        top_proposal = proposals[0] if proposals else None
        subsystem = remediation_brief.get("subsystem", "")
        targets = remediation_brief.get("targets", [])[:4]
        checks = remediation_brief.get("checks", [])[:4]
        generated_at = datetime.now(UTC).isoformat()

        steps = [
            {
                "step_number": 1,
                "description": f"Open the mapped files for `{subsystem}` and inspect the shared failure path.",
                "target": f"ls -l {targets[0] if targets else '.'}",
                "status": "ready",
            },
            {
                "step_number": 2,
                "description": "Implement the smallest contained fix that addresses the hotspot without widening scope.",
                "target": f"python3 -m compileall {targets[0] if targets else '.'}",
                "status": "ready",
            },
            {
                "step_number": 3,
                "description": "Re-run the internal eval suite and confirm the hotspot score or drift improved.",
                "target": "PYTHONPATH=.:backend pytest tests/test_backend_eval.py tests/test_agent_route_imports.py -q",
                "status": "ready",
            },
        ]

        agent_prompt = "\n\n".join(
            [
                "Execute this remediation packet now.",
                f"Packet id: {subsystem}",
                f"Subsystem: {subsystem}",
                f"Summary: Execution packet for `{subsystem}`: inspect mapped files, apply a narrow fix, then re-run evals.",
                f"Eval score at generation: {eval_score}/10",
                f"Focus files: {', '.join(targets) if targets else subsystem}",
                f"Checks: {' | '.join(checks) if checks else 'none'}",
                "Verification commands: "
                + " | ".join(
                    [
                        "PYTHONPATH=.:backend pytest tests/test_backend_eval.py tests/test_agent_route_imports.py -q",
                        "npm run build",
                        "python3 -m compileall backend/app frontend/src",
                    ]
                ),
                "Make the code changes in the project and verify them. Keep the reply concise and report what changed.",
            ]
        )
        packet_id = hashlib.sha1(
            json.dumps(
                {
                    "subsystem": subsystem,
                    "targets": targets,
                    "checks": checks,
                    "eval_score": eval_score,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:12]

        return {
            "ready": True,
            "summary": f"Execution packet for `{subsystem}`: inspect mapped files, apply a narrow fix, then re-run evals.",
            "subsystem": subsystem,
            "targets": targets,
            "checks": checks,
            "verification": [
                "PYTHONPATH=.:backend pytest tests/test_backend_eval.py tests/test_agent_route_imports.py -q",
                "npm run build",
                "python3 -m compileall backend/app frontend/src",
            ],
            "steps": steps,
            "agent_prompt": agent_prompt.replace(f"Packet id: {subsystem}", f"Packet id: {packet_id}"),
            "generated_at": generated_at,
            "packet_id": packet_id,
            "eval_score": eval_score,
            "max_age_minutes": self.EXECUTION_PACKET_MAX_AGE_MINUTES,
            "is_stale": False,
            "stale_reason": "",
        }

    async def assess_execution_packet_freshness(self, packet: dict) -> dict:
        latest_report = await self.build_plan()
        latest_packet = latest_report.get("signals", {}).get("execution_packet", {})
        if not packet or not packet.get("ready"):
            return {
                "is_stale": True,
                "reason": "Packet is missing or not ready.",
                "latest_packet": latest_packet,
            }

        generated_at_raw = packet.get("generated_at", "")
        try:
            generated_at = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
        except ValueError:
            generated_at = None

        if generated_at is None:
            return {
                "is_stale": True,
                "reason": "Packet has no valid generation timestamp.",
                "latest_packet": latest_packet,
            }

        age_minutes = max(
            0,
            round((datetime.now(UTC) - generated_at).total_seconds() / 60),
        )
        if age_minutes > self.EXECUTION_PACKET_MAX_AGE_MINUTES:
            return {
                "is_stale": True,
                "reason": f"Packet is older than {self.EXECUTION_PACKET_MAX_AGE_MINUTES} minutes.",
                "latest_packet": latest_packet,
            }

        if latest_packet.get("packet_id") and latest_packet.get("packet_id") != packet.get("packet_id"):
            return {
                "is_stale": True,
                "reason": "A newer execution packet is available.",
                "latest_packet": latest_packet,
            }

        return {
            "is_stale": False,
            "reason": "",
            "latest_packet": latest_packet,
        }

    def _build_proposals(self, eval_report: dict, codebase: dict) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        failures = [result for result in eval_report["results"] if not result["passed"]]
        backend_services = codebase["summary"]["backend_service_files"]
        frontend_components = codebase["summary"]["frontend_component_files"]
        tests = codebase["summary"]["test_files"]
        capabilities = self.capability_registry.list_capabilities()

        if failures:
            proposals.append(
                ImprovementProposal(
                    title="Close routing eval failures",
                    category="runtime_quality",
                    priority="critical",
                    score=9.7,
                    summary="Fix the remaining intent and context regressions found by the internal routing suite.",
                    rationale=[
                        f"{len(failures)} eval case(s) are currently failing.",
                        "Routing mistakes propagate into chat, coding, research, and self-development behavior.",
                    ],
                    actions=[
                        "Inspect each failing eval case and map it to classifier/orchestrator logic.",
                        "Promote failures into dedicated regression tests before changing heuristics.",
                        "Re-run the internal eval suite until the failures are closed.",
                    ],
                )
            )

        if backend_services > max(tests * 2, 1):
            proposals.append(
                ImprovementProposal(
                    title="Increase behavioral test coverage",
                    category="validation",
                    priority="high",
                    score=9.2,
                    summary="The service surface is growing faster than the regression suite and needs better coverage.",
                    rationale=[
                        f"Backend services: {backend_services}. Test files: {tests}.",
                        "More agent/runtime paths now exist than the current tests directly exercise.",
                    ],
                    actions=[
                        "Add eval-backed tests for coding progress, file preview, self-improvement planning, and project map behavior.",
                        "Separate routing evals from end-to-end behavior evals.",
                        "Track score changes over time from inside the dashboard.",
                    ],
                )
            )

        if frontend_components >= 12:
            proposals.append(
                ImprovementProposal(
                    title="Unify dashboard and operator surfaces",
                    category="frontend_architecture",
                    priority="high",
                    score=8.8,
                    summary="The frontend now has enough operator surfaces that shared patterns should be standardized.",
                    rationale=[
                        f"Frontend component count is {frontend_components}.",
                        "Dashboard, chat, docs, evals, coding runs, and file previews are converging into one operator workspace.",
                    ],
                    actions=[
                        "Extract reusable cards for eval reports, coding runs, research runs, and architecture maps.",
                        "Normalize action bars, status chips, and expandable details.",
                        "Reduce ad hoc per-panel UI logic in the dashboard.",
                    ],
                )
            )

        if not any(item["name"] == "self_improvement_planning" for item in capabilities):
            proposals.append(
                ImprovementProposal(
                    title="Register self-improvement planning as a first-class capability",
                    category="capabilities",
                    priority="medium",
                    score=8.3,
                    summary="The planner exists logically, but it is not yet surfaced as a formal capability with health and metadata.",
                    rationale=[
                        "Capability discovery is stronger when planning features are visible in the registry.",
                        "The agent should reason about self-improvement through the same capability model as other tools.",
                    ],
                    actions=[
                        "Add a `self_improvement_planning` capability entry with route and render metadata.",
                        "Expose health/status in the dashboard capability list.",
                        "Feed planner output into future approval-driven autonomous execution.",
                    ],
                )
            )

        gap_names = sorted(self.gap_detector.CAPABILITY_GAPS.keys())
        if gap_names:
            proposals.append(
                ImprovementProposal(
                    title="Prioritize missing capability development",
                    category="capability_growth",
                    priority="medium",
                    score=7.9,
                    summary="Several known capability gaps are tracked but not yet ranked against actual product goals.",
                    rationale=[
                        f"Known gaps include: {', '.join(gap_names[:5])}.",
                        "Capability growth should be driven by product value and measured demand, not only keyword detection.",
                    ],
                    actions=[
                        "Add demand scoring to capability gaps based on user prompts and eval misses.",
                        "Rank gaps by usefulness, integration complexity, and validation readiness.",
                        "Only surface top-ranked gaps for proposed autonomous development.",
                    ],
                )
            )

        recent_scores = [
            item.get("score", 0.0)
            for item in self.eval_history.list_history(limit=5)
        ]
        drift = self.eval_history.compare_recent_runs()
        if len(recent_scores) >= 2 and recent_scores[-1] < recent_scores[-2]:
            proposals.append(
                ImprovementProposal(
                    title="Stabilize regressions before adding more surface area",
                    category="runtime_quality",
                    priority="critical",
                    score=9.5,
                    summary="The latest eval score regressed relative to the previous run, so stability work should take priority over new features.",
                    rationale=[
                        f"Recent eval scores: {', '.join(str(score) for score in recent_scores)}.",
                        "Trend reversals mean the system is adding capability faster than it is controlling behavior.",
                    ],
                    actions=[
                        "Compare the latest failing cases against the previous passing run.",
                        "Freeze net-new capability work until the regression is closed.",
                        "Promote the regression into a dedicated deterministic test.",
                    ],
                )
            )

        if drift.get("available") and drift.get("new_failures"):
            proposals.append(
                ImprovementProposal(
                    title="Close newly introduced eval regressions",
                    category="runtime_quality",
                    priority="critical",
                    score=9.4,
                    summary="Specific eval cases started failing in the latest run and should be addressed directly.",
                    rationale=[
                        f"New failures: {', '.join(drift['new_failures'][:4])}.",
                        "Case-level drift is more actionable than score-only monitoring.",
                    ],
                    actions=[
                        "Inspect the exact cases that regressed in the latest run.",
                        "Link each new failure to the responsible classifier, orchestrator, or capability change.",
                        "Do not treat the score as fixed until the individual regressions are resolved.",
                    ],
                )
            )

        unstable_cases = self.eval_history.unstable_cases(limit=3)
        if unstable_cases and unstable_cases[0]["failures"] >= 2:
            proposals.append(
                ImprovementProposal(
                    title="Stabilize repeatedly failing eval cases",
                    category="runtime_quality",
                    priority="high",
                    score=9.1,
                    summary="Some eval cases are failing across multiple runs, which suggests structural instability rather than one-off regressions.",
                    rationale=[
                        f"Most unstable cases: {', '.join(item['name'] for item in unstable_cases)}.",
                        "Repeated failures are stronger signals than single-run noise.",
                    ],
                    actions=[
                        "Promote the most unstable cases into direct service-level tests.",
                        "Inspect shared dependencies behind the repeated failures.",
                        "Prioritize architectural fixes over prompt-level tuning for those cases.",
                    ],
                )
            )

        prioritized_instability = self.eval_history.prioritized_instability(limit=3)
        if prioritized_instability and prioritized_instability[0]["weighted_score"] >= 8:
            proposals.append(
                ImprovementProposal(
                    title="Focus on highest-impact unstable eval paths",
                    category="runtime_quality",
                    priority="high",
                    score=9.0,
                    summary="Some failures are disproportionately important because they are both recent and correlated with weaker eval runs.",
                    rationale=[
                        f"Highest-impact instability: {', '.join(item['name'] for item in prioritized_instability)}.",
                        "Weighted instability is a better prioritization signal than raw failure counts alone.",
                    ],
                    actions=[
                        "Fix the highest weighted unstable case before lower-impact cleanup.",
                        "Check whether the same subsystem appears across the top weighted failures.",
                        "Use weighted instability as a release gate for future agent changes.",
                    ],
                )
            )

        subsystem_hotspots = self.eval_history.subsystem_hotspots(limit=3)
        if subsystem_hotspots and subsystem_hotspots[0]["weighted_score"] >= 8:
            remediation_targets = {
                item["subsystem"]: item["targets"]
                for item in self._build_remediation_targets(codebase)
            }
            top_hotspot = subsystem_hotspots[0]["subsystem"]
            proposals.append(
                ImprovementProposal(
                    title="Stabilize the hottest failing subsystem",
                    category="runtime_quality",
                    priority="high",
                    score=8.9,
                    summary="Several unstable cases cluster into the same subsystem, which suggests shared root causes that should be fixed together.",
                    rationale=[
                        f"Top hotspots: {', '.join(item['subsystem'] for item in subsystem_hotspots)}.",
                        "Subsystem clustering is a stronger signal for architectural work than isolated case fixes.",
                    ],
                    actions=[
                        "Investigate the top hotspot as a shared failure domain.",
                        f"Start with likely files: {', '.join(remediation_targets.get(top_hotspot, [])[:3]) or 'no targets mapped yet'}.",
                        "Fix common routing or context logic before handling each case separately.",
                        "Use hotspot scores to group future stabilization work into batches.",
                    ],
                )
            )

        recent_launches = self.execution_history.list_history_with_outcomes(limit=5)
        pending_launches = [item for item in recent_launches if item.get("status") == "pending_verification"]
        regressed_launches = [item for item in recent_launches if item.get("status") == "regressed"]
        if not recent_launches and (drift.get("new_failures") or failures):
            proposals.append(
                ImprovementProposal(
                    title="Convert recommendations into executed remediation runs",
                    category="execution_discipline",
                    priority="high",
                    score=8.7,
                    summary="The system is identifying issues, but there is no recent remediation execution history to show follow-through.",
                    rationale=[
                        "No execution packet launches are recorded yet.",
                        "Planning quality only matters if fixes are actually being run and validated.",
                    ],
                    actions=[
                        "Launch the current execution packet against the top hotspot.",
                        "Track whether remediation launches reduce future eval instability.",
                        "Use launch history to identify stalled improvement loops.",
                    ],
                )
            )

        if pending_launches:
            proposals.append(
                ImprovementProposal(
                    title="Verify recent remediation launches",
                    category="execution_discipline",
                    priority="high",
                    score=8.9,
                    summary="Recent remediation packets were launched but have not been verified by a follow-up eval run yet.",
                    rationale=[
                        f"{len(pending_launches)} launch(es) are still waiting for verification.",
                        "Unverified launches create false confidence and weaken the self-improvement loop.",
                    ],
                    actions=[
                        "Re-run the internal eval suite after the current remediation work.",
                        "Compare the launch baseline score against the newest eval score and keep the outcome in history.",
                        "Do not launch another wide fix until the pending packet is verified.",
                    ],
                )
            )

        if regressed_launches:
            proposals.append(
                ImprovementProposal(
                    title="Contain regressed remediation packets",
                    category="execution_discipline",
                    priority="high",
                    score=9.1,
                    summary="A recent remediation launch was followed by a worse eval score and should be investigated before starting another packet.",
                    rationale=[
                        f"{len(regressed_launches)} recent launch(es) show regression after execution.",
                        "Regression after remediation usually means the fix scope was too wide or the wrong hotspot was targeted.",
                    ],
                    actions=[
                        "Inspect the latest regressed packet and its target files first.",
                        "Narrow the remediation scope before retrying the fix.",
                        "Add a deterministic regression test for the affected hotspot before the next launch.",
                    ],
                )
            )

        proposals.sort(key=lambda item: item.score, reverse=True)
        return proposals


@lru_cache
def get_self_improvement_planner() -> SelfImprovementPlanner:
    return SelfImprovementPlanner(
        eval_service=get_eval_service(),
        codebase_map=get_codebase_map_service(),
    )
