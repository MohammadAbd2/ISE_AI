"""Dynamic tool routing descriptors for programming-agent tasks."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

@dataclass(slots=True)
class ToolRoute:
    name: str
    status: str
    trigger: str
    reason: str
    user_visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_tools(prompt: str, has_files: bool = False, previewable: bool = False) -> list[dict[str, Any]]:
    text = prompt.lower()
    routes = [
        ToolRoute("ProjectSearchAgent", "available", "folder/path/codebase", "Reads project files before editing when a workspace path is provided.").to_dict(),
        ToolRoute("TerminalAgent", "available", "build/test/run command", "Runs commands in sandbox and feeds errors into the repair loop.").to_dict(),
        ToolRoute("VerifierAgent", "available", "export/merge gate", "Blocks ZIP/merge until required files, imports, stack coverage, and anti-template gates pass.").to_dict(),
    ]
    if previewable or any(word in text for word in ("website", "component", "page", "react", "frontend", "browser", "preview")):
        routes.append(ToolRoute("PreviewAgent", "selected", "browser-renderable output", "Creates a direct preview contract after frontend verification passes.").to_dict())
    if any(word in text for word in ("internet", "search", "latest", "docs", "learn", "research")):
        routes.append(ToolRoute("WebResearchAgent", "selected", "search/docs/latest", "Should browse and cite current docs before implementing unfamiliar or recent APIs.").to_dict())
    if any(word in text for word in ("image", "photo", "picture", "logo", "asset", "generate photos")):
        routes.append(ToolRoute("ImageGenerationAgent", "selected", "visual asset generation", "Routes visual asset creation to the image generation capability.").to_dict())
    if has_files:
        routes.append(ToolRoute("FileTreeAgent", "selected", "generated or loaded files", "Renders folders/files with type icons, preview, and per-file download.").to_dict())
    return routes
