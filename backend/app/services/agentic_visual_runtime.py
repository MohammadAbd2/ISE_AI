from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "AGI_Output" / ".state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

VISUAL_COMPONENTS = [
    {"id": "data-table", "title": "Data table", "best_for": "CSV, JSON arrays, API payloads, logs, records", "block_type": "visual_data_table"},
    {"id": "metric-grid", "title": "Metric grid", "best_for": "Counts, test results, costs, benchmark summaries", "block_type": "visual_metric_grid"},
    {"id": "image-gallery", "title": "Image gallery", "best_for": "Internet images, uploaded images, generated image sets", "block_type": "visual_image_gallery"},
    {"id": "file-gallery", "title": "File gallery", "best_for": "Generated project files with preview/download actions", "block_type": "visual_file_gallery"},
    {"id": "website-brief", "title": "Website design brief", "best_for": "A URL the DesignAgent inspected and translated into a new project", "block_type": "visual_design_brief"},
    {"id": "repair-loop", "title": "Repair loop", "best_for": "Errors, build failures, tests, import graph issues", "block_type": "visual_repair_loop"},
    {"id": "agent-panel", "title": "Agent command panel", "best_for": "Planning, execution, preview, export, memory, safety controls", "block_type": "agent_panel"},
]

ROADMAP = {
    "title": "Agentic AGI Visual Component + Maximum Agent Roadmap",
    "status": "implementation_started",
    "north_star": "Every Agent answer should render the best visual surface for the task: data, images, files, diagrams, website design briefs, debugging loops, previews, downloads, and self-repair evidence directly inside chat.",
    "phases": [
        {"id": "V1", "name": "Visual output contract", "goal": "Normalize Agent outputs into render blocks, not plain text blobs."},
        {"id": "V2", "name": "Universal data components", "goal": "Render tables, metrics, JSON, CSV, logs, and charts from one contract."},
        {"id": "V3", "name": "Universal image components", "goal": "Render uploaded, internet, and generated images with captions, source, analysis, and download."},
        {"id": "V4", "name": "Project/file gallery", "goal": "Show generated project files in chat with preview, copy, download, and open-preview actions."},
        {"id": "V5", "name": "Dedicated Agent panel", "goal": "Add one panel for roadmap, active run, debug loop, design agent, visual components, memory, safety, preview, and exports."},
        {"id": "V6", "name": "Debugging Agent v2", "goal": "When execution fails, classify error, plan fix, patch, rerun, verify, and continue instead of stopping."},
        {"id": "V7", "name": "Designing Agent", "goal": "Inspect URL or screenshot, understand layout/content/style, produce implementation plan, then generate a similar project."},
        {"id": "V8", "name": "Chat tab project rendering", "goal": "Generated website/app results appear in chat just like Agent tab: preview, file tree, download, run evidence."},
        {"id": "V9", "name": "Visual router", "goal": "Automatically choose image gallery, data table, file gallery, diagram, repair loop, or design brief per task."},
        {"id": "V10", "name": "Maximum Agent ability pass", "goal": "Wire planning, design, debug, execution, visual rendering, artifact export, memory, and safety into one Agent pipeline."},
    ],
    "quality_gates": [
        "No task returns a generic preview when a specific file/image/data output was requested.",
        "Every failure produces a repair loop block with next action and retry evidence.",
        "Every generated project includes preview metadata, file gallery, download artifact, and verification state.",
        "Every URL-design task produces a design brief before code generation.",
        "Every image result includes renderable URLs or uploaded previews and optional analysis.",
    ],
}


def _host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or parsed.path.split("/")[0] or "website"


def visual_capabilities() -> dict:
    return {"components": VISUAL_COMPONENTS, "router_rules": [
        {"match": ["json", "csv", "data", "table", "metrics"], "block": "visual_data_table"},
        {"match": ["image", "photo", "screenshot", "uploaded", "internet image"], "block": "visual_image_gallery"},
        {"match": ["file", "project", "component", "download", "preview"], "block": "visual_file_gallery"},
        {"match": ["error", "traceback", "failed", "blocked gate"], "block": "visual_repair_loop"},
        {"match": ["website", "similar to", "clone", "url", "landing page"], "block": "visual_design_brief"},
    ]}


def roadmap() -> dict:
    return ROADMAP


def render_contract_for_task(task: str, *, artifacts: list[dict] | None = None, images: list[dict] | None = None, data: list[dict] | None = None) -> dict:
    lower = (task or "").lower()
    blocks: list[dict] = []
    if data or any(word in lower for word in ("data", "table", "json", "csv", "metrics")):
        rows = data or [{"name": "Example", "status": "ready", "value": 1}]
        blocks.append({"type": "visual_data_table", "payload": {"title": "Structured data", "rows": rows, "columns": list(rows[0].keys()) if rows else []}})
    if images or any(word in lower for word in ("image", "photo", "screenshot", "picture")):
        blocks.append({"type": "visual_image_gallery", "payload": {"title": "Images", "images": images or []}})
    if artifacts or any(word in lower for word in ("file", "project", "website", "component", "download", "preview")):
        blocks.append({"type": "visual_file_gallery", "payload": {"title": "Generated files", "files": artifacts or []}})
    if any(word in lower for word in ("error", "failed", "traceback", "blocked gate", "import_graph")):
        blocks.append(debug_repair_plan(task, context="visual-router")["render_block"])
    return {"task": task, "blocks": blocks, "component_count": len(blocks)}


def design_from_url(url: str, prompt: str = "Create a similar website") -> dict:
    host = _host_from_url(url)
    palette_seed = hashlib.sha256(host.encode()).hexdigest()[:6]
    brief = {
        "source_url": url,
        "site_name": host,
        "intent": prompt,
        "observations": [
            "Inspect visible hero, navigation, call-to-action hierarchy, content sections, media treatment, spacing, and responsive behavior.",
            "Extract reusable design tokens: typography scale, color contrast, component rhythm, card density, and interaction patterns.",
            "Recreate a similar experience without copying proprietary assets, text, logos, or exact trade dress.",
        ],
        "design_tokens": {
            "primary": f"#{palette_seed}",
            "radius": "20px",
            "layout": "responsive hero + card sections + sticky navigation",
            "motion": "subtle reveal, hover lift, scroll-safe transitions",
        },
        "implementation_plan": [
            "Create visual design brief from URL analysis.",
            "Generate React/Vite project with reusable sections: Nav, Hero, FeatureGrid, SocialProof, CTA, Footer.",
            "Run import/build verification.",
            "If errors occur, DebuggingAgent classifies, repairs, and reruns verification.",
            "Return chat-rendered preview, file gallery, and downloadable project export.",
        ],
        "safety_note": "Build an original, similar-quality layout. Do not copy copyrighted text, logos, or private assets from the source website.",
    }
    files = [
        {"path": "frontend/src/App.jsx", "kind": "react", "summary": "Generated original website shell inspired by analyzed structure."},
        {"path": "frontend/src/styles/app.css", "kind": "css", "summary": "Design tokens, responsive layout, and polished visual states."},
        {"path": "docs/DESIGN_BRIEF.md", "kind": "markdown", "summary": "Agent-visible design brief and implementation plan."},
    ]
    return {
        "agent": "DesigningAgent",
        "status": "planned",
        "brief": brief,
        "files": files,
        "render_blocks": [
            {"type": "visual_design_brief", "payload": brief},
            {"type": "visual_file_gallery", "payload": {"title": "Planned generated project", "files": files}},
        ],
    }


def debug_repair_plan(error_text: str, context: str = "") -> dict:
    text = (error_text or "").lower()
    if "import" in text or "module not found" in text or "import_graph" in text:
        root = "Import graph failure"
        strategy = ["Locate unresolved import", "Check file path and extension", "Create missing file or rewrite import", "Run build/import scan again"]
    elif "template" in text or "no_template" in text:
        root = "Template marker or placeholder content detected"
        strategy = ["Find banned placeholder markers", "Replace with task-specific content", "Run no-template verifier", "Continue export if clean"]
    elif "eaddrinuse" in text or "address already" in text or "517" in text:
        root = "Preview port conflict"
        strategy = ["Find next free port", "Restart preview process", "Update preview URL contract", "Verify HTTP reachability"]
    elif "syntax" in text or "unexpected token" in text:
        root = "Syntax/compile error"
        strategy = ["Parse failing file and line", "Patch syntax safely", "Run formatter/build", "Reopen verification loop"]
    else:
        root = "Unknown execution failure"
        strategy = ["Classify stderr/stdout", "Map failure to responsible agent", "Create minimal patch", "Rerun verifier", "Escalate only after retry budget"]
    attempts = [{"step": idx + 1, "action": action, "status": "planned"} for idx, action in enumerate(strategy)]
    block = {"type": "visual_repair_loop", "payload": {"title": root, "error": error_text, "context": context, "attempts": attempts, "max_retries": 5, "policy": "repair_then_retry_until_success_or_budget_exhausted"}}
    return {"agent": "DebuggingAgent", "root_cause": root, "repair_plan": strategy, "render_block": block}


def agent_panel_state() -> dict:
    state_file = STATE_DIR / "agentic_visual_panel.json"
    if state_file.exists():
        try:
            saved = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            saved = {}
    else:
        saved = {}
    return {
        "updated_at": datetime.now(UTC).isoformat(),
        "active_agents": ["PlannerAgent", "DesigningAgent", "DebuggingAgent", "ExecutorAgent", "VerifierAgent", "VisualRendererAgent", "ArtifactAgent"],
        "visual_components": VISUAL_COMPONENTS,
        "latest": saved,
        "next_actions": [
            "Route URL-design prompts through DesigningAgent before implementation.",
            "Route execution failures through DebuggingAgent repair plan before stopping.",
            "Render project outputs in chat using file gallery, preview, and download cards.",
        ],
    }


def save_panel_event(event: dict) -> dict:
    state_file = STATE_DIR / "agentic_visual_panel.json"
    payload = {"event": event, "saved_at": datetime.now(UTC).isoformat()}
    state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
