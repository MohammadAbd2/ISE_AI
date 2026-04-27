"""Runtime preview registry for verified generated projects."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PreviewSession:
    id: str
    workspace: Path
    command: str
    url: str


class RuntimePreviewRegistry:
    def __init__(self) -> None:
        self.sessions: dict[str, PreviewSession] = {}

    def create_static_preview_command(self, workspace: Path, *, port: int = 4173) -> dict[str, Any]:
        preview_id = str(uuid4())
        frontend = workspace / "frontend"
        if not (frontend / "dist").exists():
            return {"status": "unavailable", "id": preview_id, "reason": "No frontend/dist build found"}
        command = f"cd {frontend} && python3 -m http.server {port} --directory dist"
        session = PreviewSession(preview_id, workspace, command, f"http://localhost:{port}")
        self.sessions[preview_id] = session
        return {"status": "ready", "id": preview_id, "url": session.url, "command": command}


_registry = RuntimePreviewRegistry()

def get_preview_registry() -> RuntimePreviewRegistry:
    return _registry
