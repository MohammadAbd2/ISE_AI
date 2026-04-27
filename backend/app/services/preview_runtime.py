from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PreviewSession:
    id: str
    workspace: str
    command: str
    port: int
    url: str
    status: str = "starting"
    started_at: float = field(default_factory=time.time)
    logs: list[str] = field(default_factory=list)
    install_status: str = "not_needed"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["elapsed_seconds"] = int(time.time() - self.started_at)
        return data


class PreviewRuntimeRegistry:
    """Local process manager for generated previews.

    Unlike the old preview contract, this starts a real Vite process on the local
    machine, captures logs, tracks the port, and can stop the process later.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, PreviewSession] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def allocate_port(self, preferred: int | None = None) -> int:
        candidates = [preferred] if preferred else []
        candidates += [5174, 5175, 5176, 5177, 4173, 4174, 3000, 3001]
        for port in candidates:
            if port and port != 5173 and self._port_free(port):
                return int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    def _port_free(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", int(port))) != 0

    async def start_vite_preview(self, workspace: Path, subdir: str = "frontend", preferred_port: int | None = None) -> PreviewSession:
        workspace = workspace.resolve()
        project_dir = (workspace / subdir).resolve()
        port = self.allocate_port(preferred_port)
        session = PreviewSession(
            id=str(uuid4()),
            workspace=str(project_dir),
            command=f"npm run dev -- --host 0.0.0.0 --port {port}",
            port=port,
            url=f"http://127.0.0.1:{port}",
        )
        self._sessions[session.id] = session
        if not project_dir.is_dir():
            session.status = "failed"
            session.logs.append(f"Preview directory not found: {project_dir}")
            return session
        if not (project_dir / "package.json").is_file():
            session.status = "failed"
            session.logs.append("package.json not found in preview project")
            return session
        if not (project_dir / "node_modules").exists():
            session.install_status = "running"
            install = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                out, _ = await asyncio.wait_for(install.communicate(), timeout=180)
                session.logs.extend(out.decode(errors="replace").splitlines()[-80:])
                session.install_status = "completed" if install.returncode == 0 else "failed"
                if install.returncode != 0:
                    session.status = "failed"
                    session.logs.append(f"npm install failed with exit code {install.returncode}")
                    return session
            except asyncio.TimeoutError:
                install.kill()
                session.install_status = "failed"
                session.status = "failed"
                session.logs.append("npm install timed out after 180 seconds")
                return session
        cmd = ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(session.port)]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._processes[session.id] = process
        session.status = "running"
        asyncio.create_task(self._capture_logs(session.id, process))
        await asyncio.sleep(0.8)
        if process.returncode is not None:
            session.status = "failed"
        return session

    async def _capture_logs(self, session_id: str, process: asyncio.subprocess.Process) -> None:
        session = self._sessions.get(session_id)
        if session is None or process.stdout is None:
            return
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                session.logs.append(line.decode(errors="replace").rstrip())
                session.logs[:] = session.logs[-300:]
        finally:
            if session_id in self._sessions and process.returncode is not None:
                self._sessions[session_id].status = "stopped" if process.returncode == 0 else "failed"

    def get(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        return session.to_dict() if session else None

    def list(self) -> list[dict[str, Any]]:
        return [session.to_dict() for session in self._sessions.values()]

    async def stop(self, session_id: str) -> bool:
        process = self._processes.pop(session_id, None)
        if process and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
        if session_id in self._sessions:
            self._sessions[session_id].status = "stopped"
            return True
        return False

_preview_registry = PreviewRuntimeRegistry()

def get_preview_registry() -> PreviewRuntimeRegistry:
    return _preview_registry
