from __future__ import annotations
from pathlib import Path
import re
from typing import Any

BANNED = ["agentic-landing", "generated from your request", "placeholder", "professional cv landing page", "a modern landing page"]

class AGIVerifier:
    def verify_graph(self, request: str, files: dict[str, str], contract: dict[str, Any]) -> dict[str, Any]:
        checks = {}
        paths = set(files)
        checks["contract_exists"] = "agent-contract.json" in paths
        checks["roadmap_exists"] = "docs/ROADMAP.md" in paths
        app_text = "\n".join(v for k, v in files.items() if not k.startswith(("docs/", "scripts/")) and not k.endswith(".json")).lower()
        checks["no_template_markers"] = not any(b in app_text for b in BANNED)
        checks["import_graph_resolves"] = self.imports_resolve(files)
        stacks = set(contract.get("stacks", []))
        if "react" in stacks:
            checks["react_frontend_present"] = all(p in paths for p in ["frontend/package.json", "frontend/src/main.jsx", "frontend/src/App.jsx"])
        if "node" in stacks:
            checks["node_backend_present"] = "backend-node/src/server.js" in paths
        if "chromadb" in stacks:
            checks["chromadb_store_present"] = "database/chromadb/collections.json" in paths or "backend-node/src/chromaStore.js" in paths
        failed = [k for k, ok in checks.items() if not ok]
        return {"passed": not failed, "checks": checks, "failed": failed, "score": round(sum(1 for ok in checks.values() if ok) / max(len(checks), 1) * 100, 2)}

    def imports_resolve(self, files: dict[str, str]) -> bool:
        for path, content in files.items():
            if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            base = path.split('/')[:-1]
            for m in re.finditer(r"from\s+[\"'](\.[^\"']+)[\"']|import\s+[\"'](\.[^\"']+)[\"']", content):
                rel = m.group(1) or m.group(2)
                target = self.norm('/'.join(base + [rel]))
                candidates = [target, target+'.js', target+'.jsx', target+'.ts', target+'.tsx', target+'.css', target+'/index.js', target+'/index.jsx']
                if not any(c in files for c in candidates):
                    return False
        return True

    def norm(self, path: str) -> str:
        parts = []
        for p in path.split('/'):
            if p in ('', '.'):
                continue
            if p == '..':
                if parts: parts.pop()
            else:
                parts.append(p)
        return '/'.join(parts)
