from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any


@dataclass(slots=True)
class DynamicOutputPlan:
    task: str
    route: str
    title: str
    summary: str
    confidence: float
    specialist_agents: list[str]
    output_components: list[str]
    execution_steps: list[dict[str, Any]]
    render_blocks: list[dict[str, Any]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_KEYWORDS = {
    "data": ("data", "csv", "json", "table", "metrics", "analytics", "report"),
    "image": ("image", "photo", "screenshot", "picture", "gallery", "vision", "uploaded"),
    "debug": ("error", "traceback", "failed", "bug", "debug", "exception", "blocked gate"),
    "design": ("figma", "design", "prototype", "similar to", "website", "landing", "clone"),
    "file": ("file", "download", "pdf", "docx", "txt", "html", "jsx", "zip"),
    "project": ("app", "project", "frontend", "backend", "component", "api", "full stack"),
}


def _words(text: str, limit: int = 10) -> list[str]:
    stop = {"create", "make", "build", "implement", "update", "rewrite", "with", "from", "into", "that", "this", "please", "agent", "agi"}
    out: list[str] = []
    for item in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text or ""):
        token = item.lower()
        if token in stop or token in out:
            continue
        out.append(token)
        if len(out) >= limit:
            break
    return out or ["task", "workspace", "result"]


def _pick_route(task: str) -> str:
    lower = (task or "").lower()
    scores = {name: sum(1 for word in words if word in lower) for name, words in _KEYWORDS.items()}
    route, score = max(scores.items(), key=lambda pair: pair[1])
    if score == 0:
        return "chat"
    if route in {"file", "project"} and any(x in lower for x in ("preview", "browser", "render")):
        return "preview"
    return route


def _agents_for_route(route: str) -> list[str]:
    return {
        "data": ["DataAgent", "ChartAgent", "VerifierAgent"],
        "image": ["VisionAgent", "ImageRenderAgent", "SourceVerifierAgent"],
        "debug": ["DebuggingAgent", "PatchAgent", "VerifierAgent", "RetryAgent"],
        "design": ["DesigningAgent", "FigmaAgent", "FrontendAgent", "PreviewAgent"],
        "file": ["FileAgent", "ArtifactAgent", "VerifierAgent"],
        "project": ["PlannerAgent", "FrontendAgent", "BackendAgent", "VerifierAgent", "ExportAgent"],
        "preview": ["StaticPreviewAgent", "PreviewAgent", "ArtifactAgent"],
        "chat": ["ChatAgent", "MemoryAgent"],
    }.get(route, ["Agent"])


def _components_for_route(route: str) -> list[str]:
    return {
        "data": ["visual_data_table", "visual_metric_grid", "visual_json_viewer"],
        "image": ["visual_image_gallery", "visual_json_viewer"],
        "debug": ["visual_repair_loop", "smart_error_explainer", "interactive_terminal"],
        "design": ["figma_design_brief", "figma_prototype_preview", "visual_file_gallery"],
        "file": ["download_card", "file_preview", "visual_file_gallery"],
        "project": ["thinking_trace", "agent_loop_visualizer", "file_explorer", "visual_file_gallery"],
        "preview": ["figma_prototype_preview", "download_card", "visual_file_gallery"],
        "chat": ["report"],
    }.get(route, ["report"])


def build_dynamic_output_plan(task: str, artifacts: list[dict] | None = None, images: list[dict] | None = None, data: list[dict] | None = None) -> dict[str, Any]:
    artifacts = artifacts or []
    images = images or []
    data = data or []
    route = _pick_route(task)
    tokens = _words(task)
    digest = hashlib.sha256((task or route).encode("utf-8")).hexdigest()[:8]
    title = f"Dynamic {route.title()} Workspace"
    agents = _agents_for_route(route)
    components = _components_for_route(route)
    steps = [
        {"id": "understand", "agent": agents[0], "title": f"Understand {', '.join(tokens[:3])}", "status": "ready"},
        {"id": "plan", "agent": agents[min(1, len(agents)-1)], "title": "Create task-specific execution plan", "status": "ready"},
        {"id": "execute", "agent": agents[min(2, len(agents)-1)], "title": "Execute with verification evidence", "status": "ready"},
        {"id": "repair", "agent": "DebuggingAgent", "title": "Analyze, patch, and retry if any error occurs", "status": "armed"},
        {"id": "render", "agent": "VisualRenderAgent", "title": "Render best-fit UI result blocks", "status": "ready"},
    ]
    blocks: list[dict[str, Any]] = [
        {"type": "visual_data_table", "payload": {"title": "Dynamic routing contract", "columns": ["field", "value"], "rows": [
            {"field": "route", "value": route},
            {"field": "agents", "value": " → ".join(agents)},
            {"field": "components", "value": ", ".join(components)},
            {"field": "task_fingerprint", "value": digest},
        ]}},
        {"type": "agent_loop_visualizer", "payload": {"title": "Self-healing task loop", "retry_count": 0, "phases": [
            {"id": "plan", "label": "Plan", "status": "ready"},
            {"id": "execute", "label": "Execute", "status": "ready"},
            {"id": "verify", "label": "Verify", "status": "ready"},
            {"id": "repair", "label": "Repair", "status": "armed"},
            {"id": "render", "label": "Render", "status": "ready"},
        ]}},
    ]
    if data or route == "data":
        rows = data or [{"metric": token.title(), "value": len(token) * 7, "status": "derived"} for token in tokens[:5]]
        blocks.append({"type": "visual_data_table", "payload": {"title": "Task data preview", "columns": list(rows[0].keys()) if rows else [], "rows": rows}})
    if images or route == "image":
        blocks.append({"type": "visual_image_gallery", "payload": {"title": "Image workspace", "images": images, "empty_state": "Upload images or provide image URLs to render them here."}})
    if artifacts or route in {"file", "project", "preview", "design"}:
        files = artifacts or [{"path": f"{tokens[0]}-result.{ 'html' if route in {'preview','design'} else 'txt'}", "kind": route, "summary": "Task-specific artifact slot prepared by the Agent."}]
        blocks.append({"type": "visual_file_gallery", "payload": {"title": "Result files", "files": files}})
    if route == "debug":
        blocks.append({"type": "visual_repair_loop", "payload": {"title": "DebuggingAgent repair plan", "policy": "think → analyze → patch → rerun → verify", "error": task[:4000], "attempts": [
            {"step": 1, "action": "Classify root cause from stderr/traceback", "status": "ready"},
            {"step": 2, "action": "Patch the smallest responsible file set", "status": "ready"},
            {"step": 3, "action": "Rerun verifier and continue until clean", "status": "ready"},
        ]}})
    plan = DynamicOutputPlan(
        task=task,
        route=route,
        title=title,
        summary=f"Selected {route} flow with {len(agents)} specialist agents and {len(components)} visual component types.",
        confidence=0.78 if route == "chat" else 0.92,
        specialist_agents=agents,
        output_components=components,
        execution_steps=steps,
        render_blocks=blocks,
        generated_at=datetime.now(UTC).isoformat(),
    )
    return plan.to_dict()
