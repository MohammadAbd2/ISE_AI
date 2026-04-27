from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class ToolRoute:
    capability: str
    trigger: list[str]
    tool: str
    safety: str
    enabled: bool

    def to_dict(self):
        return asdict(self)

class ToolRouter:
    def routes_for(self, request: str) -> list[dict]:
        text = request.lower()
        routes = [
            ToolRoute("terminal", ["build", "test", "install", "run"], "safe_shell", "allowlist + sandbox only", True),
            ToolRoute("filesystem", ["create", "edit", "merge", "copy"], "safe_filesystem", "path normalization + ignored state dirs", True),
            ToolRoute("preview", ["website", "component", "browser", "preview"], "preview_manager", "real URL/port contract only", True),
            ToolRoute("web_search", ["search", "internet", "docs", "latest"], "web_search_agent", "admin toggle + citation required", False),
            ToolRoute("image_generation", ["image", "photo", "generate picture"], "image_generation_agent", "admin toggle + policy checks", False),
        ]
        selected = []
        for route in routes:
            if any(t in text for t in route.trigger):
                selected.append(route.to_dict())
        return selected or [routes[0].to_dict(), routes[1].to_dict()]
