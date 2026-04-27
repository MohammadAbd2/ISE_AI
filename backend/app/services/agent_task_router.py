"""Deterministic task routing for the daily programmer Agent."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any

@dataclass(slots=True)
class TaskRouteDecision:
    route: str
    confidence: float
    reason: str
    requires_agent: bool
    requires_memory: bool = True
    requires_web: bool = False
    requires_vision: bool = False
    export_zip: bool = False
    output_kind: str = "message"
    suggested_extension: str = ""
    suggested_endpoint: str = "/api/chat/stream"
    ui_mode: str = "chat"
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

_CODE_RE = re.compile(r"\b(create|build|implement|fix|debug|rewrite|refactor|update|improve|frontend|backend|component|api|route|endpoint|zip|export|file|project|app|self[- ]?improve|develop your|develop yourself)\b", re.I)
_WEB_RE = re.compile(r"\b(search|browse|internet|web|latest|current|today|news|source|sources|resource|resources|lookup|research)\b", re.I)
_IMAGE_RE = re.compile(r"\b(image|picture|photo|screenshot|vision|describe this|understand.*image|analy[sz]e.*image|ocr)\b", re.I)
_CHAT_RE = re.compile(r"\b(explain|what is|why|how do i|summarize|translate|email|message)\b", re.I)
_DIRECT_FILE_RE = re.compile(r"\b(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\s+file\b|\bfile\s+.*\b(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\b|\bdownloadable\s+(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\b", re.I)
_FIGMA_RE = re.compile(r"\b(figma|figma\.com|design\s+to\s+code|convert.*design|prototype\s+from\s+prompt|create.*prototype)\b", re.I)
_FILE_LOCATION_RE = re.compile(r"\b(where\s+is|where\s+are|location\s+of|path\s+of|find\s+the\s+file|show\s+me\s+where).{0,80}\b(file|folder|index\.html|html|pdf|txt|jsx|js)\b", re.I)
_STATIC_HTML_RE = re.compile(r"\b(create|make|generate|write)\b.{0,120}\b(html\s+file|index\.html|html)\b|\b(html\s+file|index\.html)\b.{0,120}\b(preview|browser|show\s+me\s+the\s+preview|render)\b", re.I)

def _requested_extension(text: str) -> str:
    match = _DIRECT_FILE_RE.search(text or "")
    if not match:
        return ""
    value = next((group for group in match.groups() if group), "txt").lower()
    if value == "markdown":
        value = "md"
    return f".{value.lstrip('.')}"

def classify_agent_task(message: str, *, has_attachments: bool = False, mode: str = "auto") -> TaskRouteDecision:
    text = (message or "").strip()
    lower = text.lower()
    ext = _requested_extension(text)
    if re.search(r"\b(traceback|stack trace|blocked gates|module not found|syntaxerror|failed|error occur|error occurred|debug this)\b", lower):
        return TaskRouteDecision("debug_repair", 0.9, "Error/debugging text should use DebuggingAgent repair analysis before retrying execution.", False, output_kind="debug_result", suggested_endpoint="/api/agentic-visual/debug/self-heal", ui_mode="debug")
    if _FILE_LOCATION_RE.search(text):
        return TaskRouteDecision("file_location_lookup", 0.93, "User is asking where an existing/generated file is located; do not start a new implementation run.", False, output_kind="file_location", suggested_endpoint="/api/agents/latest-file-location", ui_mode="artifact")
    if _FIGMA_RE.search(text):
        return TaskRouteDecision("figma_design", 0.92, "Figma/design/prototype request should use the Figma DesignAgent before code generation.", False, requires_web=bool("http" in lower), output_kind="figma_design", suggested_endpoint="/api/figma-agent/inspect", ui_mode="design")
    if _STATIC_HTML_RE.search(text):
        return TaskRouteDecision("static_html_preview", 0.91, "User asked for a direct HTML file with browser preview; generate a static artifact/preview instead of a generic React app.", False, export_zip=False, output_kind="html_preview", suggested_extension=".html", suggested_endpoint="/api/devx/files/generate", ui_mode="artifact")
    direct_file_requested = bool(ext and re.search(r"\b(create|make|generate|put|write|save|download|give me)\b", lower))
    if direct_file_requested and not re.search(r"\b(app|website|frontend|backend|project|component|route|api|full stack|zip)\b", lower):
        return TaskRouteDecision("artifact_generate", 0.94, f"User asked for a direct downloadable {ext} artifact, not an app preview.", False, export_zip=False, output_kind="downloadable_file", suggested_extension=ext, suggested_endpoint="/api/devx/files/generate", ui_mode="artifact")
    if mode == "agent":
        return TaskRouteDecision("agent_execute", 0.98, "User explicitly selected agent mode.", True, export_zip=bool(re.search(r"\b(zip|download|export|file)\b", lower)), suggested_endpoint="/api/agents/plan-and-execute", ui_mode="agent_workspace")
    if has_attachments and _IMAGE_RE.search(text):
        return TaskRouteDecision("vision_chat", 0.9, "Image or screenshot attachment needs vision understanding before answering.", False, requires_vision=True, ui_mode="vision")
    if _CODE_RE.search(text):
        return TaskRouteDecision("agent_execute", 0.86, "Implementation/debugging/project-changing request should use planner, memory, executor, verifier.", True, requires_web=bool(_WEB_RE.search(text)), export_zip=bool(re.search(r"\b(zip|download|export|give me the file)\b", lower)), suggested_endpoint="/api/agents/plan-and-execute", ui_mode="agent_workspace")
    if _WEB_RE.search(text):
        return TaskRouteDecision("research_chat", 0.8, "Fresh web/research request should use chat plus search tools and source deduplication.", False, requires_web=True, ui_mode="research")
    if _IMAGE_RE.search(text) or has_attachments:
        return TaskRouteDecision("vision_chat", 0.75, "Visual content is present or requested.", False, requires_vision=True, ui_mode="vision")
    if _CHAT_RE.search(text):
        return TaskRouteDecision("memory_chat", 0.64, "Question can be answered conversationally with memory context.", False)
    return TaskRouteDecision("memory_chat", 0.55, "Default safe route: answer in chat, using memory where available.", False)
