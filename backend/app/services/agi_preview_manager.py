from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import socket
from typing import Any

@dataclass
class PreviewState:
    available: bool
    status: str
    url: str
    port: int | None
    cwd: str
    command: str
    reason: str
    controls: dict[str, bool]

    def to_dict(self):
        return asdict(self)

class PreviewManager:
    def find_free_port(self, preferred: int | None = None) -> int:
        candidates = [preferred] if preferred else []
        candidates += [5174, 5175, 5176, 5177, 4173, 4174, 3000, 3001]
        for port in [p for p in candidates if p]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(("127.0.0.1", int(port))) != 0:
                    return int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            return int(sock.getsockname()[1])

    def create(self, sandbox: str | Path, *, base_url: str | None = None, preferred_port: int | None = None) -> PreviewState:
        root = Path(sandbox)
        frontend = root / "frontend"
        if not frontend.exists():
            return PreviewState(False, "unavailable", "", None, "", "", "No frontend folder exists for browser preview.", {"restart": False, "stop": False})
        port = self.find_free_port(preferred_port)
        base = (base_url or os.getenv("PREVIEW_BASE_URL") or f"http://127.0.0.1:{port}").rstrip("/")
        # If caller gave origin like http://localhost:5173, do not append fake /preview/id.
        url = base if str(port) in base else f"{base}:{port}" if base.startswith("http://127.0.0.1") or base.startswith("http://localhost") else base
        command = f"cd {frontend} && npm install && npm run dev -- --host 0.0.0.0 --port {port}"
        return PreviewState(True, "ready_to_start", url, port, str(frontend), command, "Run the command to start a real Vite preview; no fake 404 preview route is generated.", {"restart": True, "stop": True})
