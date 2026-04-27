from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ValidationCheck:
    name: str
    status: str
    detail: str = ""
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass(slots=True)
class ExecutionValidationReport:
    id: str
    status: str
    checks: list[ValidationCheck]
    artifact_path: str | None = None
    created_at: str = field(default_factory=_now)
    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "artifact_path": self.artifact_path, "created_at": self.created_at, "checks": [c.to_dict() for c in self.checks]}


class ExecutionGuaranteeValidator:
    """Hard execution gate: no fake success, no empty output, no broken ZIP."""
    def validate(self, *, workspace: str | Path, expected_files: list[str] | None = None, artifact_path: str | Path | None = None) -> ExecutionValidationReport:
        workspace = Path(workspace).expanduser().resolve()
        checks: list[ValidationCheck] = [ValidationCheck("workspace_exists", "passed" if workspace.exists() else "failed", str(workspace))]
        if expected_files:
            for rel in expected_files:
                path = (workspace / rel).resolve()
                ok = path.is_file() and path.stat().st_size > 0
                checks.append(ValidationCheck(f"file:{rel}", "passed" if ok else "failed", f"{path} ({path.stat().st_size if path.exists() else 0} bytes)"))
        else:
            real_files = [p for p in workspace.rglob("*") if p.is_file() and self._is_deliverable(p)] if workspace.exists() else []
            checks.append(ValidationCheck("deliverable_files", "passed" if real_files else "failed", f"{len(real_files)} deliverable files discovered"))
        if artifact_path:
            artifact = Path(artifact_path).expanduser().resolve()
            artifact_ok = artifact.is_file() and artifact.stat().st_size > 0
            checks.append(ValidationCheck("artifact_exists", "passed" if artifact_ok else "failed", str(artifact)))
            if artifact_ok and artifact.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(artifact) as zf:
                        bad = zf.testzip()
                        names = [n for n in zf.namelist() if not n.endswith("/")]
                    zip_ok = bad is None and len(names) > 0
                    checks.append(ValidationCheck("zip_integrity", "passed" if zip_ok else "failed", f"files={len(names)} bad={bad}"))
                except Exception as exc:
                    checks.append(ValidationCheck("zip_integrity", "failed", str(exc)))
        status = "passed" if all(c.status == "passed" for c in checks) else "failed"
        return ExecutionValidationReport(id=str(uuid4()), status=status, checks=checks, artifact_path=str(artifact_path) if artifact_path else None)
    def _is_deliverable(self, path: Path) -> bool:
        ignored = {"node_modules", ".git", ".venv", "__pycache__", "dist", "build"}
        if any(part in ignored for part in path.parts): return False
        return path.suffix.lower() in {".jsx", ".tsx", ".js", ".ts", ".css", ".html", ".json", ".md", ".env", ".py"}


class ArtifactDownloadVerifier:
    def manifest_for_zip(self, zip_path: str | Path) -> dict[str, Any]:
        path = Path(zip_path).expanduser().resolve()
        if not path.is_file(): raise FileNotFoundError(f"Artifact does not exist: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        entries: list[dict[str, Any]] = []
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad: raise ValueError(f"ZIP failed integrity check at {bad}")
            for info in zf.infolist():
                if not info.is_dir(): entries.append({"path": info.filename, "size": info.file_size, "compressed_size": info.compress_size})
        if not entries: raise ValueError("ZIP artifact is empty")
        return {"filename": path.name, "path": str(path), "size": path.stat().st_size, "sha256": digest.hexdigest(), "file_count": len(entries), "files": entries, "verified_at": _now()}


@dataclass(slots=True)
class PreviewProcess:
    id: str
    workspace: str
    command: str
    port: int
    url: str
    status: str
    pid: int | None = None
    log_path: str | None = None
    started_at: str = field(default_factory=_now)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


class LivePreviewManager:
    def __init__(self) -> None:
        self.runtime_root = Path(os.getenv("ISE_AI_RUNTIME_ROOT", Path.home() / ".cache" / "ise_ai" / "runtime"))
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._previews: dict[str, PreviewProcess] = {}
    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0)); return int(sock.getsockname()[1])
    def start(self, workspace: str | Path, subdir: str = "frontend") -> PreviewProcess:
        workspace = Path(workspace).expanduser().resolve()
        project = (workspace / subdir).resolve() if subdir else workspace
        if not project.exists(): raise FileNotFoundError(f"Preview directory not found: {project}")
        if not (project / "package.json").is_file(): raise FileNotFoundError(f"package.json not found for preview: {project / 'package.json'}")
        preview_id = str(uuid4()); port = self._free_port()
        log_path = self.runtime_root / "preview-logs" / f"{preview_id}.log"; log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)]
        handle = log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(cmd, cwd=project, stdout=handle, stderr=subprocess.STDOUT)
        record = PreviewProcess(id=preview_id, workspace=str(project), command=" ".join(cmd), port=port, url=f"http://127.0.0.1:{port}", status="starting", pid=process.pid, log_path=str(log_path))
        self._previews[preview_id] = record
        time.sleep(0.4); record.status = "running" if process.poll() is None else "failed"
        return record
    def list(self) -> list[dict[str, Any]]: return [self.refresh(item.id).to_dict() for item in self._previews.values()]
    def refresh(self, preview_id: str) -> PreviewProcess:
        record = self._previews[preview_id]
        if record.pid:
            try:
                os.kill(record.pid, 0)
                if record.status == "starting": record.status = "running"
            except OSError:
                if record.status not in {"stopped", "failed"}: record.status = "stopped"
        return record
    def stop(self, preview_id: str) -> bool:
        record = self._previews.get(preview_id)
        if not record: return False
        if record.pid:
            try: os.kill(record.pid, 15)
            except OSError: pass
        record.status = "stopped"; return True
    def logs(self, preview_id: str, tail: int = 200) -> dict[str, Any]:
        record = self._previews.get(preview_id)
        if not record: raise KeyError(preview_id)
        log_path = Path(record.log_path or "")
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else []
        return {"preview": record.to_dict(), "lines": lines[-tail:]}


class DeploymentAssistant:
    TARGETS = {"vercel": {"command": "npx vercel --prod", "best_for": "React/Next/Vite frontend apps"}, "netlify": {"command": "npx netlify deploy --prod", "best_for": "static frontends and JAMstack sites"}, "docker": {"command": "docker build -t generated-app .", "best_for": "portable full-stack apps"}}
    def deployment_plan(self, target: str, project_dir: str | Path) -> dict[str, Any]:
        target = target.lower().strip()
        if target not in self.TARGETS: raise KeyError(target)
        project_dir = Path(project_dir).expanduser().resolve(); files = [p.name for p in project_dir.iterdir()] if project_dir.exists() else []
        return {"target": target, "project_dir": str(project_dir), "command": self.TARGETS[target]["command"], "best_for": self.TARGETS[target]["best_for"], "ready": project_dir.exists(), "detected_files": files, "next_steps": ["Review generated files and environment variables.", "Run the final build/test command locally or in CI.", f"Authenticate with {target} if required.", "Run the deployment command from the generated project directory."]}


class IntelligenceMetricsStore:
    def __init__(self) -> None:
        self.path = Path(os.getenv("ISE_AI_RUNTIME_ROOT", Path.home() / ".cache" / "ise_ai" / "runtime")) / "intelligence-metrics.jsonl"; self.path.parent.mkdir(parents=True, exist_ok=True)
    def record(self, *, task: str, success: bool, duration_seconds: float, retries: int, quality: float, artifact_id: str | None = None) -> dict[str, Any]:
        row = {"id": str(uuid4()), "task": task, "success": bool(success), "duration_seconds": round(float(duration_seconds), 2), "retries": int(retries), "quality": round(float(quality), 3), "artifact_id": artifact_id, "created_at": _now()}
        with self.path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(row) + "\n")
        return row
    def summary(self) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try: rows.append(json.loads(line))
                except Exception: continue
        if not rows: return {"runs": 0, "success_rate": None, "avg_duration_seconds": None, "avg_quality": None, "recent": []}
        return {"runs": len(rows), "success_rate": round(sum(1 for r in rows if r.get("success"))/len(rows), 3), "avg_duration_seconds": round(sum(float(r.get("duration_seconds", 0)) for r in rows)/len(rows), 2), "avg_quality": round(sum(float(r.get("quality", 0)) for r in rows)/len(rows), 3), "recent": rows[-10:]}

_preview_manager: LivePreviewManager | None = None
_metrics_store: IntelligenceMetricsStore | None = None

def get_execution_validator() -> ExecutionGuaranteeValidator: return ExecutionGuaranteeValidator()
def get_artifact_download_verifier() -> ArtifactDownloadVerifier: return ArtifactDownloadVerifier()
def get_live_preview_manager() -> LivePreviewManager:
    global _preview_manager
    if _preview_manager is None: _preview_manager = LivePreviewManager()
    return _preview_manager
def get_deployment_assistant() -> DeploymentAssistant: return DeploymentAssistant()
def get_intelligence_metrics_store() -> IntelligenceMetricsStore:
    global _metrics_store
    if _metrics_store is None: _metrics_store = IntelligenceMetricsStore()
    return _metrics_store
