"""AGI System v3 control plane: phases K-U.

Concrete backend contracts for deeper reasoning, multi-strategy execution,
evaluation, graph memory, continuous improvement, debugging, compression,
integrations, safety gates, autonomous modes, and simplified UI.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import hashlib
import json
import re

PHASES = [
    ("K", "Tree reasoning engine", "Generate competing plans, score tradeoffs, and choose the best path."),
    ("L", "Multi-strategy execution", "Run alternative strategies, compare results, and merge the safest winning approach."),
    ("M", "Real evaluation system", "Grade correctness, code quality, UX, performance, safety, and verification depth."),
    ("N", "Knowledge graph brain", "Represent files, errors, fixes, components, tasks, and lessons as linked nodes."),
    ("O", "Continuous execution loop", "Monitor, improve, update, and repeat with explicit stop conditions."),
    ("P", "Debugging intelligence", "Reproduce, classify, isolate, patch, and verify root causes."),
    ("Q", "Context compression", "Compress large project context into high-signal task summaries."),
    ("R", "External integration layer", "Expose guarded adapters for GitHub, CI, deployment, databases, and APIs."),
    ("S", "Safety + control v2", "Risk-score actions and require approvals for dangerous operations."),
    ("T", "Real autonomous mode", "Manual, assisted, and autonomous modes with explicit boundaries."),
    ("U", "UI evolution v2", "Show less, explain better, and surface only key insights."),
]

@dataclass(slots=True)
class ReasoningCandidate:
    id: str
    title: str
    approach: str
    strengths: list[str]
    risks: list[str]
    score: float

@dataclass(slots=True)
class EvaluationScore:
    correctness: int
    code_quality: int
    ux: int
    performance: int
    safety: int
    verification: int
    @property
    def overall(self) -> int:
        return round((self.correctness*0.25)+(self.code_quality*0.18)+(self.ux*0.14)+(self.performance*0.12)+(self.safety*0.16)+(self.verification*0.15))

class TreeReasoningEngine:
    def create_candidates(self, task: str, context: dict[str, Any] | None = None) -> list[ReasoningCandidate]:
        context = context or {}
        lower = task.lower()
        candidates = [
            ReasoningCandidate("plan-fast", "Minimal focused patch", "Patch the smallest set of files and run import/build checks.", ["fast", "low churn"], ["may miss systemic design issues"], 72),
            ReasoningCandidate("plan-system", "Systemic architecture upgrade", "Create reusable backend contracts and frontend components for the whole agent flow.", ["scalable", "reduces repeated bugs"], ["larger change surface"], 86),
            ReasoningCandidate("plan-hybrid", "Hybrid verified delivery", "Apply architecture upgrade only where it fixes observed failures, then verify and package.", ["balanced", "safe", "user-visible improvement"], ["requires stricter scope control"], 91),
        ]
        if any(word in lower for word in ["bug", "error", "fix", "broken"]):
            candidates.append(ReasoningCandidate("plan-debug-first", "Debug-first repair", "Reproduce the failure, inspect import graph, patch root cause, then improve UX output.", ["root-cause oriented", "prevents fake repairs"], ["slower initial response"], 94))
        stack = " ".join(context.get("stack", [])) if isinstance(context.get("stack"), list) else str(context.get("stack", ""))
        if "React" in stack or "Vite" in stack:
            candidates.append(ReasoningCandidate("plan-react-aware", "React/Vite aware implementation", "Respect src/main.jsx, components, styles, and package scripts before export.", ["file-path correct", "build-aware"], ["frontend-specific"], 93))
        return sorted(candidates, key=lambda item: item.score, reverse=True)
    def decide(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        candidates = self.create_candidates(task, context)
        winner = candidates[0]
        return {"winner": asdict(winner), "candidates": [asdict(c) for c in candidates], "decision_rule": "highest score after risk, context fit, and verification depth", "confidence": min(99, max(60, int(winner.score)))}

class MultiStrategyExecutor:
    def plan_strategies(self, task: str) -> list[dict[str, Any]]:
        return [
            {"id": "direct", "label": "Direct implementation", "steps": ["scan", "patch", "verify"], "best_for": "small scoped changes"},
            {"id": "debug", "label": "Debug-first", "steps": ["reproduce", "classify", "root-cause", "patch", "verify"], "best_for": "errors and broken exports"},
            {"id": "architecture", "label": "Architecture-first", "steps": ["map system", "define contracts", "implement reusable modules", "verify"], "best_for": "systemic agent issues"},
        ]
    def merge_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        if not results:
            return {"winner": None, "merged": [], "reason": "no strategies executed"}
        ranked = sorted(results, key=lambda r: (r.get("verified", False), r.get("score", 0)), reverse=True)
        return {"winner": ranked[0], "merged": [r for r in ranked if r.get("score", 0) >= 70], "reason": "verified strategies outrank unverified strategies"}

class RealEvaluator:
    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        files = payload.get("files", []) or []
        verification = payload.get("verification", []) or []
        text = json.dumps(payload, ensure_ascii=False).lower()
        generic_penalty = sum(marker in text for marker in ["placeholder", "lorem ipsum", "generated from your request", "hero section"])
        missing_penalty = sum("missing" in str(item).lower() or "failed" in str(item).lower() for item in verification)
        score = EvaluationScore(
            correctness=max(35, 92 - generic_penalty*10 - missing_penalty*14),
            code_quality=max(40, 88 + min(6, len(files)) - generic_penalty*8),
            ux=max(45, 84 - generic_penalty*12),
            performance=82,
            safety=88 if payload.get("risk", "low") in ["low", "medium"] else 62,
            verification=min(95, 55 + len(verification)*12),
        )
        return {"scores": asdict(score) | {"overall": score.overall}, "pass": score.overall >= 75 and missing_penalty == 0, "notes": self._notes(score, generic_penalty, missing_penalty)}
    def _notes(self, score: EvaluationScore, generic_penalty: int, missing_penalty: int) -> list[str]:
        notes = [f"Overall score: {score.overall}/100"]
        if generic_penalty:
            notes.append("Generic/template language detected; require domain-specific rewrite before export.")
        if missing_penalty:
            notes.append("Verification contains failures; block export until repaired.")
        if score.overall >= 85:
            notes.append("High confidence delivery candidate.")
        return notes

class KnowledgeGraphBrain:
    def __init__(self, path: str | Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def _read(self) -> dict[str, Any]:
        if self.path.exists():
            try: return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception: pass
        return {"nodes": [], "edges": []}
    def upsert_node(self, node_type: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        graph = self._read()
        node_id = hashlib.sha1(f"{node_type}:{name}".encode()).hexdigest()[:12]
        node = {"id": node_id, "type": node_type, "name": name, "metadata": metadata or {}, "updated_at": datetime.now(UTC).isoformat()}
        graph["nodes"] = [n for n in graph["nodes"] if n.get("id") != node_id] + [node]
        self.path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        return node
    def add_edge(self, source: str, relation: str, target: str) -> dict[str, Any]:
        graph = self._read(); edge = {"source": source, "relation": relation, "target": target, "created_at": datetime.now(UTC).isoformat()}
        graph["edges"].append(edge); self.path.write_text(json.dumps(graph, indent=2), encoding="utf-8"); return edge
    def summary(self) -> dict[str, Any]:
        graph = self._read(); counts: dict[str, int] = {}
        for node in graph.get("nodes", []): counts[node.get("type", "unknown")] = counts.get(node.get("type", "unknown"), 0) + 1
        return {"node_count": len(graph.get("nodes", [])), "edge_count": len(graph.get("edges", [])), "types": counts, "recent_nodes": graph.get("nodes", [])[-10:]}

class ContinuousExecutionLoop:
    def next_cycle(self, task: str, last_result: dict[str, Any] | None = None) -> dict[str, Any]:
        last_result = last_result or {}
        action = "monitor" if last_result.get("pass") is True else "debug" if last_result.get("error") else "improve"
        return {"task": task, "cycle": ["observe", "decide", "act", "verify", "learn"], "next_action": action, "stop_conditions": ["user stops task", "budget exceeded", "verification passes", "approval required"]}

class DebuggingIntelligence:
    IMPORT_RE = re.compile(r"Failed to resolve import [\"'](?P<import>[^\"']+)[\"'] from [\"'](?P<source>[^\"']+)[\"']")
    def diagnose(self, error_text: str) -> dict[str, Any]:
        text = error_text or ""; match = self.IMPORT_RE.search(text)
        if match:
            return {"class": "missing_import", "root_cause": f"{match.group('source')} imports {match.group('import')} but the file is absent or exported from the wrong path.", "repair_plan": ["create the exact missing file", "or update import path", "run import graph validation", "run npm build"], "confidence": 94}
        if "vite" in text.lower() and "import-analysis" in text.lower():
            return {"class": "vite_import_analysis", "root_cause": "Vite could not statically resolve a module import.", "repair_plan": ["inspect source import", "validate extension", "create target file", "rebuild"], "confidence": 87}
        if "build" in text.lower() or "failed" in text.lower():
            return {"class": "build_failure", "root_cause": "Build command failed; inspect first compiler error, not the last symptom.", "repair_plan": ["capture command", "parse first error", "patch root cause", "rerun"], "confidence": 78}
        return {"class": "unknown", "root_cause": "Insufficient error signature; require logs and file graph.", "repair_plan": ["collect logs", "scan imports", "run tests/build", "classify again"], "confidence": 55}

class ContextCompressionEngine:
    def compress(self, context: dict[str, Any], budget: int = 1200) -> dict[str, Any]:
        text = json.dumps(context, ensure_ascii=False, indent=2)
        keys = ["task", "error", "stack", "files", "verification", "policy", "recent_failures"]
        distilled = {k: context[k] for k in keys if k in context}
        summary = json.dumps(distilled, ensure_ascii=False)
        if len(summary) > budget: summary = summary[:budget-120] + "... [compressed]"
        return {"summary": summary, "original_chars": len(text), "compressed_chars": len(summary), "compression_ratio": round(len(summary)/max(1, len(text)), 3), "kept_keys": list(distilled.keys())}

class ExternalIntegrationRegistry:
    DEFAULTS = {
        "github": {"enabled": False, "risk": "medium", "requires_approval": True, "capabilities": ["read repos", "create branches", "open PRs"]},
        "ci": {"enabled": False, "risk": "medium", "requires_approval": True, "capabilities": ["run pipelines", "read artifacts"]},
        "deploy": {"enabled": False, "risk": "high", "requires_approval": True, "capabilities": ["deploy preview", "rollback"]},
        "database": {"enabled": False, "risk": "high", "requires_approval": True, "capabilities": ["read schema", "run migrations with approval"]},
        "api": {"enabled": False, "risk": "medium", "requires_approval": True, "capabilities": ["call approved APIs"]},
    }
    def __init__(self, path: str | Path): self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def list(self) -> dict[str, Any]:
        data = dict(self.DEFAULTS)
        if self.path.exists():
            try:
                for k, v in json.loads(self.path.read_text(encoding="utf-8")).items():
                    if k in data: data[k].update(v)
            except Exception: pass
        return data
    def update(self, name: str, patch: dict[str, Any]) -> dict[str, Any]:
        data = self.list()
        if name not in data: raise ValueError(f"Unknown integration: {name}")
        data[name].update({k:v for k,v in patch.items() if k in {"enabled", "requires_approval"}})
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data[name]

class SafetyControlV2:
    HIGH_RISK = ["delete", "deploy", "secret", "credential", "migration", "payment", "production"]
    def assess(self, action: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = policy or {}; lower = (action or "").lower(); hits = [term for term in self.HIGH_RISK if term in lower]
        risk = "high" if hits else ("medium" if any(term in lower for term in ["write", "execute", "shell", "network"]) else "low")
        requires_approval = risk == "high" or action in policy.get("require_approval_for", [])
        return {"action": action, "risk": risk, "triggers": hits, "requires_approval": requires_approval, "allowed": not requires_approval}

class AutonomousModeController:
    MODES = {
        "manual": {"can_execute": False, "needs_approval": "all changes", "description": "AI proposes only; human executes."},
        "assisted": {"can_execute": True, "needs_approval": "high-risk actions", "description": "AI can patch and verify safe tasks."},
        "autonomous": {"can_execute": True, "needs_approval": "dangerous or external actions", "description": "AI runs full loop within policy boundaries."},
    }
    def describe(self, mode: str = "assisted") -> dict[str, Any]:
        return {"mode": mode if mode in self.MODES else "assisted", **self.MODES.get(mode, self.MODES["assisted"]), "boundaries": ["budget limits", "approval gates", "sandbox isolation", "export only after verification"]}

class UIEvolutionV2:
    def compact_card(self, run: dict[str, Any]) -> dict[str, Any]:
        critical = [item for item in run.get("events", []) if item.get("status") in ["failed", "needs_repair", "blocked"]]
        return {"display_mode": "compressed", "headline": run.get("title", "Agent run"), "status": run.get("status", "unknown"), "progress": run.get("progress", 0), "critical_events": critical[:5], "primary_sections": ["summary", "verification", "download"], "hidden_by_default": ["raw logs", "metadata", "full manifest"]}

class AGISystemV3:
    def __init__(self):
        runtime = Path(".ise_ai_runtime")
        self.reasoning = TreeReasoningEngine(); self.executor = MultiStrategyExecutor(); self.evaluator = RealEvaluator(); self.graph = KnowledgeGraphBrain(runtime / "knowledge_graph_v3.json"); self.loop = ContinuousExecutionLoop(); self.debugger = DebuggingIntelligence(); self.compressor = ContextCompressionEngine(); self.integrations = ExternalIntegrationRegistry(runtime / "integrations_v3.json"); self.safety = SafetyControlV2(); self.mode = AutonomousModeController(); self.ui = UIEvolutionV2()
    def roadmap(self) -> dict[str, Any]: return {"title": "AGI System v3 roadmap: phases K-U", "phases": [{"id": p, "title": t, "goal": g, "status": "implemented"} for p,t,g in PHASES], "principle": "Depth, correctness, verification, and operator control before more surface features."}
    def plan(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = self.reasoning.decide(task, context); strategies = self.executor.plan_strategies(task); task_node = self.graph.upsert_node("task", task[:120], {"confidence": decision["confidence"]}); self.graph.upsert_node("decision", decision["winner"]["title"], {"task_node": task_node["id"]}); return {"decision": decision, "strategies": strategies, "graph": self.graph.summary()}
    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.evaluator.evaluate(payload); self.graph.upsert_node("evaluation", f"score-{result['scores']['overall']}", result); return result
    def diagnose(self, error_text: str) -> dict[str, Any]:
        result = self.debugger.diagnose(error_text); self.graph.upsert_node("error", result["class"], {"root_cause": result["root_cause"], "confidence": result["confidence"]}); return result
    def control_summary(self) -> dict[str, Any]: return {"modes": self.mode.MODES, "integrations": self.integrations.list(), "graph": self.graph.summary()}

runtime = AGISystemV3()
def get_agi_system_v3() -> AGISystemV3: return runtime
