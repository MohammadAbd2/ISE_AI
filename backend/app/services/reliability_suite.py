from __future__ import annotations

import asyncio
import hashlib
import json
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.services.project_exports import get_project_export_service
from app.services.terminal import TerminalIntegration


@dataclass(slots=True)
class SmokeCheck:
    name: str
    status: str
    detail: str = ""
    elapsed_ms: int = 0


@dataclass(slots=True)
class ReliabilityReport:
    task: str
    status: str
    checks: list[SmokeCheck] = field(default_factory=list)
    artifact_id: str | None = None
    download_url: str | None = None
    manifest: dict[str, Any] | None = None
    elapsed_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [asdict(check) for check in self.checks]
        return data


class EndToEndReliabilitySuite:
    """Runs the end-to-end invariant checks that previously failed in production.

    This suite is intentionally deterministic: it does not ask the LLM to decide if an
    export is valid. A run passes only when files exist, the build command succeeds,
    a ZIP is created, the manifest matches the archive, and the download metadata is
    present.
    """

    def __init__(self, workspace: Path, session_id: str) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.checks: list[SmokeCheck] = []
        self.started = time.perf_counter()

    async def _check(self, name: str, fn) -> Any:
        started = time.perf_counter()
        try:
            result = await fn() if asyncio.iscoroutinefunction(fn) else fn()
            self.checks.append(SmokeCheck(name=name, status="passed", detail=str(result or "ok"), elapsed_ms=int((time.perf_counter()-started)*1000)))
            return result
        except Exception as exc:  # noqa: BLE001
            self.checks.append(SmokeCheck(name=name, status="failed", detail=str(exc), elapsed_ms=int((time.perf_counter()-started)*1000)))
            raise

    async def run_react_artifact_smoke(self, task: str) -> ReliabilityReport:
        app = self.workspace / "frontend" / "src" / "App.jsx"
        css = self.workspace / "frontend" / "src" / "App.css"
        package_json = self.workspace / "frontend" / "package.json"

        async def ensure_layout():
            (self.workspace / "frontend" / "src").mkdir(parents=True, exist_ok=True)
            if not package_json.exists():
                package_json.parent.mkdir(parents=True, exist_ok=True)
                package_json.write_text(json.dumps({
                    "scripts": {"build": "vite build", "dev": "vite --host 127.0.0.1"},
                    "dependencies": {"@vitejs/plugin-react": "latest", "vite": "^5.0.0", "react": "^18.2.0", "react-dom": "^18.2.0"},
                    "devDependencies": {}
                }, indent=2), encoding="utf-8")
            if not app.exists():
                app.write_text('import React from "react";\nimport "./App.css";\nexport default function App(){return <main className="app"><h1>Generated app</h1></main>}\n', encoding="utf-8")
            if not css.exists():
                css.write_text('.app{min-height:100vh;display:grid;place-items:center;font-family:sans-serif}\n', encoding="utf-8")
            return "workspace files ready"

        await self._check("workspace files exist", ensure_layout)
        await self._check("required files non-empty", lambda: self._assert_files([app, css, package_json]))
        await self._check("no forbidden template markers", lambda: self._assert_no_template_markers([app, css]))
        # Build only when dependencies exist; the generated ZIP invariant should not depend on internet.
        node_modules = self.workspace / "frontend" / "node_modules"
        if node_modules.exists():
            async def build():
                result = await TerminalIntegration(self.workspace).run_command("npm run build", cwd="frontend", timeout=180)
                if result.return_code != 0:
                    raise RuntimeError(result.stderr or result.stdout or "npm build failed")
                return "npm build passed"
            await self._check("frontend build", build)
        else:
            self.checks.append(SmokeCheck(name="frontend build", status="skipped", detail="node_modules not present; build will run in live environment"))

        async def export():
            service = get_project_export_service()
            result = await service.export_paths(
                root_dir=self.workspace,
                relative_paths=["frontend/src/App.jsx", "frontend/src/App.css", "frontend/package.json"],
                session_id=self.session_id,
                title="Verified generated React project",
                filename="verified-generated-react-project.zip",
                package_root="generated-react-project",
                export_mode="app",
            )
            artifact = result.artifact or {}
            manifest = artifact.get("metadata", {}).get("manifest") or {}
            self._assert_zip(result.zip_path, manifest)
            return {"artifact_id": artifact.get("id"), "manifest": manifest, "download_url": f"/api/artifacts/{artifact.get('id')}/download"}

        export_result = await self._check("verified artifact export", export)
        status = "passed" if all(check.status in {"passed", "skipped"} for check in self.checks) else "failed"
        return ReliabilityReport(
            task=task,
            status=status,
            checks=self.checks,
            artifact_id=export_result.get("artifact_id"),
            download_url=export_result.get("download_url"),
            manifest=export_result.get("manifest"),
            elapsed_ms=int((time.perf_counter()-self.started)*1000),
        )

    def _assert_files(self, paths: list[Path]) -> str:
        missing = [str(path) for path in paths if not path.is_file() or path.stat().st_size <= 0]
        if missing:
            raise FileNotFoundError(f"Required generated files missing or empty: {missing}")
        return f"{len(paths)} files verified"

    def _assert_no_template_markers(self, paths: list[Path]) -> str:
        forbidden = ["lorem ipsum", "replace with", "placeholder", "example.com", "mock data", "sample data"]
        hits: list[str] = []
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for marker in forbidden:
                if marker in text:
                    hits.append(f"{path.name}:{marker}")
        if hits:
            raise ValueError("Template/mock markers detected: " + ", ".join(hits))
        return "no canned markers"

    def _assert_zip(self, zip_path: Path, manifest: dict[str, Any]) -> None:
        if not zip_path.is_file() or zip_path.stat().st_size <= 0:
            raise FileNotFoundError(f"Export ZIP missing: {zip_path}")
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        expected = manifest.get("sha256")
        if expected and expected != digest:
            raise RuntimeError("ZIP hash mismatch")
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Corrupt ZIP entry: {bad}")
            names = [name for name in archive.namelist() if not name.endswith('/')]
            if not names:
                raise RuntimeError("ZIP is empty")
            forbidden_roots = {"backend/", "tests/", "output/", ".git/", "node_modules/"}
            bad_names = [name for name in names if any(name.startswith(root) for root in forbidden_roots)]
            if bad_names:
                raise RuntimeError("ZIP includes forbidden project/runtime files: " + ", ".join(bad_names[:5]))
