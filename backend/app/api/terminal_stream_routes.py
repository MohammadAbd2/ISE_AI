"""Real-time terminal streaming API.

This module provides newline-delimited JSON streaming for commands so the
frontend can render stdout/stderr while a command is still running instead of
waiting for the whole process to finish.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import time
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/terminal", tags=["terminal-stream"])

_RUNNING: dict[str, asyncio.subprocess.Process] = {}
_ALLOWED_COMMANDS = {
    "pwd", "ls", "dir", "cat", "type", "echo", "find", "grep", "rg", "tree",
    "python", "python3", "node", "npm", "npx", "pnpm", "yarn", "pip", "pytest",
    "git", "uvicorn", "vite", "tsc", "eslint"
}
_BLOCKED_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bsudo\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bchmod\s+777\s+/",
    r"\bchown\b",
]


class StreamCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=2000)
    cwd: Optional[str] = None
    timeout: int = Field(default=120, ge=1, le=900)
    run_id: Optional[str] = None


def _json_line(event: str, **payload: object) -> bytes:
    data = {
        "event": event,
        "time": datetime.now(UTC).isoformat(),
        **payload,
    }
    return (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")


def _validate_command(command: str) -> None:
    lowered = command.lower()
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            raise HTTPException(status_code=400, detail=f"Blocked unsafe command pattern: {pattern}")
    try:
        first = shlex.split(command, posix=os.name != "nt")[0]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse command: {exc}") from exc
    executable = Path(first).name
    if executable not in _ALLOWED_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Command '{executable}' is not allowed for streaming execution")


def _resolve_cwd(cwd: Optional[str]) -> str:
    root = Path.cwd().resolve()
    requested = Path(cwd or ".").expanduser()
    if not requested.is_absolute():
        requested = (root / requested).resolve()
    else:
        requested = requested.resolve()
    if not requested.exists() or not requested.is_dir():
        raise HTTPException(status_code=400, detail=f"Working directory does not exist: {requested}")
    return str(requested)


async def _read_stream(stream: asyncio.StreamReader, name: str, queue: asyncio.Queue[bytes]) -> None:
    while True:
        chunk = await stream.readline()
        if not chunk:
            break
        text = chunk.decode("utf-8", errors="replace")
        await queue.put(_json_line(name, text=text))


async def _stream_process(request: StreamCommandRequest) -> AsyncIterator[bytes]:
    run_id = request.run_id or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    cwd = _resolve_cwd(request.cwd)
    yield _json_line("start", run_id=run_id, command=request.command, cwd=cwd, timeout=request.timeout)

    process = await asyncio.create_subprocess_shell(
        request.command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        executable="/bin/bash" if os.name != "nt" else None,
    )
    _RUNNING[run_id] = process
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    stdout_task = asyncio.create_task(_read_stream(process.stdout, "stdout", queue))  # type: ignore[arg-type]
    stderr_task = asyncio.create_task(_read_stream(process.stderr, "stderr", queue))  # type: ignore[arg-type]
    wait_task = asyncio.create_task(process.wait())

    try:
        while True:
            if wait_task.done() and queue.empty() and stdout_task.done() and stderr_task.done():
                break
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
                yield item
            except asyncio.TimeoutError:
                yield _json_line("heartbeat", run_id=run_id, elapsed_ms=int((time.perf_counter() - start) * 1000))
            if (time.perf_counter() - start) > request.timeout and process.returncode is None:
                process.kill()
                await process.wait()
                yield _json_line("stderr", text=f"\nCommand timed out after {request.timeout}s and was killed.\n")
                break
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        code = process.returncode if process.returncode is not None else await wait_task
        success = code == 0
        yield _json_line(
            "exit",
            run_id=run_id,
            success=success,
            return_code=code,
            duration_ms=int((time.perf_counter() - start) * 1000),
            cwd=cwd,
        )
    finally:
        _RUNNING.pop(run_id, None)


@router.post("/run-stream")
async def run_command_stream(request: StreamCommandRequest):
    """Run a command and stream NDJSON events: start/stdout/stderr/heartbeat/exit."""
    _validate_command(request.command)
    return StreamingResponse(_stream_process(request), media_type="application/x-ndjson")


@router.post("/runs/{run_id}/cancel")
async def cancel_streaming_run(run_id: str):
    process = _RUNNING.get(run_id)
    if not process:
        return {"success": False, "message": "Run is not active or already finished."}
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
    return {"success": True, "run_id": run_id, "message": "Run cancelled."}


@router.get("/streaming-capabilities")
async def streaming_capabilities():
    return {
        "success": True,
        "transport": "fetch-stream-ndjson",
        "events": ["start", "stdout", "stderr", "heartbeat", "exit"],
        "allowed_commands": sorted(_ALLOWED_COMMANDS),
        "blocked_patterns": _BLOCKED_PATTERNS,
        "active_runs": list(_RUNNING.keys()),
    }
