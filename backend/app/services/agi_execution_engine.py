from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import time
from typing import Callable, Any

@dataclass
class StepState:
    id: str
    agent: str
    title: str
    status: str = "pending"
    command: str | None = None
    logs: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    error: str = ""
    retries: int = 0
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self):
        return asdict(self)

@dataclass
class EngineEvent:
    time: str
    type: str
    step_id: str
    agent: str
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

class ExecutionEngine:
    def __init__(self, steps: list[StepState], *, max_repairs: int = 5):
        self.steps = steps
        self.max_repairs = max_repairs
        self.events: list[EngineEvent] = []

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def emit(self, step: StepState, status: str, message: str, data: dict[str, Any] | None = None):
        self.events.append(EngineEvent(self.now(), "step:update", step.id, step.agent, status, message, data or {}))

    def progress(self) -> int:
        terminal = {"done", "failed", "blocked", "skipped"}
        return round(sum(1 for s in self.steps if s.status in terminal) / max(len(self.steps), 1) * 100)

    def run_step(self, step_id: str, fn: Callable[[], dict[str, Any] | list[str] | str | None], repair_fn: Callable[[Exception, StepState], bool] | None = None) -> dict[str, Any]:
        step = next((s for s in self.steps if s.id == step_id), None)
        if not step:
            return {}
        step.status = "running"
        step.started_at = self.now()
        self.emit(step, "running", step.title)
        while True:
            try:
                raw = fn()
                result = self.normalize(raw)
                step.status = "done"
                step.completed_at = self.now()
                step.files.extend(result.get("files", []))
                step.logs.extend(result.get("logs", []))
                self.emit(step, "done", step.title, result)
                return result
            except Exception as exc:
                step.error = str(exc)
                step.logs.append(str(exc))
                if repair_fn and step.retries < self.max_repairs:
                    step.status = "repairing"
                    step.retries += 1
                    self.emit(step, "repairing", f"{step.title}: {exc}", {"retry": step.retries})
                    fixed = repair_fn(exc, step)
                    if fixed:
                        time.sleep(0.05)
                        continue
                step.status = "failed"
                step.completed_at = self.now()
                self.emit(step, "failed", str(exc), {"retries": step.retries})
                raise

    @staticmethod
    def normalize(raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            return {"files": [str(x) for x in raw], "logs": [f"received {len(raw)} item(s)"]}
        return {"logs": [str(raw)]}


def run_command(command: str, cwd: str | Path, *, timeout: int = 120) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=Path(cwd), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return {"command": command, "return_code": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}
