"""Normalize agent outputs into one frontend-safe contract.

The chat UI can receive results from chat, web search, image search, vision,
Programming AGI, and multi-agent runtimes. Those services often emit repeated
URLs or differently shaped resources. This module turns them into one compact,
deduplicated payload so the frontend displays each resource once.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref", "source"}


@dataclass(slots=True)
class NormalizedResource:
    url: str
    title: str = "Untitled resource"
    domain: str = ""
    snippet: str = ""
    kind: str = "web"
    image_url: str = ""
    favicon_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_url(raw_url: str) -> str:
    raw = (raw_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in _TRACKING_KEYS and not any(key.startswith(prefix) for prefix in _TRACKING_PREFIXES)
    ]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", urlencode(query), ""))


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _resource_from_any(item: Any, *, default_kind: str = "web") -> NormalizedResource | None:
    if isinstance(item, str):
        url = canonical_url(item)
        return NormalizedResource(url=url, domain=_domain(url), kind=default_kind) if url else None
    if not isinstance(item, dict):
        return None
    raw_url = item.get("url") or item.get("href") or item.get("link") or item.get("source") or item.get("image_url") or ""
    url = canonical_url(str(raw_url))
    if not url:
        return None
    image_url = item.get("image_url") or item.get("thumbnail") or item.get("thumbnail_url") or (url if default_kind == "image" else "")
    domain = item.get("domain") or _domain(url)
    favicon = item.get("favicon_url") or (f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "")
    return NormalizedResource(
        url=url,
        title=str(item.get("title") or item.get("name") or domain or "Untitled resource")[:180],
        domain=str(domain),
        snippet=str(item.get("snippet") or item.get("description") or item.get("summary") or "")[:500],
        kind=str(item.get("kind") or item.get("type") or default_kind),
        image_url=str(image_url or ""),
        favicon_url=str(favicon),
    )


def collect_resources(*payloads: Any, limit: int = 12) -> list[dict[str, Any]]:
    """Extract, canonicalize, and dedupe resources from arbitrary nested payloads."""
    seen: set[str] = set()
    output: list[NormalizedResource] = []

    def visit(value: Any, inherited_kind: str = "web") -> None:
        if len(output) >= limit:
            return
        if isinstance(value, dict):
            direct = _resource_from_any(value, default_kind=inherited_kind)
            if direct and direct.url not in seen:
                seen.add(direct.url)
                output.append(direct)
                return
            for key, child in value.items():
                key_lower = str(key).lower()
                child_kind = "image" if "image" in key_lower or "thumbnail" in key_lower else inherited_kind
                if key_lower in {"resources", "sources", "search_logs", "image_logs", "results", "links", "citations"} or isinstance(child, (list, dict)):
                    visit(child, child_kind)
        elif isinstance(value, list):
            for child in value:
                visit(child, inherited_kind)
        elif isinstance(value, str) and value.startswith(("http://", "https://")):
            direct = _resource_from_any(value, default_kind=inherited_kind)
            if direct and direct.url not in seen:
                seen.add(direct.url)
                output.append(direct)

    for payload in payloads:
        visit(payload)
    return [item.to_dict() for item in output]


def build_ui_contract(*, task: str, plan: dict[str, Any], execution: dict[str, Any], timeline: list[dict[str, Any]], memory: dict[str, Any]) -> dict[str, Any]:
    resources = collect_resources(plan, execution, timeline, limit=12)
    files = execution.get("files") or execution.get("files_changed") or []
    export = execution.get("export") if isinstance(execution.get("export"), dict) else {}
    artifact_id = export.get("artifact_id") if export else None
    truth_payload = {
        "is_real": bool(files or artifact_id or execution.get("preview")),
        "verified": bool(execution.get("validation", {}).get("passed", False)) if isinstance(execution.get("validation"), dict) else execution.get("status") == "completed",
        "has_preview": bool(execution.get("preview")),
        "score": 100 if execution.get("status") == "completed" else 72,
        "checks": {
            "filesystem_effect": bool(files),
            "preview_available": bool(execution.get("preview")),
            "verification_passed": bool(execution.get("validation", {}).get("passed", False)) if isinstance(execution.get("validation"), dict) else execution.get("status") == "completed",
        },
    }
    engineer_dashboard = {
        "title": "AI Engineer Workbench",
        "headline": "Watching an AI engineer work",
        "truth": truth_payload,
        "lanes": [
            {"name": "Thinking", "items": [event for event in timeline if str(event.get("agent", "")).lower() in {"memoryagent", "planneragent", "routeragent"}]},
            {"name": "Building", "items": [event for event in timeline if str(event.get("agent", "")).lower() in {"executoragent", "frontendagent", "backendagent", "designingagent"}]},
            {"name": "Debugging", "items": [event for event in timeline if str(event.get("agent", "")).lower() in {"debugagent", "repairagent", "verifieragent"}]},
            {"name": "Shipping", "items": [event for event in timeline if str(event.get("agent", "")).lower() in {"previewagent", "exportagent", "artifactagent"}]},
        ],
    }
    blocks = [
        {"type": "ai_engineer_workbench", "payload": engineer_dashboard},
        {"type": "truth_layer_card", "payload": truth_payload},
        {"type": "agent_timeline", "payload": {"events": timeline, "status": execution.get("status", "completed"), "artifacts": [artifact_id] if artifact_id else []}},
    ]
    if execution.get("folder_listing"):
        blocks.append({"type": "folder_listing", "payload": {"title": "Isolated environment files", "files": execution.get("folder_listing")}})
    if execution.get("file_content") is not None:
        blocks.append({"type": "file_preview", "payload": {"title": "File content", "content": execution.get("file_content")}})
    if files:
        blocks.append({"type": "visual_file_gallery", "payload": {"title": "Generated project files", "files": [{"path": str(item), "summary": "Changed or generated by Agent."} for item in files[:80]], "artifact": {"artifact_id": artifact_id} if artifact_id else {}}})
    failed = execution.get("validation", {}).get("failed", []) if isinstance(execution.get("validation"), dict) else []
    if failed:
        blocks.append({"type": "visual_repair_loop", "payload": {"title": "DebuggingAgent repair loop", "error": " · ".join(map(str, failed)), "attempts": [{"step": 1, "action": "Classify failed verifier gates", "status": "completed"}, {"step": 2, "action": "Patch imports, template markers, or build errors", "status": "planned"}, {"step": 3, "action": "Rerun verifier and continue", "status": "planned"}], "policy": "repair_then_retry_until_success_or_budget_exhausted"}})
    if artifact_id or export.get("path"):
        blocks.append({"type": "download_card", "payload": {"title": export.get("filename") or "Download result", "artifact_id": artifact_id, "download_url": export.get("download_url"), "file_count": export.get("file_count"), "size_bytes": export.get("size_bytes"), "sha256": export.get("sha256")}})
    if resources:
        blocks.append({"type": "resource_list", "payload": {"title": "Sources and images", "resources": resources}})
    return {
        "task": task,
        "display_mode": "agent_workspace",
        "resources": resources,
        "resource_count": len(resources),
        "files_changed": files,
        "artifact_id": artifact_id,
        "export": export,
        "folder_listing": execution.get("folder_listing") or [],
        "file_content": execution.get("file_content"),
        "memory_hits": len(memory.get("memories", [])) + len(memory.get("lessons", [])) if isinstance(memory, dict) else 0,
        "blocks": blocks,
    }
