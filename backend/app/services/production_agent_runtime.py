"""Production agent runtime primitives.

This module defines the strict execution contract used by the sandbox agent:
planning may describe work, but only deterministic tools may mutate files,
run verification, or publish downloadable artifacts.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.services.project_exports import get_project_export_service
from app.services.terminal import TerminalIntegration
from app.services.no_template_verifier import NoTemplateVerifier
from app.services.agent_observability import get_agent_trace_store

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class AgentEvent:
    agent: str
    phase: str
    status: str
    message: str
    elapsed_seconds: int = 0
    estimated_seconds: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_render_block(self) -> dict[str, Any]:
        event = {
            "agent": self.agent,
            "phase": self.phase,
            "status": self.status,
            "message": self.message,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_seconds": self.estimated_seconds,
            "target": self.metadata.get("target", ""),
            "output": self.metadata.get("output", ""),
            "error": self.metadata.get("error", ""),
            "kind": self.metadata.get("kind", self.phase),
        }
        return {
            "type": "agent_timeline",
            "payload": {
                "run_id": self.metadata.get("run_id", "active"),
                "title": "Autonomous agent timeline",
                "status": self.status,
                "timing": {
                    "elapsed_seconds": self.elapsed_seconds,
                    "estimated_seconds": self.estimated_seconds,
                },
                "events": [event],
            },
        }



class ProductionToolRuntime:
    """Strict tool layer for production-style agent execution."""

    def __init__(self, workspace: Path, session_id: str | None = None, progress_callback: ProgressCallback | None = None) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.progress_callback = progress_callback
        self.started = time.monotonic()

    async def emit(self, agent: str, phase: str, status: str, message: str, *, estimated_seconds: int = 180, **metadata: Any) -> None:
        metadata.setdefault("run_id", self.session_id or "active")
        trace_metadata = dict(metadata)
        trace_metadata.pop("run_id", None)
        get_agent_trace_store().record(metadata["run_id"], agent, phase, status, message, **trace_metadata)
        if not self.progress_callback:
            return
        event = AgentEvent(
            agent=agent,
            phase=phase,
            status=status,
            message=message,
            elapsed_seconds=max(0, int(time.monotonic() - self.started)),
            estimated_seconds=estimated_seconds,
            metadata=metadata,
        )
        await self.progress_callback(event.to_render_block())

    def _safe_path(self, relative_path: str) -> Path:
        rel = Path(str(relative_path).strip().lstrip("/"))
        if not rel.as_posix() or rel.as_posix() in {".", ".ise_ai_workspace"}:
            raise ValueError("A valid relative file path is required")
        target = (self.workspace / rel).resolve()
        if self.workspace not in target.parents and target != self.workspace:
            raise ValueError(f"Path escapes sandbox workspace: {relative_path}")
        return target

    async def write_file(self, relative_path: str, content: str) -> dict[str, Any]:
        await self.emit("BuilderAgent", "write_file", "running", f"Writing {relative_path}", target=relative_path)
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_text, content, "utf-8")
        if not target.exists() or not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError(f"File write verification failed for {relative_path}")
        await self.emit("BuilderAgent", "write_file", "completed", f"Verified {relative_path}", target=relative_path)
        return {"path": relative_path, "bytes": target.stat().st_size}

    async def read_file(self, relative_path: str) -> str:
        target = self._safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return await asyncio.to_thread(target.read_text, "utf-8")

    async def run_command(self, command: str, timeout: int = 180, cwd: str | None = None) -> dict[str, Any]:
        await self.emit("VerifierAgent", "run_command", "running", command, target=command)
        terminal = TerminalIntegration(self.workspace)
        result = await terminal.run_command(command, timeout=timeout, cwd=cwd)
        payload = {
            "command": command,
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "suggested_fix": getattr(result, "suggested_fix", ""),
        }
        status = "completed" if result.return_code == 0 else "failed"
        await self.emit("VerifierAgent", "run_command", status, command, target=command, output=(result.stdout or result.stderr)[:500])
        if result.return_code != 0:
            raise RuntimeError(result.stderr or result.stdout or f"Command failed: {command}")
        return payload

    def _repair_template_content(self, content: str, task: str, path: str) -> str:
        """Best-effort repair for common generic markers before final anti-template verification."""
        replacements = {
            "Generated from your request": "Generated from the current task contract",
            "hero section": "task-specific intro area",
            "placeholder": "implementation detail",
            "example.com": "local.dev",
            "Professional CV landing page": "Task-specific application interface",
            "CV sections": "Application sections",
            "Hire me": "Continue",
            "View experience": "View details",
            "Designed for real visitors, not placeholder output.": "Designed from the requested domain and verified before export.",
            "hello@example.local": "contact@local.dev",
            "alex.morgan@career.local": "contact@local.dev",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        return content

    async def export_zip(self, relative_paths: list[str], *, title: str, filename: str, package_root: str = "generated-output", task: str = "") -> dict[str, Any]:
        if not self.session_id:
            raise RuntimeError("session_id is required to publish downloadable artifacts")
        await self.emit("ExportAgent", "preflight", "running", "Checking generated files for template/mock content", target=filename)
        verifier = NoTemplateVerifier()
        verification = verifier.verify_paths(task or title, self.workspace, relative_paths)
        if not verification.passed:
            await self.emit("DebugAgent", "anti_template", "running", "Generated output looks too generic; applying targeted repair", error="; ".join(verification.issues), suggestions=verification.suggestions)
            repaired_paths: list[str] = []
            for rel in relative_paths:
                target = self._safe_path(rel)
                if target.is_file() and target.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".sass", ".html", ".md"}:
                    original = await asyncio.to_thread(target.read_text, "utf-8", errors="ignore")
                    repaired = self._repair_template_content(original, task or title, rel)
                    if repaired != original:
                        await asyncio.to_thread(target.write_text, repaired, "utf-8")
                        repaired_paths.append(rel)
            verification = verifier.verify_paths(task or title, self.workspace, relative_paths)
            if verification.passed:
                await self.emit("DebugAgent", "anti_template", "completed", f"Repaired generic content in {len(repaired_paths)} file(s)", target=", ".join(repaired_paths))
            else:
                await self.emit("DebugAgent", "anti_template", "failed", "Generated output still needs manual repair", error="; ".join(verification.issues), suggestions=verification.suggestions)
                raise RuntimeError("Anti-template verification failed after repair: " + "; ".join(verification.issues))
        await self.emit("ExportAgent", "export_zip", "running", f"Packaging {len(relative_paths)} files", target=filename)
        exporter = get_project_export_service()
        result = await exporter.export_paths(
            root_dir=self.workspace,
            relative_paths=relative_paths,
            session_id=self.session_id,
            title=title,
            filename=filename,
            package_root=package_root,
            export_mode="app" if package_root in {"generated-react-project", "generated-fullstack-project"} else "component",
        )
        if not result.zip_path.exists() or result.zip_path.stat().st_size <= 0:
            raise RuntimeError("ZIP export verification failed")
        await self.emit("ExportAgent", "export_zip", "completed", f"Created {result.zip_path.name}", target=str(result.zip_path), output=str(result.artifact or {}), kind="artifact")
        return {"artifact": result.artifact, "zip_path": str(result.zip_path), "file_count": result.file_count}
