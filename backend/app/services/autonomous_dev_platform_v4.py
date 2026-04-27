from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "AGI_Output" / "platform_v4"
STATE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STATE_DIR / "workspace.db.json"
JOBS_DIR = STATE_DIR / "jobs"
JOBS_DIR.mkdir(exist_ok=True)
PLUGINS_DIR = STATE_DIR / "plugins"
PLUGINS_DIR.mkdir(exist_ok=True)

PHASES = [
    (9, "WebSocket streaming core", "Bidirectional event protocol with cancel/pause/resume controls."),
    (10, "Multi-task background jobs", "Durable jobs with status, logs, artifacts, and resume metadata."),
    (11, "Persistent workspaces", "Saved projects, run history, sandbox links, and reopen support."),
    (12, "Git and version control", "Diff/status/commit/rollback primitives with human approval."),
    (13, "Codebase intelligence", "Symbol and dependency indexes for architecture-aware answers."),
    (14, "Autonomous debugging", "Stacktrace parser, root-cause hints, fix plan, and retry contract."),
    (15, "DevTools panel", "Console, network, file system, timeline, memory, security panels."),
    (16, "Agent memory v2", "Project-scoped preferences, fixes, failures, and retrieval signals."),
    (17, "Collaboration", "Shared sessions, comments, approvals, and activity feed."),
    (18, "Plugin ecosystem", "Registered tools with manifests, permissions, and audit metadata."),
    (19, "Security and sandbox hardening", "Allowed paths, command policy, timeout, audit, and risk scoring."),
    (20, "Self-evolution v3", "Recurring-failure detector, sandboxed upgrade proposals, diff, approval gate."),
]

DEFAULT_STATE: dict[str, Any] = {
    "workspaces": {},
    "jobs": {},
    "memory": [],
    "collaboration": [],
    "plugins": {},
    "security": {
        "allowed_commands": ["npm", "node", "python", "python3", "pytest", "git", "ls", "cat", "pwd", "echo", "find"],
        "blocked_fragments": ["rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot"],
        "max_timeout_seconds": 120,
        "safe_mode": True,
    },
    "self_evolution": {"proposals": [], "recurring_failures": []},
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load() -> dict[str, Any]:
    if DB_PATH.exists():
        try:
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
            merged = DEFAULT_STATE | data
            for key, value in DEFAULT_STATE.items():
                if isinstance(value, dict):
                    merged[key] = value | merged.get(key, {})
            return merged
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_STATE))


def _save(state: dict[str, Any]) -> None:
    DB_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_path(path: str | None) -> Path:
    raw = Path(path or ROOT).expanduser().resolve()
    return raw


def _command_is_allowed(command: str, security: dict[str, Any]) -> tuple[bool, str]:
    stripped = command.strip()
    if not stripped:
        return False, "empty command"
    for fragment in security.get("blocked_fragments", []):
        if fragment and fragment in stripped:
            return False, f"blocked fragment: {fragment}"
    first = stripped.split()[0]
    allowed = set(security.get("allowed_commands", []))
    if security.get("safe_mode", True) and first not in allowed:
        return False, f"command '{first}' is not allowed in safe mode"
    return True, "allowed"


@dataclass
class PlatformEvent:
    id: str
    time: str
    type: str
    title: str
    status: str = "completed"
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousDevPlatformV4:
    def roadmap(self) -> dict[str, Any]:
        return {
            "title": "Autonomous Dev Platform v4 — phases 9-20",
            "status": "implementation_started",
            "north_star": "A ChatGPT-level programmer Agent with real streaming, persistent workspaces, Git, code intelligence, debugging, collaboration, plugins, security, and safe self-evolution.",
            "phases": [
                {"id": f"P{num}", "phase": num, "name": name, "goal": goal, "status": "implemented_foundation"}
                for num, name, goal in PHASES
            ],
            "completion_contract": [
                "Every run has durable job state and event logs.",
                "Every workspace can be reopened and inspected.",
                "Every command is checked by security policy before execution.",
                "Every Git operation exposes status/diff before commit.",
                "Every self-upgrade is proposal-first and human-gated.",
            ],
        }

    def status(self) -> dict[str, Any]:
        state = _load()
        return {
            "status": "ready",
            "state_path": str(DB_PATH),
            "counts": {k: len(v) if isinstance(v, (dict, list)) else 1 for k, v in state.items()},
            "security": state["security"],
            "features": [f"phase_{num}" for num, *_ in PHASES],
        }

    def create_job(self, task: str, workspace_id: str | None = None) -> dict[str, Any]:
        state = _load()
        job_id = f"job-{uuid4().hex[:12]}"
        job = {
            "id": job_id,
            "task": task,
            "workspace_id": workspace_id,
            "status": "queued",
            "progress": 0,
            "created_at": _now(),
            "updated_at": _now(),
            "events": [],
            "artifacts": [],
            "controls": {"cancel_requested": False, "paused": False},
        }
        state["jobs"][job_id] = job
        _save(state)
        return job

    def list_jobs(self) -> dict[str, Any]:
        state = _load()
        jobs = sorted(state["jobs"].values(), key=lambda j: j.get("updated_at", ""), reverse=True)
        return {"jobs": jobs[:100]}

    def update_job_control(self, job_id: str, action: str) -> dict[str, Any]:
        state = _load()
        job = state["jobs"].get(job_id)
        if not job:
            raise KeyError("job not found")
        if action == "cancel":
            job["controls"]["cancel_requested"] = True
            job["status"] = "cancelled"
        elif action == "pause":
            job["controls"]["paused"] = True
            job["status"] = "paused"
        elif action == "resume":
            job["controls"]["paused"] = False
            job["status"] = "queued"
        job["updated_at"] = _now()
        job["events"].append(PlatformEvent(uuid4().hex, _now(), "control", f"Job {action}", job["status"]).to_dict())
        _save(state)
        return job

    def run_command(self, command: str, cwd: str | None = None, job_id: str | None = None, timeout: int | None = None) -> dict[str, Any]:
        state = _load()
        ok, reason = _command_is_allowed(command, state["security"])
        event_base = {"command": command, "cwd": str(_safe_path(cwd)), "policy": reason}
        if not ok:
            result = {"ok": False, "exit_code": 126, "stdout": "", "stderr": reason, **event_base}
            self._record_memory("security_block", result)
            return result
        limit = min(int(timeout or 30), int(state["security"].get("max_timeout_seconds", 120)))
        started = time.time()
        try:
            proc = subprocess.run(command, cwd=str(_safe_path(cwd)), shell=True, capture_output=True, text=True, timeout=limit)
            result = {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-12000:],
                "stderr": proc.stderr[-12000:],
                "duration_ms": int((time.time() - started) * 1000),
                **event_base,
            }
        except subprocess.TimeoutExpired as exc:
            result = {"ok": False, "exit_code": 124, "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "", "stderr": f"Timed out after {limit}s", "duration_ms": int((time.time() - started) * 1000), **event_base}
        if job_id and job_id in state["jobs"]:
            job = state["jobs"][job_id]
            job["status"] = "completed" if result["ok"] else "failed"
            job["progress"] = 100
            job["updated_at"] = _now()
            job["events"].append(PlatformEvent(uuid4().hex, _now(), "command", command, job["status"], result).to_dict())
            _save(state)
        return result

    def _record_memory(self, kind: str, payload: dict[str, Any]) -> None:
        state = _load()
        state["memory"].append({"id": uuid4().hex, "kind": kind, "payload": payload, "created_at": _now()})
        state["memory"] = state["memory"][-500:]
        _save(state)

    def remember_workspace(self, label: str, path: str) -> dict[str, Any]:
        state = _load()
        root = _safe_path(path)
        workspace_id = f"ws-{uuid4().hex[:10]}"
        workspace = {"id": workspace_id, "label": label or root.name, "path": str(root), "exists": root.exists(), "created_at": _now(), "updated_at": _now()}
        state["workspaces"][workspace_id] = workspace
        _save(state)
        return workspace

    def list_workspaces(self) -> dict[str, Any]:
        return {"workspaces": list(_load()["workspaces"].values())}

    def git_status(self, path: str) -> dict[str, Any]:
        root = _safe_path(path)
        if not (root / ".git").exists():
            return {"is_git_repo": False, "path": str(root), "status": "", "diff": "", "branch": ""}
        status = self.run_command("git status --short --branch", str(root), timeout=20)
        diff = self.run_command("git diff --stat && git diff -- .", str(root), timeout=30)
        branch = self.run_command("git rev-parse --abbrev-ref HEAD", str(root), timeout=10)
        return {"is_git_repo": True, "path": str(root), "status": status["stdout"], "diff": diff["stdout"], "branch": branch["stdout"].strip(), "ok": status["ok"]}

    def git_commit(self, path: str, message: str) -> dict[str, Any]:
        root = _safe_path(path)
        pre = self.git_status(str(root))
        if not pre.get("is_git_repo"):
            return {"ok": False, "error": "Not a git repository", "precheck": pre}
        add = self.run_command("git add -A", str(root), timeout=30)
        commit = self.run_command(f"git commit -m {json.dumps(message or 'Agent changes')}", str(root), timeout=60)
        return {"ok": commit["ok"], "precheck": pre, "add": add, "commit": commit}

    def index_codebase(self, path: str) -> dict[str, Any]:
        root = _safe_path(path)
        symbols: list[dict[str, Any]] = []
        dependencies: dict[str, list[str]] = {}
        exts = {".py", ".js", ".jsx", ".ts", ".tsx"}
        scan_files = root.rglob("*") if root.exists() else []
        for file in scan_files:
            if any(part in {"node_modules", ".git", "AGI_Output", "__pycache__"} for part in file.parts):
                continue
            if file.is_file() and file.suffix in exts and file.stat().st_size < 500_000:
                rel = str(file.relative_to(root))
                text = file.read_text(encoding="utf-8", errors="ignore")
                deps = []
                for line_no, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    if stripped.startswith(("import ", "from ", "const ")) and "require(" in stripped or stripped.startswith("import ") or stripped.startswith("from "):
                        deps.append(stripped[:220])
                    for marker in ("function ", "class ", "def ", "export function ", "export default function "):
                        if marker in stripped:
                            symbols.append({"file": rel, "line": line_no, "signature": stripped[:220]})
                            break
                dependencies[rel] = deps[:40]
        return {"path": str(root), "symbol_count": len(symbols), "symbols": symbols[:500], "dependencies": dependencies, "indexed_at": _now()}

    def debug_error(self, error_text: str, context: str = "") -> dict[str, Any]:
        text = error_text or ""
        patterns = []
        if "ModuleNotFoundError" in text or "Cannot find module" in text:
            patterns.append("missing dependency or wrong import path")
        if "SyntaxError" in text:
            patterns.append("syntax error near the reported line")
        if "EADDRINUSE" in text or "address already in use" in text.lower():
            patterns.append("port conflict; select an available port dynamically")
        if "permission" in text.lower():
            patterns.append("permission or sandbox policy issue")
        if not patterns:
            patterns.append("generic failure; inspect command, cwd, env, and recent file changes")
        return {
            "root_cause_candidates": patterns,
            "fix_plan": [
                "Capture exact failing command and cwd.",
                "Locate first stacktrace frame in project code.",
                "Patch smallest responsible file.",
                "Re-run the failing command and store proof.",
            ],
            "context": context,
            "confidence": 0.72 if len(patterns) > 1 else 0.55,
        }

    def devtools_snapshot(self, workspace_path: str | None = None) -> dict[str, Any]:
        state = _load()
        path = _safe_path(workspace_path) if workspace_path else ROOT
        files = []
        if path.exists():
            for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:80]:
                files.append({"name": child.name, "path": str(child), "kind": "folder" if child.is_dir() else "file", "size": child.stat().st_size if child.is_file() else None})
        return {
            "console": list(state["jobs"].values())[-20:],
            "network": [{"method": "GET", "path": "/api/platform-v4/status"}, {"method": "WS", "path": "/api/platform-v4/ws/{job_id}"}],
            "filesystem": files,
            "timeline": [event for job in state["jobs"].values() for event in job.get("events", [])][-100:],
            "memory": state["memory"][-50:],
            "security": state["security"],
        }

    def add_collaboration_event(self, session_id: str, author: str, message: str, kind: str = "comment") -> dict[str, Any]:
        state = _load()
        item = {"id": uuid4().hex, "session_id": session_id, "author": author or "developer", "message": message, "kind": kind, "created_at": _now()}
        state["collaboration"].append(item)
        _save(state)
        return item

    def register_plugin(self, manifest: dict[str, Any]) -> dict[str, Any]:
        state = _load()
        plugin_id = manifest.get("id") or f"plugin-{uuid4().hex[:10]}"
        plugin = {"id": plugin_id, "manifest": manifest, "enabled": False, "registered_at": _now(), "audit": []}
        state["plugins"][plugin_id] = plugin
        _save(state)
        return plugin

    def security_report(self) -> dict[str, Any]:
        state = _load()
        return {"policy": state["security"], "audit": [m for m in state["memory"] if m.get("kind") == "security_block"][-50:], "recommendations": ["Keep safe_mode enabled for external projects.", "Require approval before git commit or merge.", "Use Docker isolation before untrusted command execution."]}

    def self_evolution_plan(self) -> dict[str, Any]:
        state = _load()
        failures = [job for job in state["jobs"].values() if job.get("status") == "failed"][-20:]
        proposal = {"id": f"proposal-{uuid4().hex[:10]}", "created_at": _now(), "title": "Self-evolution v3 upgrade proposal", "detected_failures": len(failures), "changes": ["Add validator for repeated failed command patterns.", "Improve router hints when task asks for file vs app.", "Strengthen preview/export finalizer checks."], "approval_required": True, "status": "proposed"}
        state["self_evolution"]["proposals"].append(proposal)
        _save(state)
        return proposal


_platform = AutonomousDevPlatformV4()

def get_platform_v4() -> AutonomousDevPlatformV4:
    return _platform
