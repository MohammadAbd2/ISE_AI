from __future__ import annotations
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

@dataclass(slots=True)
class CommandDecision:
    allowed: bool
    command: str
    reason: str = ""
    sanitized: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)

class SecuritySandboxPolicy:
    ALLOWED_BINARIES = {"npm","node","npx","python","python3","pip","pip3","pytest","vite","playwright","git","ls","cat","pwd","mkdir","touch","cp","mv","rm","find","grep","sed","echo","zip","unzip","cd","env"}
    DENIED_TOKENS = {"sudo","su","chmod 777","chown","mkfs","dd",":(){","fork","/dev/","curl|sh","wget|sh","rm -rf /","rm -rf ~","shutdown","reboot"}
    WRITE_DENY_PARTS = {".git",".venv","node_modules","__pycache__"}
    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or Path.cwd()).expanduser().resolve(); self.workspace.mkdir(parents=True, exist_ok=True)
    def validate_command(self, command: str) -> CommandDecision:
        raw=(command or '').strip()
        if not raw: return CommandDecision(False, command, 'Empty command')
        lower=raw.lower()
        for token in self.DENIED_TOKENS:
            if token in lower: return CommandDecision(False, command, f'Denied unsafe token: {token}')
        try: parts=shlex.split(raw)
        except ValueError as exc: return CommandDecision(False, command, f'Invalid shell syntax: {exc}')
        if not parts: return CommandDecision(False, command, 'No command parsed')
        binary=Path(parts[0]).name
        if binary not in self.ALLOWED_BINARIES: return CommandDecision(False, command, f'Command not in allowlist: {binary}')
        if binary == 'rm' and '-rf' in parts and len(parts) <= 3: return CommandDecision(False, command, 'Refusing broad rm -rf command')
        return CommandDecision(True, command, sanitized=parts)
    def resolve_write_path(self, relative_path: str | Path) -> Path:
        rel=Path(str(relative_path).strip().replace('\\','/'))
        if rel.is_absolute(): raise ValueError('Absolute write paths are not allowed')
        if any(part in self.WRITE_DENY_PARTS for part in rel.parts): raise ValueError(f'Write path contains protected segment: {rel}')
        target=(self.workspace/rel).resolve()
        if not str(target).startswith(str(self.workspace)): raise ValueError('Path escapes sandbox workspace')
        target.parent.mkdir(parents=True, exist_ok=True); return target
    def file_manifest(self) -> list[dict[str, Any]]:
        return [{'path': p.relative_to(self.workspace).as_posix(), 'size': p.stat().st_size} for p in self.workspace.rglob('*') if p.is_file() and not any(part in self.WRITE_DENY_PARTS for part in p.parts)]
