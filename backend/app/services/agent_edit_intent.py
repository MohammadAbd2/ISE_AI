"""Edit-intent detection and exact patch planning for the programming AGI.

This module prevents the agent from treating small user edits as a brand new
project generation request.  Requests like `change the title from X to Y` are
converted into a focused patch contract that can be applied inside the sandbox
against the copied project files.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any


@dataclass(slots=True)
class EditIntent:
    kind: str
    source_text: str
    target_text: str
    confidence: float
    patch_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TITLE_PATTERNS = (
    re.compile(r"change\s+(?:the\s+)?title\s+from\s+[\"'](?P<old>[^\"']+)[\"']\s+to\s+[\"'](?P<new>[^\"']+)[\"']", re.I),
    re.compile(r"update\s+(?:the\s+)?title\s+from\s+[\"'](?P<old>[^\"']+)[\"']\s+to\s+[\"'](?P<new>[^\"']+)[\"']", re.I),
    re.compile(r"rename\s+(?:the\s+)?title\s+[\"'](?P<old>[^\"']+)[\"']\s+to\s+[\"'](?P<new>[^\"']+)[\"']", re.I),
)


def detect_edit_intent(request: str) -> EditIntent | None:
    clean = " ".join(request.strip().split())
    for pattern in TITLE_PATTERNS:
        match = pattern.search(clean)
        if match:
            return EditIntent(
                kind="exact_text_replace:title",
                source_text=match.group("old"),
                target_text=match.group("new"),
                confidence=0.98,
                patch_policy="minimal_patch_only_no_regeneration",
            )
    return None


def apply_exact_text_patch(files: dict[str, str], intent: EditIntent) -> tuple[dict[str, str], dict[str, Any]]:
    """Patch every relevant occurrence and report exactly what changed.

    The function does not invent new product data, routes, styling, or sections.
    If the old title is not found, it returns unchanged files with a blocker so
    the DebugAgent can inspect the sandbox instead of regenerating the app.
    """
    changed: list[str] = []
    patched: dict[str, str] = {}
    source_suffixes = (".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".cs", ".py")
    metadata_names = {"agent-contract.json", "ROADMAP.md", "README.md", "RUN_REPORT.json", "verification-report.json"}
    for path, content in files.items():
        if path in metadata_names or path.startswith(("docs/", "scripts/")):
            patched[path] = content
            continue
        if path.endswith(source_suffixes):
            next_content = content.replace(intent.source_text, intent.target_text)
            if next_content != content:
                changed.append(path)
            patched[path] = next_content
        else:
            patched[path] = content
    return patched, {
        "intent": intent.to_dict(),
        "changed_files": changed,
        "passed": bool(changed),
        "blockers": [] if changed else [f"source title not found: {intent.source_text}"],
    }
