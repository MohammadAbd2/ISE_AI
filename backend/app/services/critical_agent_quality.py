from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import difflib
import html
import re
from typing import Any

from app.services.safe_file_writer import atomic_write_text, verify_text_content

@dataclass(slots=True)
class ResultContract:
    kind: str
    title: str
    summary: str
    blocks: list[dict[str, Any]]
    confidence: float = 1.0
    route: str = "message_result"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_quoted_content(message: str) -> str:
    text = message or ""
    patterns = [
        # Prefer semantic content/message captures before single-quote extraction so apostrophes inside words are preserved.
        r"content\s+(?:to\s+be|as|is)\s*[:=]?\s*['\"“”]?(.+?)['\"“”]?\s*(?:then|and\s+then|into\s+a|in\s+a|$)",
        r"message\s*(?:->|:|=)\s*['\"“”]?(.+?)['\"“”]?\s*(?:into\s+a|in\s+a|to\s+a|$)",
        r"[\"“”]([^\"“”]{0,20000})[\"“”]",
        r"'([^']{0,20000})'",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return match.group(1).strip().strip("'\"“” ")
    return text.strip()

def build_static_html_from_message(message: str) -> str:
    if "<html" in (message or "").lower() or "<!doctype" in (message or "").lower():
        return message
    phrase = extract_quoted_content(message) or "Hi from Agent"
    if len(phrase) > 4000:
        phrase = phrase[:4000]
    safe = html.escape(phrase)
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Agent Preview</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Inter, system-ui, sans-serif; background: linear-gradient(135deg,#eef2ff,#f8fafc); color: #0f172a; }
    .dev-element { padding: 32px 42px; border-radius: 24px; background: white; box-shadow: 0 24px 80px rgba(15,23,42,.16); border: 1px solid rgba(99,102,241,.2); font-size: clamp(2rem, 6vw, 4rem); font-weight: 900; letter-spacing: -0.04em; }
  </style>
</head>
<body>
  <div class=\"dev-element\">%s</div>
</body>
</html>""" % safe


def classify_error(error_text: str) -> dict[str, Any]:
    text = (error_text or "").lower()
    if any(t in text for t in ["module not found", "cannot resolve", "import_graph", "unresolved import"]):
        return {"category": "import_graph", "root_cause": "An import path or dependency is missing.", "severity": "high"}
    if any(t in text for t in ["template", "placeholder", "todo", "no_template"]):
        return {"category": "template_marker", "root_cause": "Generated output still contains placeholder/template markers.", "severity": "medium"}
    if any(t in text for t in ["syntaxerror", "unexpected token", "unterminated", "parse"]):
        return {"category": "syntax", "root_cause": "A generated source file has invalid syntax.", "severity": "high"}
    if any(t in text for t in ["eaddrinuse", "address already in use", "port"]):
        return {"category": "preview_port", "root_cause": "Preview port is unavailable or preview process failed.", "severity": "medium"}
    if any(t in text for t in ["checksum", "content_mismatch", "truncated", "write verification"]):
        return {"category": "file_write", "root_cause": "Generated file content did not match the requested content.", "severity": "critical"}
    if any(t in text for t in ["npm err", "dependency", "package", "lockfile"]):
        return {"category": "dependency", "root_cause": "Dependency installation or package configuration failed.", "severity": "high"}
    return {"category": "unknown", "root_cause": "The failure needs stdout/stderr inspection before patching.", "severity": "unknown"}


def repair_plan_for_error(error_text: str, context: str = "", retry_limit: int = 5) -> dict[str, Any]:
    cls = classify_error(error_text)
    strategies = {
        "import_graph": ["Scan imports and referenced files", "Create missing modules or rewrite paths", "Install missing dependency only when package is valid", "Rerun import/build verifier"],
        "template_marker": ["Search generated files for banned markers", "Replace placeholders with task-specific content", "Rerun no-template verifier", "Continue export only when clean"],
        "syntax": ["Locate failing file/line", "Patch syntax with smallest safe edit", "Run parser/build again", "Store failure pattern as validator"],
        "preview_port": ["Allocate a free non-5173 port", "Restart local preview process", "Capture preview logs", "Verify URL responds or fallback to static iframe"],
        "file_write": ["Rewrite file atomically", "Verify exact content/checksum", "Retry failed write", "Display content verification evidence"],
        "dependency": ["Read package manager output", "Patch package.json/scripts", "Run npm install/build again", "Pin safe dependency versions"],
        "unknown": ["Collect stdout/stderr and changed files", "Map failure to responsible agent", "Create minimal patch", "Rerun verifier or return diagnostic after retry budget"],
    }
    actions = strategies.get(cls["category"], strategies["unknown"])
    attempts = [{"step": i + 1, "action": action, "status": "planned"} for i, action in enumerate(actions)]
    block = {"type": "visual_repair_loop", "payload": {"title": f"DebuggingAgent: {cls['root_cause']}", "error": error_text, "context": context, "policy": "analyze → patch → rerun → verify", "attempts": attempts, "classification": cls}}
    return {"classification": cls, "context": context, "retry_limit": retry_limit, "attempts": attempts, "policy": "analyze → patch → rerun → verify; diagnostic only after retry budget", "render_block": block}


def normalize_result_contract(kind: str, title: str, summary: str, blocks: list[dict[str, Any]], route: str = "") -> dict[str, Any]:
    return ResultContract(kind=kind, title=title, summary=summary, blocks=blocks, route=route or kind).to_dict()


def make_preview_result_contract(title: str, html_content: str, file_info: dict[str, Any] | None = None) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {"type": "figma_prototype_preview", "payload": {"title": title, "html": html_content}},
        {"type": "visual_file_gallery", "payload": {"title": "Preview files", "files": [{"path": title, "kind": "html", "content": html_content, "artifact_id": (file_info or {}).get("artifact_id"), "summary": "Static HTML preview rendered directly in chat."}]}},
    ]
    if file_info:
        blocks.append({"type": "download_card", "payload": {"title": file_info.get("filename") or title, "artifact_id": file_info.get("artifact_id"), "download_url": file_info.get("download_url"), "extension": ".html", "icon": "🌐", "size_bytes": file_info.get("size_bytes"), "sha256": file_info.get("sha256"), "file_count": 1, "write_verified": file_info.get("write_verified")}})
    return normalize_result_contract("preview_result", title, "Static browser preview is ready.", blocks, "static_html_preview")


def build_ide_patch(file_path: str, original: str, requested_change: str) -> dict[str, Any]:
    marker = f"\n\n/* Agent requested change:\n{requested_change.strip()}\n*/\n"
    updated = original.rstrip() + marker
    diff = "".join(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile=file_path, tofile=file_path))
    return {"type": "ide_patch", "file": file_path, "diff": diff, "updated_content": updated, "apply_mode": "replace_document_after_user_approval", "backup_required": True, "refresh_editor": True, "render_blocks": [
        {"type": "visual_data_table", "payload": {"title": "IDE write-back contract", "columns": ["field", "value"], "rows": [{"field": "file", "value": file_path}, {"field": "apply_mode", "value": "replace_document_after_user_approval"}, {"field": "backup_required", "value": "true"}]}},
        {"type": "file_preview", "payload": {"title": "Proposed diff", "path": file_path, "language": "diff", "content": diff}},
    ]}


def verified_text_file(path: str | Path, content: str) -> dict[str, Any]:
    result = atomic_write_text(path, content)
    verification = verify_text_content(path, content)
    return {"write": asdict(result), "verification": verification, "ok": result.verified and verification.get("ok")}


def quality_roadmap() -> dict[str, Any]:
    return {"title": "Critical Agent Gap Fix Roadmap v9", "status": "implemented_foundation", "phases": [
        {"id": "P1", "name": "Routing correctness", "status": "implemented"},
        {"id": "P2", "name": "File-content reliability", "status": "implemented"},
        {"id": "P3", "name": "Real preview execution", "status": "implemented"},
        {"id": "P4", "name": "Self-healing execution loop", "status": "implemented"},
        {"id": "P5", "name": "Better DebuggingAgent", "status": "implemented"},
        {"id": "P6", "name": "Agent chat result contract", "status": "implemented"},
        {"id": "P7", "name": "Agent visual components", "status": "implemented"},
        {"id": "P8", "name": "Figma/design pipeline", "status": "implemented"},
        {"id": "P9", "name": "IDE write-back reliability", "status": "implemented"},
        {"id": "P10", "name": "Memory correctness", "status": "guardrails_added"},
    ]}
