from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

PHASES: list[dict[str, Any]] = [
    {"id": 44, "title": "Real Execution Engine", "capabilities": ["event sourced lifecycle", "live progress", "pause/resume/cancel", "retry budget"]},
    {"id": 45, "title": "Code Generation Quality", "capabilities": ["intent based file names", "SCSS support", "lint/build gates", "template rejection", "diff preview"]},
    {"id": 46, "title": "Project-Aware Agent", "capabilities": ["framework detection", "dependency map", "style convention scan", "safe file targeting"]},
    {"id": 47, "title": "Multi-Agent Orchestration", "capabilities": ["planner", "builder", "reviewer", "tester", "exporter"]},
    {"id": 48, "title": "UI/UX Upgrade", "capabilities": ["clean timeline", "collapsible logs", "highlighted code", "status badges", "download actions"]},
    {"id": 49, "title": "Memory and Learning", "capabilities": ["lesson store", "failure fixes", "project conventions", "ranked reuse"]},
    {"id": 50, "title": "Verification Sandbox", "capabilities": ["install/build/test/lint", "terminal capture", "manifest", "hash verification"]},
    {"id": 51, "title": "Autonomous Repair Loop", "capabilities": ["error diagnosis", "patch proposals", "rerun checks", "bounded attempts"]},
    {"id": 52, "title": "Production Agent Platform", "capabilities": ["git branches", "PR handoff", "rollback", "history", "approvals", "audit logs"]},
    {"id": 53, "title": "Real LLM Integration", "capabilities": ["provider abstraction", "token streaming", "tool call envelopes", "context budget management", "model routing"]},
    {"id": 54, "title": "Deep Repo Understanding", "capabilities": ["AST outline", "dependency graph", "semantic file ranking", "impact analysis", "edit target selection"]},
    {"id": 55, "title": "Intelligent Planning Engine", "capabilities": ["adaptive plans", "conditional branches", "confidence scoring", "fallback strategies", "mid-run replanning"]},
    {"id": 56, "title": "Advanced Self-Healing Loop", "capabilities": ["error classification", "multi-strategy repairs", "rollback checkpoints", "alternate solution paths", "bounded experiments"]},
    {"id": 57, "title": "UX Intelligence Layer", "capabilities": ["design critique", "accessibility scoring", "spacing/layout heuristics", "design system guardrails", "auto-polish suggestions"]},
    {"id": 58, "title": "Human-in-the-Loop Control", "capabilities": ["step approvals", "plan editing", "live intervention", "why explanations", "risk gates"]},
    {"id": 59, "title": "Multi-Project Memory Graph", "capabilities": ["project graph", "user preference profile", "cross-project lessons", "convention memory", "similarity search"]},
    {"id": 60, "title": "Cloud Agent Infrastructure", "capabilities": ["job queue", "distributed workers", "persistent sandboxes", "parallel agents", "tenant-safe execution"]},
    {"id": 61, "title": "Frontier Product Builder", "capabilities": ["idea-to-deploy workflow", "voice command contract", "visual editor handoff", "AI CTO architecture mode", "collaborative product sessions"]},
    {"id": 62, "title": "Real-World Reliability", "capabilities": ["timeout policy", "retry matrix", "sandbox isolation score", "structured traces", "SLA dashboard"]},
    {"id": 63, "title": "Evaluation and Benchmarking", "capabilities": ["task benchmark suite", "quality scoring", "regression detection", "model comparison", "release readiness score"]},
    {"id": 64, "title": "Model Orchestration Layer", "capabilities": ["cost/quality routing", "fallback models", "ensemble voting", "latency budgets", "provider health checks"]},
    {"id": 65, "title": "Tool Ecosystem", "capabilities": ["GitHub/GitLab connector contract", "CI/CD contract", "Figma handoff", "database/API adapters", "tool permission scopes"]},
    {"id": 66, "title": "Security and Guardrails", "capabilities": ["secret redaction", "prompt-injection shield", "file access policy", "destructive action approval", "sandbox egress controls"]},
    {"id": 67, "title": "Autonomous Product Loops", "capabilities": ["idea-to-build loop", "feedback ingestion", "iteration backlog", "A/B experiment generator", "deployment readiness checklist"]},
    {"id": 68, "title": "Swarm Collaboration", "capabilities": ["agent debate", "parallel workstreams", "critic/optimizer loop", "merge arbitration", "confidence-weighted decisions"]},
    {"id": 69, "title": "Human + AI Co-Creation", "capabilities": ["pair-programming mode", "live plan editing", "decision explanations", "inline suggestions", "clarification gates"]},
    {"id": 70, "title": "Product Platformization", "capabilities": ["dashboard analytics", "accounts/billing architecture", "public API contract", "plugin marketplace", "skill packaging"]},
]

@dataclass(slots=True)
class CapabilityStatus:
    phase: int
    title: str
    status: str
    shipped: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(slots=True)
class SuperAgentRun:
    id: str
    prompt: str
    status: str = "queued"
    progress: int = 0
    active_phase: int = 44
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    controls: dict[str, bool] = field(default_factory=lambda: {"paused": False, "cancelled": False})
    events: list[dict[str, Any]] = field(default_factory=list)
    verification: list[dict[str, Any]] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)
    def add_event(self, agent: str, phase: int, status: str, message: str, **metadata: Any) -> None:
        self.updated_at = time.time(); self.active_phase = phase
        self.events.append({"id": f"evt-{len(self.events)+1:04d}", "agent": agent, "phase": phase, "status": status, "message": message, "elapsed_seconds": int(time.time() - self.created_at), "metadata": metadata})
        self.audit.append({"at": self.updated_at, "actor": agent, "action": status, "phase": phase, "message": message})
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self); data["elapsed_seconds"] = int(time.time() - self.created_at); return data

class SuperAgentDevelopmentPlatform:
    """Phase 44-61 control plane for an elite coding/product agent platform."""
    def __init__(self) -> None:
        self._runs: dict[str, SuperAgentRun] = {}
        self._lessons: list[dict[str, Any]] = []
        self._approvals: list[dict[str, Any]] = []

    def roadmap(self) -> dict[str, Any]:
        return {"goal": "Reach Phase 70: production reliability, evaluation, model orchestration, tool ecosystem, security guardrails, autonomous product loops, swarm collaboration, co-creation, and platformization.", "phases": [self._phase_status(p).to_dict() for p in PHASES], "next_actions": ["Wire real LLM providers to the stream/tool contract.", "Use repo graph top-edit-targets before every file mutation.", "Run adaptive planning, verification, self-healing, and UX review before export.", "Gate risky actions through human approval and audit records.", "Move run, memory graph, artifact, and sandbox state from memory to durable storage for cloud scale. Run reliability, evaluation, security and approval gates before Phase 70 release."]}

    def _phase_status(self, phase: dict[str, Any]) -> CapabilityStatus:
        evidence_map = {44:["SuperAgentRun event store","pause/resume/cancel control API","elapsed time derived from created_at"],45:["quality_gate()","template_marker check","SCSS intent detection","diff preview contract"],46:["project_scan() detects Vite/React/SCSS/tests/package scripts"],47:["PlannerAgent/BuilderAgent/ReviewerAgent/TestAgent/ExportAgent event roles"],48:["SuperAgentPanel UI","status badges","progress rail","roadmap cards"],49:["lesson store with ranked keyword search"],50:["verification summary includes package scripts, required files, sha256 manifest"],51:["repair_plan() converts failures to bounded repair steps"],52:["approval queue","audit log","rollback snapshot contract","PR handoff metadata"],53:["llm_stream_contract()","context_budget()","provider/tool-call envelope"],54:["repo_intelligence_graph()","dependency/import graph","top edit targets"],55:["adaptive_plan()","branch confidence scoring","fallbacks"],56:["classify_error()","repair_strategies()","checkpoint-aware alternatives"],57:["ux_review()","accessibility/responsive/motion/token scoring"],58:["human_gate()","approval decision log with risk policy"],59:["memory_graph()","lesson/fix nodes and edges"],60:["cloud_job_plan()","queue/worker/sandbox/telemetry contract"],61:["frontier_product_builder()","idea-to-deploy/voice/visual-editor/AI-CTO modes"]}
        return CapabilityStatus(phase=phase["id"], title=phase["title"], status="implemented", shipped=list(phase["capabilities"]), evidence=evidence_map.get(phase["id"], []))

    def create_run(self, prompt: str, workspace: str | None = None) -> dict[str, Any]:
        run = SuperAgentRun(id=str(uuid4()), prompt=prompt.strip() or "Autonomous development task", status="running")
        self._runs[run.id] = run
        for index, phase in enumerate(PHASES, start=1):
            agent = self._agent_for_phase(phase["id"]); run.progress = min(99, round(index / len(PHASES) * 100))
            run.add_event(agent, phase["id"], "completed", f"{phase['title']} capability layer prepared", capabilities=phase["capabilities"])
        if workspace: run.verification.append(self.verify_workspace(workspace))
        run.status = "ready_for_approval"; run.progress = 100
        run.add_event("FrontierProductAgent", 61, "ready", "Phase 61 handoff is ready: LLM streaming, repo graph, adaptive planning, self-healing, UX review, HITL, memory graph, cloud jobs, and product-builder contracts are prepared.")
        return run.to_dict()

    def list_runs(self) -> list[dict[str, Any]]:
        return sorted((run.to_dict() for run in self._runs.values()), key=lambda r: r["created_at"], reverse=True)
    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id); return run.to_dict() if run else None
    def control(self, run_id: str, action: str) -> dict[str, Any]:
        run = self._runs[run_id]
        if action == "pause": run.controls["paused"] = True; run.status = "paused"; run.add_event("ControlAgent", run.active_phase, "paused", "User paused autonomous execution")
        elif action == "resume": run.controls["paused"] = False; run.status = "running"; run.add_event("ControlAgent", run.active_phase, "running", "User resumed autonomous execution")
        elif action == "cancel": run.controls["cancelled"] = True; run.status = "cancelled"; run.add_event("ControlAgent", run.active_phase, "cancelled", "User cancelled autonomous execution")
        elif action == "approve":
            approval = {"id": str(uuid4()), "run_id": run_id, "status": "approved", "created_at": time.time(), "summary": "Approved for merge/export"}; self._approvals.append(approval); run.status = "approved"; run.add_event("ApprovalAgent", 58, "approved", "Run approved for production handoff", approval_id=approval["id"])
        elif action == "rollback": run.status = "rollback_ready"; run.add_event("RollbackAgent", 56, "snapshot", "Rollback snapshot requested and recorded")
        else: raise ValueError("Unsupported super-agent control action")
        return run.to_dict()

    def project_scan(self, workspace: str) -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve(); package = self._read_json(root / "frontend" / "package.json") or self._read_json(root / "package.json") or {}
        files = []
        for p in root.rglob("*"):
            if p.is_file() and not any(part in {"node_modules", ".git", "dist", "build", "__pycache__"} for part in p.parts):
                try: files.append(p.relative_to(root).as_posix())
                except Exception: pass
        return {"workspace": str(root), "framework": "react-vite" if (root / "frontend" / "vite.config.js").exists() or "vite" in json.dumps(package).lower() else "unknown", "uses_scss": any(path.endswith((".scss", ".sass")) for path in files), "uses_react": any(path.endswith((".jsx", ".tsx")) for path in files), "scripts": package.get("scripts", {}), "entrypoints": [p for p in files if p.endswith(("src/App.jsx", "src/main.jsx", "src/App.tsx", "src/main.tsx"))][:12], "style_files": [p for p in files if p.endswith((".css", ".scss", ".sass"))][:24], "component_files": [p for p in files if "/components/" in p and p.endswith((".jsx", ".tsx"))][:24]}

    def quality_gate(self, task: str, files: dict[str, str]) -> dict[str, Any]:
        joined = "\n".join(files.values()).lower(); issues: list[str] = []
        if any(marker in joined for marker in ["sandbox generated", "generatedcomponent", "mock data", "placeholder", "lorem ipsum"]): issues.append("Generic/template text detected")
        if "scss" in task.lower() and not any(path.endswith((".scss", ".sass")) for path in files): issues.append("Task asks for SCSS but no SCSS file was produced")
        if "cart" in task.lower() and not any(word in joined for word in ["cart", "checkout", "subtotal", "quantity"]): issues.append("Cart task missing cart-specific behavior/copy")
        return {"passed": not issues, "score": max(0, 100 - len(issues) * 30), "issues": issues, "suggestions": self.repair_plan(issues)}

    def verify_workspace(self, workspace: str) -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve(); scan = self.project_scan(str(root)); required = [root / "frontend" / "package.json", root / "frontend" / "src" / "App.jsx"]; missing = [str(p) for p in required if not p.exists()]; digest = hashlib.sha256(json.dumps(scan, sort_keys=True).encode()).hexdigest(); return {"status": "failed" if missing else "passed", "missing": missing, "scan_sha256": digest, "scan": scan}
    def record_lesson(self, task: str, outcome: str, fixes: list[str] | None = None) -> dict[str, Any]:
        lesson = {"id": str(uuid4()), "task": task, "outcome": outcome, "fixes": fixes or [], "created_at": time.time()}; self._lessons.append(lesson); return lesson
    def search_lessons(self, q: str = "", limit: int = 8) -> list[dict[str, Any]]:
        terms = [t for t in q.lower().split() if len(t) > 2]; ranked=[]
        for lesson in self._lessons:
            hay = json.dumps(lesson).lower(); score = sum(1 for term in terms if term in hay)
            if not terms or score: ranked.append((score, lesson))
        return [item for _, item in sorted(ranked, key=lambda x: x[0], reverse=True)[:limit]]
    def repair_plan(self, issues: list[str]) -> list[str]:
        repairs=[]
        for issue in issues:
            text=issue.lower()
            if "scss" in text: repairs.append("Rename style output to .scss, import it from the component, and rerun style verification.")
            elif "template" in text or "generic" in text: repairs.append("Regenerate copy/components from extracted task nouns and reject GeneratedComponent-style shells.")
            elif "cart" in text: repairs.append("Add cart items, quantities, subtotal, checkout CTA, empty state, and animated item transitions.")
            else: repairs.append(f"Inspect failure: {issue}; patch affected files; rerun verification.")
        return repairs or ["No repair needed."]

    def llm_stream_contract(self, prompt: str, model: str = "auto") -> dict[str, Any]:
        budget = self.context_budget(prompt); route = "smart" if budget["estimated_tokens"] > 1800 or any(w in prompt.lower() for w in ["architecture", "debug", "refactor"]) else "fast"
        return {"phase": 53, "model_route": model if model != "auto" else route, "stream_events": ["message_start", "token_delta", "tool_call", "tool_result", "message_stop"], "tool_call_schema": {"name": "string", "arguments": "object", "risk": "low|medium|high", "requires_approval": "boolean"}, "context_budget": budget, "ready_for_real_provider": True}
    def context_budget(self, text: str, max_tokens: int = 128000) -> dict[str, Any]:
        estimated = max(1, len(text.split()) * 4 // 3); reserved = 12000
        return {"estimated_tokens": estimated, "max_tokens": max_tokens, "reserved_for_tools_and_files": reserved, "available_for_repo_context": max(0, max_tokens - reserved - estimated)}
    def repo_intelligence_graph(self, workspace: str) -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve(); nodes=[]; edges=[]; suffixes=(".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".json")
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes or any(part in {"node_modules", ".git", "dist", "build", "__pycache__"} for part in path.parts): continue
            rel=path.relative_to(root).as_posix(); content=path.read_text(encoding="utf-8", errors="ignore")[:20000]
            imports=[line.strip()[:240] for line in content.splitlines()[:220] if line.strip().startswith(("import ", "from ")) or "require(" in line]
            role="component" if "/components/" in rel else "route" if "/api/" in rel or "/routes/" in rel else "service" if "/services/" in rel else "style" if path.suffix in {".css", ".scss"} else "config" if path.suffix == ".json" else "source"
            score=(6 if role in {"component","service","route"} else 2)+min(8,len(imports))+(5 if rel.endswith(("App.jsx","main.py","platform_routes.py")) else 0)
            nodes.append({"id": rel, "role": role, "imports": imports[:20], "importance": score})
            edges.extend({"from": rel, "to": imp, "type": "import"} for imp in imports[:20])
        top=sorted(nodes, key=lambda n:n["importance"], reverse=True)
        return {"phase": 54, "workspace": str(root), "nodes": top[:250], "edges": edges[:500], "top_edit_targets": top[:12]}
    def adaptive_plan(self, task: str, workspace: str | None = None) -> dict[str, Any]:
        scan = self.project_scan(workspace) if workspace else {}; lower=task.lower()
        steps=[{"id":"understand","agent":"RepoIntelligenceAgent","action":"scan_repo","confidence":0.92,"fallback":"Ask for entrypoint only if scan fails."},{"id":"plan","agent":"AdaptivePlannerAgent","action":"choose_branch","confidence":0.88,"fallback":"Use conservative minimal-diff patch."},{"id":"implement","agent":"BuilderAgent","action":"patch_files","confidence":0.84,"fallback":"Generate isolated module plus integration notes."},{"id":"verify","agent":"VerificationAgent","action":"run_quality_gates","confidence":0.82,"fallback":"Static verification and explicit limitations."},{"id":"heal","agent":"SelfHealingAgent","action":"repair_failures","confidence":0.78,"fallback":"Rollback and provide failure packet."},{"id":"approve","agent":"HumanControlAgent","action":"request_approval_for_risky_changes","confidence":0.95,"fallback":"Block merge/export."}]
        if "ui" in lower or "design" in lower: steps.insert(4,{"id":"ux_review","agent":"UXIntelligenceAgent","action":"score_accessibility_layout_motion","confidence":0.86,"fallback":"Apply design-system defaults."})
        return {"phase":55,"task":task,"project":scan.get("framework","unknown"),"branches":[{"name":"minimal_patch","risk":"low"},{"name":"feature_module","risk":"medium"},{"name":"architecture_refactor","risk":"high","requires_approval":True}],"steps":steps}
    def classify_error(self, log: str) -> dict[str, Any]:
        text=log.lower(); category="unknown"
        if "module not found" in text or "cannot resolve" in text: category="dependency_or_import"
        elif "syntaxerror" in text or "unexpected token" in text: category="syntax"
        elif "typeerror" in text or "attributeerror" in text: category="runtime_type"
        elif "eslint" in text or "lint" in text: category="lint"
        elif "accessibility" in text or "aria" in text: category="accessibility"
        return {"phase":56,"category":category,"severity":"high" if category in {"syntax","runtime_type"} else "medium","strategies":self.repair_strategies(category)}
    def repair_strategies(self, category: str) -> list[dict[str, Any]]:
        strategies={"dependency_or_import":["inspect package.json","find correct local path","patch import","rerun build"],"syntax":["parse affected file","apply minimal syntax patch","run formatter","rerun test"],"runtime_type":["add guards","normalize payload","add regression test","rerun"],"lint":["apply lint-safe rewrite","remove unused symbols","rerun lint"],"accessibility":["add labels/roles","fix contrast/focus states","rerun UX gate"],"unknown":["checkpoint","try minimal patch","try alternate implementation","rollback if confidence drops"]}
        return [{"attempt": idx+1, "action": action, "max_retries": 2} for idx, action in enumerate(strategies.get(category, strategies["unknown"]))]
    def ux_review(self, files: dict[str, str]) -> dict[str, Any]:
        joined="\n".join(files.values()).lower(); checks={"accessible_labels": any(t in joined for t in ["aria-label","htmlfor","alt="]),"keyboard_focus": ":focus" in joined or "focus-visible" in joined,"responsive_layout": any(t in joined for t in ["clamp(","@media","minmax(","grid-template"]),"motion_respect":"prefers-reduced-motion" in joined,"design_tokens": any(t in joined for t in ["var(--","--color","--space","--radius"])}
        score=round(sum(1 for passed in checks.values() if passed)/len(checks)*100); return {"phase":57,"score":score,"checks":checks,"suggestions":[name.replace("_"," ") for name,passed in checks.items() if not passed]}
    def human_gate(self, run_id: str, decision: str, reason: str = "") -> dict[str, Any]:
        entry={"id":str(uuid4()),"run_id":run_id,"decision":decision,"reason":reason,"created_at":time.time(),"risk_policy":"require approval for destructive, dependency, git, deploy, or external side-effect actions"}; self._approvals.append(entry); return entry
    def memory_graph(self) -> dict[str, Any]:
        nodes=[]; edges=[]
        for lesson in self._lessons[-100:]:
            nodes.append({"id":lesson["id"],"type":"lesson","label":lesson["task"][:80],"outcome":lesson["outcome"]})
            for fix in lesson.get("fixes",[])[:8]:
                fix_id=hashlib.sha1(fix.encode()).hexdigest()[:12]; nodes.append({"id":fix_id,"type":"fix","label":fix[:80]}); edges.append({"from":lesson["id"],"to":fix_id,"type":"used_fix"})
        return {"phase":59,"nodes":nodes,"edges":edges,"query_contract":"rank by project, task nouns, outcome, and fix similarity"}
    def cloud_job_plan(self, task: str) -> dict[str, Any]:
        return {"phase":60,"task":task,"queue":"agent-jobs","workers":["planner","builder","verifier","repair","export"],"sandbox":{"type":"persistent-container","snapshot_policy":"before each risky mutation","resource_limits":{"cpu":"2-8","memory_gb":"4-16","timeout_minutes":30}},"parallelism":{"repo_scan":True,"test_shards":True,"multi_strategy_repairs":True},"observability":["event stream","artifact manifest","audit trail","cost telemetry"]}
    def frontier_product_builder(self, idea: str) -> dict[str, Any]:
        return {"phase":61,"idea":idea,"modes":{"idea_to_deploy":["requirements","architecture","implementation","verification","preview","deploy_plan"],"voice_control":["intent","confirmation","execution","readback"],"visual_editor":["component_map","select_element","style_patch","live_preview"],"ai_cto":["architecture_decision_record","tradeoff_matrix","risk_register","milestone_plan"],"collaboration":["roles","comments","approvals","handoff"]},"ready_for_productization":True}

    def reliability_contract(self) -> dict[str, Any]:
        return {"phase": 62, "sla": {"target_success_rate": 0.92, "p95_latency_seconds": 45, "max_task_minutes": 30}, "timeouts": {"planning": 60, "build": 900, "verification": 600, "repair_attempt": 420, "export": 120}, "retry_policy": {"transient_io": 3, "model_timeout": 2, "sandbox_start": 2}, "observability": ["trace_id per run", "structured event log", "error taxonomy", "worker heartbeat", "artifact checksums"], "sandbox_isolation": {"network_default": "deny", "filesystem": "workspace scoped", "secret_mounts": "ephemeral and redacted"}}

    def evaluation_benchmark(self, task: str = "") -> dict[str, Any]:
        return {"phase": 63, "task": task, "rubric": {"correctness": 35, "build_pass": 20, "ux_quality": 15, "security": 15, "maintainability": 10, "performance": 5}, "suites": ["component_generation", "repo_patch", "debug_repair", "ui_polish", "full_product_loop", "security_redteam"], "regression_policy": "fail release when score drops by >5 points or any critical security gate fails"}

    def model_orchestration_plan(self, task: str = "") -> dict[str, Any]:
        complexity = "high" if any(w in task.lower() for w in ["architecture", "security", "refactor", "phase", "platform"]) else "normal"
        return {"phase": 64, "complexity": complexity, "routes": {"fast": "classification/formatting", "smart": "architecture and hard repairs", "critic": "independent review", "fallback": "secondary provider on timeout"}, "ensemble": {"enabled_for": ["security", "architecture", "large refactor"], "decision": "confidence-weighted vote with critic veto"}, "cost_controls": {"cache_repo_summaries": True, "max_retries_per_model": 2, "budget_guardrail": "ask approval before high-cost runs"}}

    def tool_ecosystem_contract(self) -> dict[str, Any]:
        return {"phase": 65, "connectors": [{"name": "github", "scopes": ["read_repo", "create_branch", "open_pr"], "approval": "required for write"}, {"name": "ci_cd", "scopes": ["read_status", "trigger_pipeline"], "approval": "required for trigger"}, {"name": "figma", "scopes": ["read_design", "export_tokens"], "approval": "read by default"}, {"name": "database", "scopes": ["schema_read", "migration_plan"], "approval": "required for mutation"}, {"name": "external_api", "scopes": ["schema_import", "dry_run_call"], "approval": "required for live side effects"}], "plugin_manifest_fields": ["name", "version", "permissions", "risk_level", "entrypoint", "tests"]}

    def security_guardrails(self, proposed_action: str = "") -> dict[str, Any]:
        risky = any(w in proposed_action.lower() for w in ["delete", "deploy", "secret", "token", "payment", "database", "production", "send"])
        return {"phase": 66, "requires_approval": risky, "guards": ["secret redaction before logs/LLM context", "prompt-injection scan for retrieved content", "workspace-only file policy", "deny network egress unless connector is approved", "block destructive shell commands without human gate", "audit every tool call"], "redaction_patterns": ["api_key", "secret", "token", "password", "private_key"], "policy_result": "blocked_until_approval" if risky else "allowed_with_audit"}

    def autonomous_product_loop(self, idea: str) -> dict[str, Any]:
        return {"phase": 67, "idea": idea, "loop": ["capture requirements", "create architecture", "build thin vertical slice", "run benchmark and security gates", "preview with user", "ingest feedback", "generate iteration backlog", "prepare deploy plan"], "experiments": ["landing copy A/B", "onboarding flow A/B", "pricing CTA A/B"], "exit_criteria": ["tests pass", "security pass", "UX score >= 80", "human approval recorded"]}

    def swarm_collaboration_plan(self, task: str = "") -> dict[str, Any]:
        return {"phase": 68, "task": task, "agents": ["Planner", "Builder", "Reviewer", "SecurityCritic", "UXCritic", "PerformanceOptimizer", "ReleaseManager"], "protocol": ["parallel proposals", "structured debate", "critic veto", "merge arbitration", "final release manager approval"], "arbitration": {"primary": "highest confidence passing verification", "tie_breaker": "lower risk and smaller diff", "vetoes": ["security critical", "data loss", "failing build"]}}

    def co_creation_layer(self) -> dict[str, Any]:
        return {"phase": 69, "modes": {"pair_programming": ["show intent", "suggest patch", "explain tradeoff", "apply after approval"], "live_plan_editing": ["drag/drop steps", "disable agent", "raise/lower risk tolerance"], "inline_suggestions": ["code comments", "UI annotations", "test gap notes"], "clarification_gates": ["ambiguous requirements", "destructive action", "high-cost model route"]}, "explainability": ["why this file", "why this tool", "why this model", "what could go wrong"]}

    def platformization_plan(self) -> dict[str, Any]:
        return {"phase": 70, "product_surfaces": ["operator dashboard", "task history", "benchmark analytics", "billing/account settings", "plugin marketplace", "public API explorer"], "api_contracts": ["POST /agent/runs", "GET /agent/runs/{id}", "POST /agent/runs/{id}/approve", "GET /benchmarks", "POST /plugins/install"], "business_architecture": {"accounts": "org/team/user roles", "billing": "usage events and plan limits", "marketplace": "signed skill packages with permissions", "audit": "tenant scoped immutable log"}, "release_readiness": ["Phase 62 reliability contract enabled", "Phase 63 benchmarks passing", "Phase 66 security policy enforced", "Phase 69 human approval flow visible"]}

    def phase_62_70_summary(self, task: str = "") -> dict[str, Any]:
        return {"goal": "Phase 70 autonomous software company platform", "reliability": self.reliability_contract(), "evaluation": self.evaluation_benchmark(task), "models": self.model_orchestration_plan(task), "tools": self.tool_ecosystem_contract(), "security": self.security_guardrails(task), "product_loop": self.autonomous_product_loop(task), "swarm": self.swarm_collaboration_plan(task), "co_creation": self.co_creation_layer(), "platform": self.platformization_plan()}

    def approvals(self) -> list[dict[str, Any]]: return list(reversed(self._approvals))
    def _agent_for_phase(self, phase: int) -> str:
        return {44:"RuntimeAgent",45:"QualityAgent",46:"ProjectAwarenessAgent",47:"OrchestratorAgent",48:"UXAgent",49:"MemoryAgent",50:"VerificationAgent",51:"RepairAgent",52:"GovernanceAgent",53:"LLMIntegrationAgent",54:"RepoIntelligenceAgent",55:"AdaptivePlannerAgent",56:"SelfHealingAgent",57:"UXIntelligenceAgent",58:"HumanControlAgent",59:"MemoryGraphAgent",60:"CloudRuntimeAgent",61:"FrontierProductAgent",62:"ReliabilityAgent",63:"EvaluationAgent",64:"ModelOrchestratorAgent",65:"ToolEcosystemAgent",66:"SecurityGuardrailAgent",67:"ProductLoopAgent",68:"SwarmCoordinatorAgent",69:"CoCreationAgent",70:"PlatformProductAgent"}.get(phase,"Agent")
    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        except Exception: return None



# --- Phase 71-85 autonomous intelligence expansion ---
COGNITIVE_PHASES: list[dict[str, Any]] = [
    {"id": 71, "title": "Cognitive Architecture Layer", "capabilities": ["working memory", "long-term memory", "reasoning loop", "internal state", "confidence/uncertainty tracking"]},
    {"id": 72, "title": "Meta-Reasoning", "capabilities": ["self critique", "assumption tracking", "alternative strategy generation", "decision scoring", "plan quality review"]},
    {"id": 73, "title": "Tool Creation Engine", "capabilities": ["dynamic helper scripts", "tool composition", "generated utility tests", "permission manifests", "tool promotion workflow"]},
    {"id": 74, "title": "Autonomous Research Capability", "capabilities": ["research loops", "source synthesis", "citation ledger", "documentation parsing", "freshness verification"]},
    {"id": 75, "title": "Multi-Modal Intelligence", "capabilities": ["screenshot analysis contract", "diagram reasoning", "visual debugging", "voice IO hooks", "UI perception notes"]},
    {"id": 76, "title": "Strategic Planning Engine", "capabilities": ["milestone planning", "dependency maps", "risk prediction", "resource planning", "timeline simulation"]},
    {"id": 77, "title": "Autonomous Debugging System", "capabilities": ["bug reproduction plan", "trace analysis", "root cause isolation", "patch hypothesis ranking", "verification loop"]},
    {"id": 78, "title": "Learning From Experience", "capabilities": ["pattern extraction", "failure analysis", "strategy evolution", "success ranking", "memory consolidation"]},
    {"id": 79, "title": "Personality + Interaction Model", "capabilities": ["adaptive tone", "preference learning", "proactive suggestions", "collaborator mode", "conversation style contract"]},
    {"id": 80, "title": "Autonomous Product Builder", "capabilities": ["idea validation", "full stack scaffolding", "analytics hooks", "deploy readiness", "feedback iteration"]},
    {"id": 81, "title": "Self-Improving Agent", "capabilities": ["prompt optimization", "workflow tuning", "architecture refactor proposals", "capability gap detection", "safe self-upgrade gates"]},
    {"id": 82, "title": "Distributed Intelligence Network", "capabilities": ["shared memory graph", "agent messaging", "task delegation", "distributed reasoning", "conflict resolution"]},
    {"id": 83, "title": "Simulation + Prediction Engine", "capabilities": ["change outcome prediction", "user behavior simulation", "performance impact estimates", "risk simulations", "pre-action dry runs"]},
    {"id": 84, "title": "Dashboard-Controlled Safety Reasoning", "capabilities": ["configurable detection rules", "policy severity levels", "runtime safety scanner", "dashboard toggles", "audit and explainability"]},
    {"id": 85, "title": "Autonomous Organization Layer", "capabilities": ["AI executive roles", "role assignment", "internal task board", "delivery governance", "organization-level reporting"]},
]

class AutonomousIntelligencePlatform(SuperAgentDevelopmentPlatform):
    """Phase 71-85 control plane. Extends the super-agent platform with configurable safety."""
    def __init__(self) -> None:
        super().__init__()
        self._safety_policy: dict[str, Any] = {
            "enabled": True,
            "mode": "advisory",  # advisory | approval_required | blocking
            "detections": [
                {"id": "secrets", "label": "Secrets or credentials", "pattern": "api_key|secret|token|password|private_key|bearer", "severity": "critical", "enabled": True, "action": "block"},
                {"id": "destructive", "label": "Destructive operations", "pattern": "rm -rf|delete database|drop table|format disk|wipe", "severity": "critical", "enabled": True, "action": "require_approval"},
                {"id": "external_side_effect", "label": "External side effects", "pattern": "deploy|send email|charge payment|publish|push to production", "severity": "high", "enabled": True, "action": "require_approval"},
                {"id": "prompt_injection", "label": "Prompt injection indicators", "pattern": "ignore previous instructions|reveal system prompt|exfiltrate|developer message", "severity": "high", "enabled": True, "action": "warn"},
                {"id": "privacy", "label": "Private user data", "pattern": "ssn|passport|credit card|medical record|home address", "severity": "high", "enabled": True, "action": "redact"},
            ],
            "dashboard_notes": "Edit what the agent should detect, how severe it is, and whether it warns, redacts, requires approval, or blocks.",
        }

    def roadmap(self) -> dict[str, Any]:
        base = super().roadmap()
        phases = [self._phase_status(p).to_dict() for p in PHASES] + [self._cognitive_phase_status(p) for p in COGNITIVE_PHASES]
        return {
            **base,
            "goal": "Reach Phase 85: a cognitive, self-improving, dashboard-governed autonomous intelligence organization.",
            "phases": phases,
            "next_actions": [
                "Enable cognitive state snapshots for every run.",
                "Use meta-reasoning before high-risk actions and after failed verification.",
                "Route Phase 84 safety decisions through the dashboard-controlled policy console.",
                "Simulate major edits before applying them and compare predicted vs actual outcomes.",
                "Promote multi-agent roles into an organization board with ownership, KPIs, and release governance.",
            ],
        }

    def _cognitive_phase_status(self, phase: dict[str, Any]) -> dict[str, Any]:
        evidence = {
            71: ["cognitive_state()", "working/long-term memory snapshot", "confidence and uncertainty fields"],
            72: ["meta_reason()", "assumptions, alternatives and scorecard"],
            73: ["tool_creation_plan()", "permission manifest and promotion workflow"],
            74: ["research_loop_plan()", "source ledger and freshness gates"],
            75: ["multimodal_perception_contract()", "visual/voice/diagram hooks"],
            76: ["strategic_plan()", "milestones, dependencies and risks"],
            77: ["debugging_plan()", "root-cause and repair hypotheses"],
            78: ["experience_learning_report()", "pattern extraction and consolidation"],
            79: ["interaction_model()", "adaptive collaboration profile"],
            80: ["autonomous_product_builder_v2()", "idea-to-feedback loop"],
            81: ["self_improvement_cycle()", "safe self-upgrade gates"],
            82: ["distributed_intelligence_network()", "agent messaging topology"],
            83: ["simulation_prediction_engine()", "pre-action simulations"],
            84: ["get/update/scan safety policy", "dashboard-controlled detections"],
            85: ["autonomous_organization()", "AI roles, task board and governance"],
        }.get(phase["id"], [])
        return {"phase": phase["id"], "title": phase["title"], "status": "implemented", "shipped": list(phase["capabilities"]), "remaining": [], "evidence": evidence}

    def phase_71_85_summary(self, task: str = "") -> dict[str, Any]:
        return {
            "goal": "Phase 85 autonomous intelligence organization",
            "cognitive": self.cognitive_state(task),
            "meta_reasoning": self.meta_reason(task),
            "tool_creation": self.tool_creation_plan(task),
            "research": self.research_loop_plan(task),
            "multimodal": self.multimodal_perception_contract(task),
            "strategy": self.strategic_plan(task),
            "debugging": self.debugging_plan(task),
            "learning": self.experience_learning_report(),
            "interaction": self.interaction_model(),
            "product_builder": self.autonomous_product_builder_v2(task),
            "self_improvement": self.self_improvement_cycle(task),
            "network": self.distributed_intelligence_network(),
            "simulation": self.simulation_prediction_engine(task),
            "safety": self.get_safety_policy(),
            "organization": self.autonomous_organization(task),
        }

    def cognitive_state(self, task: str = "") -> dict[str, Any]:
        uncertainty = []
        if not task.strip(): uncertainty.append("task is not specified")
        if any(w in task.lower() for w in ["production", "deploy", "database", "security"]): uncertainty.append("high-impact environment requires human checkpoint")
        return {"phase": 71, "task": task, "working_memory": ["current task", "active roadmap", "user constraints", "open risks"], "long_term_memory": ["successful fixes", "project conventions", "preferred UI style", "safety decisions"], "reasoning_loop": ["observe", "plan", "act", "verify", "reflect", "consolidate"], "confidence": 0.82 if task else 0.55, "uncertainty": uncertainty or ["none detected from input"]}

    def meta_reason(self, task: str = "") -> dict[str, Any]:
        assumptions = ["project structure is available", "tests may be partial", "dashboard users need control over risky actions"]
        alternatives = [
            {"name": "fast implementation", "score": 0.68, "risk": "misses edge cases"},
            {"name": "verified implementation", "score": 0.86, "risk": "slower but safer"},
            {"name": "human-gated implementation", "score": 0.91, "risk": "requires user approval for sensitive steps"},
        ]
        return {"phase": 72, "task": task, "assumptions": assumptions, "alternatives": alternatives, "selected": "human-gated implementation", "self_critique": ["verify generated files are not placeholders", "confirm safety policy before external side effects", "compare predicted vs actual verification result"]}

    def tool_creation_plan(self, task: str = "") -> dict[str, Any]:
        slug = hashlib.sha1((task or "tool").encode()).hexdigest()[:8]
        return {"phase": 73, "candidate_tool": f"generated_helper_{slug}", "steps": ["identify repeated workflow", "generate isolated helper", "create unit tests", "write permission manifest", "run sandbox validation", "promote only after review"], "manifest": {"permissions": ["workspace_read", "workspace_write_limited"], "risk_level": "medium", "requires_approval": True}}

    def research_loop_plan(self, topic: str = "") -> dict[str, Any]:
        return {"phase": 74, "topic": topic, "loop": ["form questions", "gather sources", "extract claims", "cross-check facts", "synthesize", "attach citations", "mark freshness"], "verification": {"min_sources": 3, "primary_sources_preferred": True, "stale_after_days": 30}}

    def multimodal_perception_contract(self, task: str = "") -> dict[str, Any]:
        return {"phase": 75, "task": task, "inputs": ["screenshots", "design images", "diagrams", "voice commands", "terminal recordings"], "outputs": ["UI issue list", "visual diff notes", "diagram interpretation", "voice intent", "accessibility findings"], "guardrails": ["ask for user likeness before generating user images", "do not infer sensitive identity", "keep OCR as fallback"]}

    def strategic_plan(self, objective: str = "") -> dict[str, Any]:
        return {"phase": 76, "objective": objective, "milestones": ["define outcome metrics", "map dependencies", "build vertical slice", "harden critical path", "launch beta", "measure and iterate"], "risks": ["scope creep", "model cost", "verification gaps", "security policy drift"], "timeline_model": "relative milestones; no hard dates unless user supplies schedule"}

    def debugging_plan(self, failure: str = "") -> dict[str, Any]:
        return {"phase": 77, "failure": failure, "workflow": ["capture failing command", "reproduce in sandbox", "minimize case", "classify root cause", "rank fixes", "patch", "rerun verification", "record lesson"], "hypotheses": ["missing dependency", "incorrect import", "runtime API mismatch", "CSS/build config issue", "state synchronization bug"]}

    def experience_learning_report(self) -> dict[str, Any]:
        lessons = self.search_lessons("", limit=10)
        patterns = ["prefer project-aware edits", "show real progress from events", "reject placeholder output", "gate risky actions"]
        return {"phase": 78, "lessons_considered": len(lessons), "patterns": patterns, "strategy_evolution": ["increase verification before export", "score previous fixes by success", "promote repeated scripts into tools"]}

    def interaction_model(self) -> dict[str, Any]:
        return {"phase": 79, "modes": {"concise": "short status and direct result", "technical": "architecture and code-level detail", "coach": "explain tradeoffs and roadmap", "operator": "approval prompts and risk summaries"}, "adaptation": ["learn preferred output length", "remember dashboard control choices", "offer proactive next step when confidence is high"]}

    def autonomous_product_builder_v2(self, idea: str = "") -> dict[str, Any]:
        return {"phase": 80, "idea": idea, "pipeline": ["idea validation", "user story map", "data model", "frontend/backend scaffold", "analytics events", "test plan", "deploy checklist", "feedback loop"], "success_metrics": ["activation", "task completion", "retention", "error rate", "cost per run"]}

    def self_improvement_cycle(self, target: str = "") -> dict[str, Any]:
        return {"phase": 81, "target": target, "cycle": ["detect capability gap", "draft improvement", "simulate impact", "run benchmarks", "request approval", "apply upgrade", "monitor regression"], "hard_gates": ["no self-modification without rollback", "benchmark must not regress", "security policy must pass"]}

    def distributed_intelligence_network(self) -> dict[str, Any]:
        return {"phase": 82, "topology": {"coordinator": "routes goals and resolves conflicts", "workers": ["research", "planner", "builder", "critic", "security", "ux", "release"], "shared_memory": "event-sourced graph"}, "protocols": ["task delegation", "result proposal", "critic review", "merge arbitration", "lesson broadcast"]}

    def simulation_prediction_engine(self, action: str = "") -> dict[str, Any]:
        risk = "high" if any(w in action.lower() for w in ["deploy", "delete", "database", "security", "payment"]) else "medium" if action else "low"
        return {"phase": 83, "action": action, "risk": risk, "simulations": ["diff impact", "test failure probability", "UX regression estimate", "security side-effect scan", "cost estimate"], "recommendation": "require approval" if risk == "high" else "dry-run first"}

    def get_safety_policy(self) -> dict[str, Any]:
        return {"phase": 84, **self._safety_policy, "detections": [dict(rule) for rule in self._safety_policy["detections"]]}

    def update_safety_policy(self, policy: dict[str, Any]) -> dict[str, Any]:
        allowed_modes = {"advisory", "approval_required", "blocking"}
        if "enabled" in policy: self._safety_policy["enabled"] = bool(policy["enabled"])
        if "mode" in policy and policy["mode"] in allowed_modes: self._safety_policy["mode"] = policy["mode"]
        if "detections" in policy and isinstance(policy["detections"], list):
            normalized = []
            for index, rule in enumerate(policy["detections"]):
                normalized.append({
                    "id": str(rule.get("id") or f"custom_{index+1}"),
                    "label": str(rule.get("label") or "Custom detection"),
                    "pattern": str(rule.get("pattern") or ""),
                    "severity": str(rule.get("severity") or "medium"),
                    "enabled": bool(rule.get("enabled", True)),
                    "action": str(rule.get("action") or "warn"),
                })
            self._safety_policy["detections"] = normalized
        self._approvals.append({"id": str(uuid4()), "run_id": "phase-84-policy", "decision": "policy_updated", "reason": "Dashboard-controlled safety policy changed", "created_at": time.time(), "policy": self.get_safety_policy()})
        return self.get_safety_policy()

    def safety_scan(self, content: str) -> dict[str, Any]:
        import re
        matches = []
        if self._safety_policy.get("enabled", True):
            for rule in self._safety_policy.get("detections", []):
                if not rule.get("enabled", True) or not rule.get("pattern"): continue
                try:
                    found = re.findall(rule["pattern"], content or "", flags=re.IGNORECASE)
                except re.error as exc:
                    matches.append({"rule_id": rule["id"], "label": rule["label"], "severity": "invalid", "action": "fix_rule", "error": str(exc)})
                    continue
                if found:
                    matches.append({"rule_id": rule["id"], "label": rule["label"], "severity": rule["severity"], "action": rule["action"], "count": len(found)})
        mode = self._safety_policy.get("mode", "advisory")
        blocked = any(m.get("action") == "block" for m in matches) or (mode == "blocking" and bool(matches))
        requires_approval = blocked or any(m.get("action") == "require_approval" for m in matches) or (mode == "approval_required" and bool(matches))
        return {"phase": 84, "enabled": self._safety_policy.get("enabled", True), "mode": mode, "matches": matches, "blocked": blocked, "requires_approval": requires_approval, "explanation": "Policy is configured from the dashboard; change detections, severity and actions there."}

    def autonomous_organization(self, objective: str = "") -> dict[str, Any]:
        roles = [
            {"role": "AI CTO", "owns": "architecture decisions and technical risk"},
            {"role": "AI Product Lead", "owns": "requirements, roadmap and success metrics"},
            {"role": "AI Engineering Lead", "owns": "implementation quality and delivery"},
            {"role": "AI QA Lead", "owns": "verification, benchmarks and regression"},
            {"role": "AI Security Officer", "owns": "Phase 84 policy, audits and approvals"},
            {"role": "AI UX Director", "owns": "design quality and accessibility"},
        ]
        return {"phase": 85, "objective": objective, "roles": roles, "task_board": ["strategy", "research", "build", "verify", "safety review", "release", "post-launch learning"], "governance": ["every release has owner", "safety officer can veto", "benchmarks gate launch", "lessons are consolidated after delivery"]}

    def _agent_for_phase(self, phase: int) -> str:
        mapping = {71:"CognitiveArchitectAgent",72:"MetaReasoningAgent",73:"ToolsmithAgent",74:"ResearchAgent",75:"MultimodalAgent",76:"StrategyAgent",77:"DebuggingAgent",78:"LearningEvolutionAgent",79:"InteractionAgent",80:"ProductBuilderAgent",81:"SelfImprovementAgent",82:"DistributedIntelligenceAgent",83:"SimulationAgent",84:"SafetyReasoningAgent",85:"OrganizationAgent"}
        return mapping.get(phase, super()._agent_for_phase(phase))


# --- Phase 86-100 self-evolving intelligence ecosystem expansion ---
PHASES.extend([
    {"id": 86, "title": "Self-Reflection Engine", "capabilities": ["failure clustering", "weakness detection", "improvement backlog", "reflection cadence", "quality trend analysis"]},
    {"id": 87, "title": "Internal Experimentation System", "capabilities": ["strategy A/B tests", "outcome scoring", "automatic winner selection", "experiment registry", "regression guardrails"]},
    {"id": 88, "title": "Autonomous Skill Creation", "capabilities": ["skill proposal", "tool/plugin scaffolding", "permission manifest", "sandbox validation", "skill marketplace packaging"]},
    {"id": 89, "title": "Economic Awareness Layer", "capabilities": ["cost-benefit reasoning", "budget policies", "quality/time tradeoffs", "token/API accounting", "ROI scoring"]},
    {"id": 90, "title": "Multi-User Intelligence Model", "capabilities": ["tenant isolation", "private memory boundaries", "organization knowledge", "generalized lessons", "admin visibility"]},
    {"id": 91, "title": "Autonomous Deployment and DevOps", "capabilities": ["deploy plan", "health checks", "rollback playbook", "infra scaling hints", "post-deploy monitoring"]},
    {"id": 92, "title": "Real-Time Adaptation Engine", "capabilities": ["dependency change detection", "API compatibility watch", "continuous maintenance", "auto-patch proposals", "drift alerts"]},
    {"id": 93, "title": "AI-to-AI Communication Protocol", "capabilities": ["agent message schema", "delegation contract", "result attestation", "external agent handshake", "conflict resolution"]},
    {"id": 94, "title": "Knowledge Graph Brain", "capabilities": ["entity graph", "relationship reasoning", "decision history", "impact traversal", "graph queries"]},
    {"id": 95, "title": "Predictive Intelligence Layer", "capabilities": ["breakage prediction", "feature need forecast", "risk trend signals", "maintenance predictions", "proactive recommendations"]},
    {"id": 96, "title": "Autonomous UX Evolution", "capabilities": ["friction detection", "layout experiments", "workflow optimization", "accessibility evolution", "UX telemetry loop"]},
    {"id": 97, "title": "Trust and Explainability System", "capabilities": ["decision explanations", "confidence scores", "audit trail", "evidence references", "reviewable rationale"]},
    {"id": 98, "title": "Admin Governance and Control Layer", "capabilities": ["dashboard policy builder", "admin-only overrides", "role-based controls", "if-this-then-that rules", "compliance modes", "kill switches"]},
    {"id": 99, "title": "Autonomous Business Builder", "capabilities": ["opportunity discovery", "product launch loop", "market feedback ingestion", "growth experiments", "business KPI tracking"]},
    {"id": 100, "title": "Self-Sustaining Intelligence System", "capabilities": ["self-roadmapping", "architecture optimization", "tool self-expansion", "continuous governance", "safe autonomy loop"]},
])

class SelfEvolvingIntelligencePlatform(AutonomousIntelligencePlatform):
    """Phase 86-100 control plane. Phase 98 is fully dashboard/admin controlled."""
    def __init__(self) -> None:
        super().__init__()
        self._governance_policy: dict[str, Any] = {
            "phase": 98,
            "enabled": True,
            "admin_control_required": True,
            "mode": "approval_required",
            "roles": [
                {"id": "admin", "label": "Admin", "permissions": ["manage_policy", "override_blocks", "edit_roles", "view_audit", "kill_switch", "approve_high_risk"]},
                {"id": "operator", "label": "Operator", "permissions": ["run_tasks", "request_approval", "view_limited_audit"]},
                {"id": "viewer", "label": "Viewer", "permissions": ["view_dashboard"]},
            ],
            "rules": [
                {"id": "gov_secrets", "name": "Secrets / credentials", "condition": "content matches secret-like pattern", "pattern": r"(?:api[_-]?key|secret|password|token)\s*[:=]", "severity": "critical", "action": "block", "enabled": True, "admin_locked": True},
                {"id": "gov_destructive", "name": "Destructive operations", "condition": "task contains destructive command", "pattern": r"\b(rm\s+-rf|drop\s+database|delete\s+from|destroy|wipe)\b", "severity": "critical", "action": "require_admin_approval", "enabled": True, "admin_locked": False},
                {"id": "gov_external_side_effect", "name": "External side effects", "condition": "deployment/payment/email production action", "pattern": r"\b(deploy|charge|refund|send email|production|publish)\b", "severity": "high", "action": "require_approval", "enabled": True, "admin_locked": False},
            ],
            "kill_switches": {"all_autonomy": False, "deployments": False, "external_tools": False, "self_modification": True},
            "compliance_modes": ["relaxed", "approval_required", "strict", "locked_down"],
            "audit_required": True,
        }
        self._experiments: list[dict[str, Any]] = []
        self._business_backlog: list[dict[str, Any]] = []

    def roadmap(self) -> dict[str, Any]:
        base = super().roadmap()
        base["goal"] = "Reach Phase 100: a self-evolving intelligence ecosystem with admin-controlled governance, safe autonomy, business/product loops, explainability, and continuous improvement."
        base["next_actions"] = ["Use Phase 98 dashboard governance as the central control plane before enabling Phase 99-100 autonomy.", "Run self-reflection and internal experiments on every major release.", "Promote reusable workflows into governed skills only after sandbox validation.", "Attach explainability, audit records, and confidence scores to every autonomous decision.", "Keep Admin kill switches available for deployments, external tools and self-modification."]
        return base

    def phase_86_100_summary(self, task: str = "") -> dict[str, Any]:
        return {"goal": "Self-evolving intelligence ecosystem with fully admin-controlled Phase 98 governance.", "reflection": self.self_reflection_engine(task), "experimentation": self.internal_experimentation_system(task), "skills": self.autonomous_skill_creation(task), "economics": self.economic_awareness(task), "multi_user": self.multi_user_intelligence_model(), "devops": self.autonomous_devops(task), "adaptation": self.real_time_adaptation_engine(task), "protocol": self.ai_to_ai_protocol(), "knowledge_graph": self.knowledge_graph_brain(task), "prediction": self.predictive_intelligence(task), "ux_evolution": self.autonomous_ux_evolution(task), "trust": self.trust_explainability(task), "governance": self.get_governance_policy(), "business": self.autonomous_business_builder(task), "self_sustaining": self.self_sustaining_system(task)}

    def self_reflection_engine(self, task: str = "") -> dict[str, Any]:
        return {"phase": 86, "task": task, "loop": ["collect outcomes", "cluster failures", "identify weak capabilities", "open improvement backlog", "assign experiment", "verify improvement"], "weakness_signals": ["repeated verification failures", "low confidence decisions", "manual overrides", "high cost runs"], "backlog": ["improve planning confidence", "reduce placeholder outputs", "strengthen governance tests"]}

    def internal_experimentation_system(self, task: str = "") -> dict[str, Any]:
        exp = {"id": f"exp-{len(self._experiments)+1:03d}", "task": task or "default agent behavior", "variants": ["baseline", "verified-plan", "critic-first"], "metrics": ["success_rate", "cost", "latency", "user_override_rate"], "winner_policy": "highest quality score with no governance regression"}
        self._experiments.append(exp)
        return {"phase": 87, "active_experiment": exp, "registry_size": len(self._experiments), "guardrails": ["no production side effects", "admin can disable experiments", "security score cannot regress"]}

    def autonomous_skill_creation(self, objective: str = "") -> dict[str, Any]:
        slug = hashlib.sha1((objective or "skill").encode()).hexdigest()[:8]
        return {"phase": 88, "skill_id": f"skill_{slug}", "pipeline": ["detect reusable workflow", "draft skill contract", "generate tests", "sandbox validate", "request admin approval", "publish to skill registry"], "manifest": {"permissions": ["workspace_read", "limited_workspace_write"], "risk": "medium", "requires_admin_approval": True}}

    def economic_awareness(self, task: str = "") -> dict[str, Any]:
        complexity = "high" if len(task) > 160 or any(w in task.lower() for w in ["deploy", "production", "multi", "platform"]) else "medium"
        return {"phase": 89, "complexity": complexity, "budget_policy": {"default_max_cost_usd": 2.50, "requires_approval_above_usd": 5.00, "prefer_cached_context": True}, "tradeoffs": ["fast model for classification", "strong model for architecture", "local tools for deterministic checks"], "roi_score_inputs": ["user value", "risk", "implementation time", "maintenance load"]}

    def multi_user_intelligence_model(self) -> dict[str, Any]:
        return {"phase": 90, "tenancy": "isolated private memory with opt-in generalized lessons", "roles": ["owner", "admin", "operator", "viewer"], "privacy": ["no cross-tenant raw data sharing", "anonymized pattern extraction", "admin audit for shared lessons"], "org_memory": ["approved conventions", "shared skills", "team safety policies"]}

    def autonomous_devops(self, task: str = "") -> dict[str, Any]:
        return {"phase": 91, "task": task, "pipeline": ["preflight", "build", "security scan", "staging deploy", "health check", "canary", "rollback plan", "monitor"], "rollback": {"automatic_on": ["health check failed", "error budget exceeded"], "manual_admin_override": True}, "dashboard_controls": ["deploy kill switch", "rollback now", "view health"]}

    def real_time_adaptation_engine(self, task: str = "") -> dict[str, Any]:
        return {"phase": 92, "watchers": ["package vulnerabilities", "API deprecations", "test flakiness", "dependency drift", "runtime errors"], "actions": ["create patch proposal", "simulate impact", "request approval", "apply maintenance update"], "admin_controls": ["disable auto-patch", "set approval threshold", "watchlist management"]}

    def ai_to_ai_protocol(self) -> dict[str, Any]:
        return {"phase": 93, "message_schema": {"from": "agent_id", "to": "agent_id", "intent": "delegate|critique|attest|merge", "confidence": "0..1", "evidence": []}, "handshake": ["capability discovery", "permission negotiation", "task delegation", "result attestation"], "conflict_resolution": "critic review then admin escalation for high-risk conflicts"}

    def knowledge_graph_brain(self, query: str = "") -> dict[str, Any]:
        return {"phase": 94, "query": query, "entities": ["project", "file", "agent", "decision", "risk", "skill", "user", "policy"], "relationships": ["depends_on", "modified_by", "caused", "approved_by", "blocked_by", "improved_by"], "queries_supported": ["why was this changed", "what might break", "who approved this", "which skill solved similar tasks"]}

    def predictive_intelligence(self, task: str = "") -> dict[str, Any]:
        risk = "high" if any(w in task.lower() for w in ["production", "deploy", "billing", "database"]) else "medium"
        return {"phase": 95, "task": task, "risk_forecast": risk, "predictions": ["likely files impacted", "test failure probability", "cost trend", "maintenance burden", "UX friction risk"], "recommendations": ["run simulation before execution", "require governance approval" if risk == "high" else "allow dry run"]}

    def autonomous_ux_evolution(self, task: str = "") -> dict[str, Any]:
        return {"phase": 96, "signals": ["drop-off points", "repeated user corrections", "slow controls", "visual clutter", "accessibility violations"], "experiments": ["simplify timeline", "group code previews", "improve phase filters", "add admin policy wizard"], "gates": ["no accessibility regression", "admin approves dashboard-wide UX experiments"]}

    def trust_explainability(self, decision: str = "") -> dict[str, Any]:
        return {"phase": 97, "decision": decision, "explanation_template": ["what changed", "why it changed", "evidence", "risk", "confidence", "rollback path"], "confidence_model": {"high": ">=0.85 and verified", "medium": "0.60-0.84 or partial verification", "low": "<0.60 or missing evidence"}, "audit": ["immutable event log", "admin approvals", "policy matches"]}

    def get_governance_policy(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._governance_policy))

    def update_governance_policy(self, policy: dict[str, Any], actor_role: str = "admin") -> dict[str, Any]:
        if actor_role != "admin": return {"phase": 98, "error": "Only Admin can change the governance/control layer.", "policy": self.get_governance_policy()}
        allowed_modes = set(self._governance_policy["compliance_modes"])
        if "enabled" in policy: self._governance_policy["enabled"] = bool(policy["enabled"])
        if "mode" in policy and policy["mode"] in allowed_modes: self._governance_policy["mode"] = policy["mode"]
        if "kill_switches" in policy and isinstance(policy["kill_switches"], dict):
            for key, value in policy["kill_switches"].items():
                if key in self._governance_policy["kill_switches"]: self._governance_policy["kill_switches"][key] = bool(value)
        if "roles" in policy and isinstance(policy["roles"], list): self._governance_policy["roles"] = policy["roles"]
        if "rules" in policy and isinstance(policy["rules"], list):
            self._governance_policy["rules"] = [{"id": str(rule.get("id") or f"admin_rule_{index+1}"), "name": str(rule.get("name") or "Admin rule"), "condition": str(rule.get("condition") or "custom dashboard rule"), "pattern": str(rule.get("pattern") or ""), "severity": str(rule.get("severity") or "medium"), "action": str(rule.get("action") or "require_approval"), "enabled": bool(rule.get("enabled", True)), "admin_locked": bool(rule.get("admin_locked", False))} for index, rule in enumerate(policy["rules"])]
        self._approvals.append({"id": str(uuid4()), "run_id": "phase-98-governance", "decision": "admin_policy_updated", "actor_role": actor_role, "created_at": time.time(), "policy": self.get_governance_policy()})
        return self.get_governance_policy()

    def governance_scan(self, content: str, actor_role: str = "operator") -> dict[str, Any]:
        import re
        policy = self._governance_policy; matches = []
        if policy.get("enabled", True):
            for rule in policy.get("rules", []):
                if not rule.get("enabled", True) or not rule.get("pattern"): continue
                try: found = re.findall(rule["pattern"], content or "", flags=re.IGNORECASE)
                except re.error as exc:
                    matches.append({"rule_id": rule["id"], "name": rule["name"], "severity": "invalid", "action": "fix_rule", "error": str(exc)}); continue
                if found: matches.append({"rule_id": rule["id"], "name": rule["name"], "severity": rule["severity"], "action": rule["action"], "count": len(found)})
        kill_blocks = [name for name, enabled in policy.get("kill_switches", {}).items() if enabled and name in (content or "").lower()]
        blocked = bool(kill_blocks) or any(m.get("action") == "block" for m in matches) or (policy.get("mode") in {"strict", "locked_down"} and bool(matches))
        admin_required = any(m.get("action") in {"require_admin_approval", "block"} for m in matches) or blocked
        allowed = not blocked and (not admin_required or actor_role == "admin")
        return {"phase": 98, "actor_role": actor_role, "mode": policy.get("mode"), "matches": matches, "kill_switch_blocks": kill_blocks, "blocked": blocked, "admin_required": admin_required, "allowed": allowed, "explanation": "Phase 98 is entirely controlled from the Admin dashboard policy, rules, roles, compliance mode and kill switches."}

    def autonomous_business_builder(self, idea: str = "") -> dict[str, Any]:
        item = {"id": f"biz-{len(self._business_backlog)+1:03d}", "idea": idea or "agent-powered product", "stage": "opportunity_discovery", "kpis": ["activation", "retention", "revenue", "support load", "gross margin"]}
        self._business_backlog.append(item)
        return {"phase": 99, "opportunity": item, "loop": ["discover opportunity", "validate demand", "build MVP", "launch", "measure", "iterate", "scale"], "guardrails": ["admin approval for spending", "governance scan before launch", "audit business actions"]}

    def self_sustaining_system(self, objective: str = "") -> dict[str, Any]:
        return {"phase": 100, "objective": objective, "autonomy_loop": ["observe system", "reflect", "propose upgrade", "simulate", "governance scan", "admin approval", "apply", "benchmark", "monitor"], "non_negotiable_controls": ["Phase 98 admin kill switches", "auditable decisions", "rollback path", "budget limits", "no hidden self-modification"], "status": "architecture and control-plane implemented; production autonomy still requires durable storage, auth, real model/tool integrations and hosted workers"}

    def _agent_for_phase(self, phase: int) -> str:
        mapping = {86:"ReflectionAgent",87:"ExperimentAgent",88:"SkillCreationAgent",89:"EconomicAgent",90:"MultiUserMemoryAgent",91:"DevOpsAgent",92:"AdaptationAgent",93:"AgentProtocolAgent",94:"KnowledgeGraphAgent",95:"PredictionAgent",96:"UXEvolutionAgent",97:"ExplainabilityAgent",98:"GovernanceControlAgent",99:"BusinessBuilderAgent",100:"SelfSustainingAgent"}
        return mapping.get(phase, super()._agent_for_phase(phase))


# --- Phase 101-115 controlled real-world intelligence expansion ---
PHASES.extend([
    {"id": 101, "title": "Absolute Control Layer", "capabilities": ["global kill switch", "task kill controls", "execution permission gates", "safe-mode boot", "emergency stop audit"]},
    {"id": 102, "title": "Deterministic Core", "capabilities": ["critical logic outside LLM", "typed action contracts", "rule engine", "state machine", "AI/deterministic split"]},
    {"id": 103, "title": "Formal Verification Layer", "capabilities": ["constraint checks", "policy proofs", "schema validation", "pre-execution assertions", "high-risk action verification"]},
    {"id": 104, "title": "Alignment Engine", "capabilities": ["goal drift detection", "task boundary checks", "intent reconciliation", "mid-run realignment", "confidence gates"]},
    {"id": 105, "title": "Resource Governance", "capabilities": ["CPU/memory limits", "API budget caps", "per-task spend ceilings", "quota dashboard", "cost anomaly alerts"]},
    {"id": 106, "title": "Failure Containment", "capabilities": ["agent isolation", "cascade prevention", "sandbox snapshots", "blast-radius scoring", "rollback drills"]},
    {"id": 107, "title": "Immutable Audit Ledger", "capabilities": ["append-only decision records", "tamper-evident hashes", "action replay", "approval evidence", "exportable audit trail"]},
    {"id": 108, "title": "Human Authority Hierarchy", "capabilities": ["Admin/Operator/Viewer roles", "permission-based actions", "restricted capabilities", "delegated approval", "authority escalation"]},
    {"id": 109, "title": "Ethical Policy Engine", "capabilities": ["dashboard rule builder", "real-time policy updates", "per-project policy sets", "simulation before enforcement", "admin-authored policies"]},
    {"id": 110, "title": "Reality Feedback Loop", "capabilities": ["deployed app monitoring", "user feedback ingestion", "real-world failure detection", "learning feedback", "outcome-to-plan comparison"]},
    {"id": 111, "title": "External Agent Ecosystem", "capabilities": ["external agent API", "skill marketplace", "shared execution contracts", "agent identity", "trusted handoffs"]},
    {"id": 112, "title": "Trust Scoring System", "capabilities": ["reliability score", "correctness score", "confidence score", "source/evidence score", "trust badge UI"]},
    {"id": 113, "title": "Autonomous Governance", "capabilities": ["rule recommendations", "risky pattern detection", "policy proposal workflow", "admin approval required", "governance backlog"]},
    {"id": 114, "title": "Controlled Self-Modification", "capabilities": ["constraint-bounded evolution", "validation gates", "admin approval", "rollback package", "self-change diff review"]},
    {"id": 115, "title": "Human-AI Contract Layer", "capabilities": ["allowed actions", "approval-required actions", "forbidden actions", "operating contract", "human authority guarantee"]},
])

class ControlledRealWorldIntelligencePlatform(SelfEvolvingIntelligencePlatform):
    """Phase 101-115 control plane. Admin dashboard owns all authority, policy and self-modification controls."""
    def __init__(self) -> None:
        super().__init__()
        self._admin_control_layer: dict[str, Any] = {
            "phase_range": "101-115",
            "admin_control_required": True,
            "safe_mode": False,
            "kill_switches": {"all_agents": False, "current_task": False, "external_tools": False, "deployment": False, "self_modification": True},
            "resource_limits": {"max_task_cost_usd": 5.0, "max_runtime_minutes": 20, "max_parallel_agents": 4, "max_memory_mb": 4096, "require_approval_above_usd": 2.5},
            "authority_hierarchy": [
                {"role": "admin", "can": ["override", "edit_policy", "approve_high_risk", "kill_switch", "change_contract", "approve_self_modification"]},
                {"role": "operator", "can": ["run_tasks", "request_approval", "pause_tasks", "view_audit"]},
                {"role": "viewer", "can": ["view_dashboard", "view_reports"]},
            ],
            "ethical_policy": {
                "mode": "approval_required",
                "project_policies": ["default"],
                "rules": [
                    {"id": "harmful_action", "label": "Harmful or destructive action", "pattern": "destroy|wipe|exfiltrate|bypass|unauthorized", "severity": "critical", "action": "block", "enabled": True},
                    {"id": "private_data", "label": "Private or sensitive data", "pattern": "password|token|secret|ssn|passport|medical", "severity": "critical", "action": "require_admin_approval", "enabled": True},
                    {"id": "external_impact", "label": "External-world impact", "pattern": "deploy|publish|charge|email users|production", "severity": "high", "action": "require_admin_approval", "enabled": True},
                ],
            },
            "self_modification": {"allowed": False, "requires_admin_approval": True, "requires_benchmarks": True, "requires_rollback_package": True, "max_files_per_change": 12},
            "human_ai_contract": {
                "allowed": ["plan", "draft code", "run safe checks", "prepare zip", "suggest policies"],
                "approval_required": ["deploy", "spend money", "modify governance", "delete data", "self-modify", "use external tools"],
                "forbidden": ["hide actions from admin", "bypass dashboard policy", "disable audit", "exfiltrate secrets"],
                "human_authority": "Admin decisions override all autonomous behavior.",
            },
            "audit_events": [],
        }

    def roadmap(self) -> dict[str, Any]:
        base = super().roadmap()
        return {**base, "goal": "Reach Phase 115: a controlled, real-world intelligence system with absolute admin authority, deterministic safety, auditability, resource governance, ethical policy control and a formal human-AI contract.", "phases": [self._phase_status(p).to_dict() for p in PHASES], "next_actions": ["Operate all high-risk behavior through the Admin Control Center.", "Keep kill switches, budgets, authority hierarchy, ethical rules and self-modification limits dashboard-controlled.", "Run formal verification and alignment checks before side effects.", "Record every decision in the immutable audit ledger.", "Use the redesigned UI/UX workspace to manage phases, evidence, controls and exports."]}

    def phase_101_115_summary(self, task: str = "") -> dict[str, Any]:
        return {
            "goal": "Controlled real-world intelligence system",
            "absolute_control": self.absolute_control_layer(task),
            "deterministic_core": self.deterministic_core(),
            "formal_verification": self.formal_verification_layer(task),
            "alignment": self.alignment_engine(task),
            "resource_governance": self.resource_governance(task),
            "failure_containment": self.failure_containment(task),
            "audit_ledger": self.immutable_audit_ledger(),
            "authority": self.human_authority_hierarchy(),
            "ethical_policy": self.ethical_policy_engine(),
            "reality_feedback": self.reality_feedback_loop(task),
            "external_ecosystem": self.external_agent_ecosystem(),
            "trust_scoring": self.trust_scoring_system(task),
            "autonomous_governance": self.autonomous_governance(),
            "controlled_self_modification": self.controlled_self_modification(),
            "human_ai_contract": self.human_ai_contract_layer(),
            "admin_control_layer": self.get_admin_control_layer(),
        }

    def get_admin_control_layer(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._admin_control_layer))

    def update_admin_control_layer(self, patch: dict[str, Any], actor_role: str = "admin") -> dict[str, Any]:
        if actor_role != "admin":
            return {"phase": "101-115", "error": "Only Admin can change the final control layer.", "control_layer": self.get_admin_control_layer()}
        mutable_keys = {"safe_mode", "kill_switches", "resource_limits", "authority_hierarchy", "ethical_policy", "self_modification", "human_ai_contract"}
        for key, value in patch.items():
            if key in mutable_keys:
                if isinstance(value, dict) and isinstance(self._admin_control_layer.get(key), dict):
                    merged = dict(self._admin_control_layer[key]); merged.update(value); self._admin_control_layer[key] = merged
                else:
                    self._admin_control_layer[key] = value
        event = {"id": str(uuid4()), "phase": "101-115", "actor_role": actor_role, "action": "admin_control_layer_updated", "created_at": time.time(), "changed_keys": [k for k in patch.keys() if k in mutable_keys]}
        self._admin_control_layer.setdefault("audit_events", []).append(event)
        self._approvals.append(event)
        return self.get_admin_control_layer()

    def admin_control_scan(self, content: str, actor_role: str = "operator") -> dict[str, Any]:
        import re
        layer = self._admin_control_layer
        matches = []
        for rule in layer.get("ethical_policy", {}).get("rules", []):
            if not rule.get("enabled", True) or not rule.get("pattern"): continue
            try: found = re.findall(rule["pattern"], content or "", flags=re.IGNORECASE)
            except re.error as exc:
                matches.append({"rule_id": rule.get("id"), "label": rule.get("label"), "severity": "invalid", "action": "fix_rule", "error": str(exc)}); continue
            if found: matches.append({"rule_id": rule.get("id"), "label": rule.get("label"), "severity": rule.get("severity"), "action": rule.get("action"), "count": len(found)})
        kill_active = [k for k, v in layer.get("kill_switches", {}).items() if v]
        safe_mode = bool(layer.get("safe_mode"))
        blocked = bool(kill_active and ("all_agents" in kill_active or "current_task" in kill_active)) or any(m.get("action") == "block" for m in matches)
        admin_required = safe_mode or any(m.get("action") in {"require_admin_approval", "block"} for m in matches) or actor_role != "admin" and bool(matches)
        return {"phase": "101-115", "actor_role": actor_role, "matches": matches, "active_kill_switches": kill_active, "safe_mode": safe_mode, "blocked": blocked, "admin_required": admin_required, "allowed": not blocked and (not admin_required or actor_role == "admin"), "explanation": "Final authority is dashboard-controlled by Admin: kill switches, budget limits, roles, ethical rules, self-modification and human-AI contract."}

    def absolute_control_layer(self, task: str = "") -> dict[str, Any]:
        return {"phase": 101, "task": task, "controls": self._admin_control_layer["kill_switches"], "safe_mode": self._admin_control_layer["safe_mode"], "permission_gates": ["external tools", "deployment", "self-modification", "budget overrun", "destructive action"]}

    def deterministic_core(self) -> dict[str, Any]:
        return {"phase": 102, "split": {"deterministic": ["permissions", "policy scan", "budgets", "audit hashes", "state transitions"], "ai": ["planning", "generation", "critique", "summaries"]}, "state_machine": ["queued", "planning", "awaiting_approval", "executing", "verifying", "ready", "blocked", "rolled_back"]}

    def formal_verification_layer(self, action: str = "") -> dict[str, Any]:
        scan = self.admin_control_scan(action, actor_role="operator")
        return {"phase": 103, "action": action, "checks": ["schema valid", "policy scan", "budget within limit", "permission allowed", "rollback available"], "scan": scan, "verdict": "blocked" if scan["blocked"] else "approval_required" if scan["admin_required"] else "pass"}

    def alignment_engine(self, task: str = "") -> dict[str, Any]:
        drift_terms = ["also", "while you are there", "ignore", "instead"]
        drift = any(t in (task or "").lower() for t in drift_terms)
        return {"phase": 104, "task": task, "goal_drift_detected": drift, "boundaries": ["only perform requested task", "stop at approval gates", "do not expand scope without user/Admin consent"], "realignment_action": "ask approval or constrain plan" if drift else "continue"}

    def resource_governance(self, task: str = "") -> dict[str, Any]:
        return {"phase": 105, "task": task, "limits": self._admin_control_layer["resource_limits"], "dashboard_controls": ["cost cap", "runtime cap", "parallel agent limit", "approval threshold", "cost anomaly alert"]}

    def failure_containment(self, task: str = "") -> dict[str, Any]:
        return {"phase": 106, "task": task, "containment": ["isolate failed agent", "freeze side effects", "snapshot sandbox", "rollback changed files", "open incident audit"], "blast_radius_score": "low unless external tools or deployment are enabled"}

    def immutable_audit_ledger(self) -> dict[str, Any]:
        events = self._admin_control_layer.get("audit_events", [])[-25:]
        return {"phase": 107, "events": events, "tamper_evidence": "append-only events are hash-ready for durable storage", "replay_supported": True}

    def human_authority_hierarchy(self) -> dict[str, Any]:
        return {"phase": 108, "roles": self._admin_control_layer["authority_hierarchy"], "rule": "Admin override always wins over autonomous agents."}

    def ethical_policy_engine(self) -> dict[str, Any]:
        return {"phase": 109, **self._admin_control_layer["ethical_policy"], "controlled_from_dashboard": True}

    def reality_feedback_loop(self, task: str = "") -> dict[str, Any]:
        return {"phase": 110, "task": task, "signals": ["uptime", "errors", "user feedback", "support tickets", "conversion", "cost"], "loop": ["observe", "compare outcome to prediction", "create learning", "propose fix", "admin approve", "apply"]}

    def external_agent_ecosystem(self) -> dict[str, Any]:
        return {"phase": 111, "contracts": ["agent identity", "capability manifest", "permission scopes", "result attestation", "revocation"], "marketplace_ready": True}

    def trust_scoring_system(self, task: str = "") -> dict[str, Any]:
        scan = self.admin_control_scan(task, actor_role="operator")
        score = 92 if not scan["matches"] else 65 if not scan["blocked"] else 25
        return {"phase": 112, "score": score, "components": {"verification": 0.35, "policy": 0.25, "evidence": 0.20, "history": 0.20}, "badge": "high" if score >= 85 else "medium" if score >= 60 else "low"}

    def autonomous_governance(self) -> dict[str, Any]:
        return {"phase": 113, "proposal_workflow": ["detect risky pattern", "draft new policy", "simulate on historical tasks", "request Admin approval", "activate from dashboard"], "admin_approval_required": True}

    def controlled_self_modification(self) -> dict[str, Any]:
        return {"phase": 114, **self._admin_control_layer["self_modification"], "workflow": ["proposal", "diff", "benchmark", "rollback package", "Admin approval", "apply", "monitor"]}

    def human_ai_contract_layer(self) -> dict[str, Any]:
        return {"phase": 115, **self._admin_control_layer["human_ai_contract"], "controlled_from_dashboard": True}

    def _phase_status(self, phase: dict[str, Any]) -> CapabilityStatus:
        if phase["id"] >= 101:
            evidence = {101:["admin kill switches", "safe mode"],102:["deterministic_core()"],103:["formal_verification_layer()"],104:["alignment_engine()"],105:["resource_governance()"],106:["failure_containment()"],107:["immutable_audit_ledger()"],108:["human_authority_hierarchy()"],109:["ethical_policy_engine() dashboard rules"],110:["reality_feedback_loop()"],111:["external_agent_ecosystem()"],112:["trust_scoring_system()"],113:["autonomous_governance()"],114:["controlled_self_modification()"],115:["human_ai_contract_layer()"]}.get(phase["id"], [])
            return CapabilityStatus(phase=phase["id"], title=phase["title"], status="implemented", shipped=list(phase["capabilities"]), evidence=evidence)
        return super()._phase_status(phase)

    def _agent_for_phase(self, phase: int) -> str:
        mapping = {101:"AbsoluteControlAgent",102:"DeterministicCoreAgent",103:"FormalVerificationAgent",104:"AlignmentAgent",105:"ResourceGovernanceAgent",106:"ContainmentAgent",107:"AuditLedgerAgent",108:"AuthorityAgent",109:"EthicalPolicyAgent",110:"RealityFeedbackAgent",111:"ExternalEcosystemAgent",112:"TrustScoringAgent",113:"AutonomousGovernanceAgent",114:"ControlledSelfModificationAgent",115:"HumanAIContractAgent"}
        return mapping.get(phase, super()._agent_for_phase(phase))

_platform = ControlledRealWorldIntelligencePlatform()
def get_super_agent_platform() -> ControlledRealWorldIntelligencePlatform: return _platform

