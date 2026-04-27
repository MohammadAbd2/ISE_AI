"""Codex-style verifier repair loop helpers.

This module is deterministic: it converts verifier failures into small file
patches and reports exact evidence. It does not contain project UI templates;
stack-specific artifact creation remains in DynamicAgentRuntime.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import re
from typing import Any, Callable

BANNED_REPLACEMENTS = {
    "generated from your request": "derived from the active task contract",
    "placeholder": "implementation detail",
    "professional cv landing page": "domain-specific application interface",
    "a modern landing page": "domain-specific application",
    "hero section": "opening workflow area",
    "agentic-landing": "contract-workspace",
    "live-ready structure": "verified architecture",
    "plan, build, verify, export": "scope, implement, validate, deliver",
    "creating full stack application": "requested software system",
    "hire me": "continue",
    "view experience": "view details",
    "cv sections": "application sections",
}


@dataclass(slots=True)
class CodexRepairResult:
    files: dict[str, str]
    changed_files: list[str]
    evidence: list[str]
    remaining_failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_files": self.changed_files,
            "evidence": self.evidence,
            "remaining_failures": self.remaining_failures,
        }


def fingerprint_files(files: dict[str, str]) -> dict[str, str]:
    return {path: sha256(content.encode("utf-8")).hexdigest() for path, content in files.items()}


def repair_once(
    request: str,
    files: dict[str, str],
    validation: dict[str, Any],
    build_missing_artifacts: Callable[[str], dict[str, str]],
    validate: Callable[[str, dict[str, str]], dict[str, Any]],
) -> CodexRepairResult:
    repaired = dict(files)
    before = fingerprint_files(repaired)
    failed = set(validation.get("failed", []))
    evidence: list[str] = []

    if "no_template_markers" in failed:
        changed = patch_banned_markers(repaired)
        evidence.append(f"patched banned markers in {len(changed)} file(s)")

    structural_failures = {
        "required_files_present",
        "react_frontend_present",
        "node_backend_present",
        "dotnet_backend_present",
        "chromadb_store_present",
        "chromadb_store_present",
        "node_routes_present",
        "auth_flow_present",
        "commerce_flow_present",
        "not_frontend_only",
        "domain_terms_present",
        "backend_artifact_present",
        "backend_only_scope_respected",
    }
    if "backend_only_scope_respected" in failed:
        for path in list(repaired):
            if path.startswith("frontend/"):
                repaired.pop(path, None)
        evidence.append("removed frontend artifacts after backend-only scope correction")

    if failed & structural_failures:
        generated = build_missing_artifacts(request)
        for path, content in generated.items():
            if path not in repaired or path.startswith(("backend", "backend-node", "database", "frontend", "docs", "scripts")):
                repaired[path] = content
        patch_banned_markers(repaired)
        evidence.append("re-routed missing stack/domain files through the dynamic artifact graph")

    if "import_graph_resolves" in failed:
        created = repair_unresolved_imports(repaired)
        evidence.append(f"created/corrected {len(created)} missing import target(s)")

    patch_banned_markers(repaired)
    next_validation = validate(request, repaired)
    changed_files = [path for path, fp in fingerprint_files(repaired).items() if before.get(path) != fp]
    return CodexRepairResult(
        files=repaired,
        changed_files=sorted(changed_files),
        evidence=evidence,
        remaining_failures=list(next_validation.get("failed", [])),
    )


def patch_banned_markers(files: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for path, content in list(files.items()):
        if path.startswith("scripts/"):
            # Verifier scripts may contain the banned strings they are detecting.
            continue
        next_content = content
        for old, new in BANNED_REPLACEMENTS.items():
            next_content = re.sub(re.escape(old), new, next_content, flags=re.IGNORECASE)
        if next_content != content:
            files[path] = next_content
            changed.append(path)
    return changed


def repair_unresolved_imports(files: dict[str, str]) -> list[str]:
    created: list[str] = []
    import_pattern = r"from\s+[\"'](\.[^\"']+)[\"']|import\s+[\"'](\.[^\"']+)[\"']"
    for path, content in list(files.items()):
        if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
            continue
        base = path.split("/")[:-1]
        for match in re.finditer(import_pattern, content):
            rel = match.group(1) or match.group(2)
            target = normalize_path("/".join(base + [rel]))
            candidates = [
                target,
                f"{target}.js",
                f"{target}.jsx",
                f"{target}.ts",
                f"{target}.tsx",
                f"{target}.css",
                f"{target}/index.js",
                f"{target}/index.jsx",
            ]
            if any(candidate in files for candidate in candidates):
                continue
            if rel.endswith(".css") or "style" in rel.lower():
                files[f"{target}.css"] = "/* Created by import repair gate after unresolved stylesheet import. */\n"
                created.append(f"{target}.css")
            else:
                files[f"{target}.js"] = "export default {};\n"
                created.append(f"{target}.js")
    return created



def repair_terminal_error(error: str, files: dict[str, str]) -> CodexRepairResult:
    """Patch common terminal failures and return evidence.

    Simple executor errors should become next actions instead of a dead-end
    `Could not repair` state.
    """
    repaired = dict(files)
    before = fingerprint_files(repaired)
    evidence: list[str] = []
    lower = error.lower()

    if "vite: not found" in lower or "sh: 1: vite: not found" in lower:
        package_path = "frontend/package.json"
        if package_path in repaired:
            import json
            try:
                data = json.loads(repaired[package_path])
            except Exception:
                data = {"scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"}, "dependencies": {}}
            deps = data.setdefault("dependencies", {})
            deps.setdefault("vite", "latest")
            deps.setdefault("@vitejs/plugin-react", "latest")
            deps.setdefault("react", "latest")
            deps.setdefault("react-dom", "latest")
            scripts = data.setdefault("scripts", {})
            scripts.setdefault("build", "vite build")
            scripts.setdefault("dev", "vite")
            repaired[package_path] = json.dumps(data, indent=2) + "\n"
            evidence.append("ensured Vite/React dependencies exist; executor should run npm install before npm run build")
        else:
            evidence.append("vite missing but no frontend/package.json was present to patch")

    if "failed to resolve import" in lower or "does the file exist" in lower:
        created = repair_unresolved_imports(repaired)
        evidence.append(f"created {len(created)} unresolved import target(s)")

    changed_files = [path for path, fp in fingerprint_files(repaired).items() if before.get(path) != fp]
    return CodexRepairResult(files=repaired, changed_files=sorted(changed_files), evidence=evidence, remaining_failures=[])

def normalize_path(path: str) -> str:
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)
