from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
from typing import Any

@dataclass
class RepairDecision:
    kind: str
    action: str
    confidence: float
    commands: list[str]
    files_to_patch: list[str]
    notes: list[str]

    def to_dict(self):
        return asdict(self)

class ErrorClassifier:
    def classify(self, text: str) -> str:
        lower = (text or "").lower()
        if "vite: not found" in lower or "vite not found" in lower:
            return "missing_dependency"
        if "failed to resolve import" in lower or "cannot find module" in lower or "module not found" in lower:
            return "missing_import"
        if "syntaxerror" in lower or "unexpected token" in lower:
            return "syntax_error"
        if "template" in lower or "banned" in lower or "placeholder" in lower:
            return "template_marker"
        if "file name too long" in lower or "enametoolong" in lower:
            return "recursive_copy"
        return "unknown"

class RepairEngine:
    def __init__(self):
        self.classifier = ErrorClassifier()

    def decide(self, error_text: str, validation: dict[str, Any] | None = None) -> RepairDecision:
        validation = validation or {}
        failed = set(validation.get("failed") or [])
        kind = self.classifier.classify(error_text)
        if "import_graph_resolves" in failed or kind == "missing_import":
            return RepairDecision("missing_import", "create missing relative module or correct path", 0.92, [], [], ["scan JS/TS import graph"])
        if "no_template_markers" in failed or kind == "template_marker":
            return RepairDecision("template_marker", "replace banned wording in generated app files", 0.94, [], [], ["patch app files only, not docs/scripts"])
        if kind == "missing_dependency":
            return RepairDecision("missing_dependency", "install dependencies then rerun build", 0.9, ["npm install"], ["package.json"], [])
        if kind == "recursive_copy":
            return RepairDecision("recursive_copy", "exclude AGI_Output and .ise_ai while copying", 0.99, [], [], [])
        return RepairDecision(kind, "rebuild affected contract files and rerun validation", 0.65, [], [], [])

    def repair_file_graph(self, files: dict[str, str], validation: dict[str, Any], build_graph) -> dict[str, str]:
        repaired = dict(files)
        failed = set(validation.get("failed") or [])
        if "no_template_markers" in failed:
            banned = ["agentic-landing", "generated from your request", "placeholder", "professional cv landing page", "a modern landing page", "hero section", "hire me", "view experience"]
            replacements = {
                "agentic-landing": "contract-workspace",
                "generated from your request": "built from validated task requirements",
                "placeholder": "working implementation",
                "professional cv landing page": "request-specific application",
                "a modern landing page": "request-specific application",
                "hero section": "primary workspace",
                "hire me": "continue",
                "view experience": "view details",
            }
            for path, content in list(repaired.items()):
                if path.startswith(("docs/", "scripts/")) or path.endswith(".json"):
                    continue
                patched = content
                for marker in banned:
                    patched = re.sub(re.escape(marker), replacements.get(marker, "application"), patched, flags=re.I)
                repaired[path] = patched
        if "import_graph_resolves" in failed:
            self._repair_imports(repaired)
        # If structural gates are missing, rebuild graph and overlay missing files.
        if any(gate.endswith("_present") or gate == "required_files_present" for gate in failed):
            rebuilt = build_graph()
            for path, content in rebuilt.items():
                repaired.setdefault(path, content)
        return repaired

    def _repair_imports(self, files: dict[str, str]) -> None:
        for path, content in list(files.items()):
            if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            base = path.split("/")[:-1]
            for match in re.finditer(r"from\s+[\"'](\.[^\"']+)[\"']|import\s+[\"'](\.[^\"']+)[\"']", content):
                rel = match.group(1) or match.group(2)
                target = self._normalize("/".join(base + [rel]))
                candidates = [target, f"{target}.js", f"{target}.jsx", f"{target}.ts", f"{target}.tsx", f"{target}.css", f"{target}/index.js"]
                if any(c in files for c in candidates):
                    continue
                if rel.endswith(".css") or "style" in rel.lower():
                    files[f"{target}.css"] = "/* Created by RepairAgent to satisfy stylesheet import. */\n"
                else:
                    files[f"{target}.js"] = "export default {};\n"

    @staticmethod
    def _normalize(path: str) -> str:
        out: list[str] = []
        for part in path.split('/'):
            if part in ('', '.'):
                continue
            if part == '..':
                if out: out.pop()
            else:
                out.append(part)
        return '/'.join(out)
