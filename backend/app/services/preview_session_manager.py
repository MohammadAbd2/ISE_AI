"""Preview session descriptors for browser-displayable generated apps.

The actual server process should be started by the sandbox runner/terminal agent.
This module creates a deterministic preview contract so the frontend can show a
preview action/link only when the generated artifact has a verified browser UI.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any


@dataclass(slots=True)
class PreviewContract:
    available: bool
    url: str | None
    command: str | None
    cwd: str | None
    reason: str
    preview_id: str
    health_command: str | None = None
    download_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_preview_contract(files: dict[str, str], *, validation_passed: bool, workspace_id: str = "sandbox", base_url: str | None = None, port: int | None = None) -> PreviewContract:
    has_vite = "frontend/package.json" in files and "frontend/src/main.jsx" in files
    preview_id = sha256((workspace_id + "|" + "|".join(sorted(files))).encode("utf-8")).hexdigest()[:12]
    port = int(port or 5174)
    base_url = (base_url or f"http://localhost:{port}").rstrip("/")
    if not has_vite:
        return PreviewContract(False, None, None, None, "No browser-renderable frontend was generated.", preview_id, None, None)
    if not validation_passed:
        return PreviewContract(False, None, f"npm install && npm run dev -- --host 0.0.0.0 --port {port}", "frontend", "Preview blocked until verification and repair gates pass.", preview_id, "npm run build", "Run verification first, then start preview.")
    return PreviewContract(
        True,
        f"{base_url}/preview/{preview_id}/",
        f"npm install && npm run dev -- --host 0.0.0.0 --port {port}",
        "frontend",
        "Verified Vite preview can be started from the sandbox workspace.",
        preview_id,
        "npm run build",
        "Use per-file download buttons or project export after gates pass.",
    )
