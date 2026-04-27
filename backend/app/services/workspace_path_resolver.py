"""Prompt-controlled workspace path resolution."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any

PATH_PATTERNS = (
    r"(?:your current folder are|your current folder is|you are now in|based on the content of this folder|based on this folder|project is in this path|the project is in this path)\s+([^\n]+)",
    r"(?:current folder|working folder|workspace|project path|folder|path)\s*[:=]\s*([^\n]+)",
)
STOP_WORDS = (" then ", " and then ", " create ", " improve ", " fix ", " update ", " merge ")


@dataclass(slots=True)
class WorkspacePathResolution:
    raw: str | None
    expanded: str | None
    exists: bool
    source: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_workspace_path(prompt: str, explicit_path: str | None = None) -> WorkspacePathResolution:
    raw = explicit_path.strip() if explicit_path else None
    source = "input" if raw else "none"
    if not raw:
        for pattern in PATH_PATTERNS:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                raw = match.group(1).strip().strip("`\"' ")
                source = "prompt"
                break
    if raw:
        lowered = raw.lower()
        for marker in STOP_WORDS:
            if marker in lowered:
                idx = lowered.find(marker)
                raw = raw[:idx].strip()
                lowered = raw.lower()
        raw = raw.rstrip(".,;)")
        expanded = str(Path(raw).expanduser())
        exists = Path(expanded).exists()
        warnings = [] if exists else ["Path was parsed but does not exist in the current runtime; sandbox copy will be skipped until the local backend can access it."]
        return WorkspacePathResolution(raw=raw, expanded=expanded, exists=exists, source=source, warnings=warnings)
    return WorkspacePathResolution(raw=None, expanded=None, exists=False, source="none", warnings=["No workspace path provided; using clean sandbox project generation."])
