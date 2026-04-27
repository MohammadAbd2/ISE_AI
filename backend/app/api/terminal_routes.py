"""
Terminal API Routes

Exposes terminal operations via REST API for:
- Running commands
- Getting command suggestions
- Error analysis
- Live terminal integration
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from app.services.terminal import get_terminal_integration

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


class RunCommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 120
    cwd: Optional[str] = None


class CommandSuggestionRequest(BaseModel):
    file_path: str
    action: str  # "run" or "test"


@router.post("/run")
async def run_command(request: RunCommandRequest):
    """Run a terminal command and return output with error analysis."""
    terminal = get_terminal_integration()
    
    output = await terminal.run_command(
        request.command,
        timeout=request.timeout or 120,
        cwd=request.cwd,
    )
    
    return {
        "success": output.return_code == 0,
        "command": output.command,
        "stdout": output.stdout[:10000],  # Limit output
        "stderr": output.stderr[:10000],
        "return_code": output.return_code,
        "duration_ms": output.duration_ms,
        "executed_at": output.executed_at,
        "cwd": output.cwd,
        "error_analysis": output.error_analysis,
        "suggested_fix": output.suggested_fix,
    }


@router.get("/run-simple")
async def run_command_simple(
    command: str = Query(..., description="Command to execute"),
    timeout: int = Query(120, ge=1, le=300, description="Timeout in seconds"),
):
    """Run a terminal command (simple GET version)."""
    terminal = get_terminal_integration()
    
    output = await terminal.run_command(command, timeout=timeout)
    
    return {
        "success": output.return_code == 0,
        "command": output.command,
        "stdout": output.stdout[:10000],
        "stderr": output.stderr[:10000],
        "return_code": output.return_code,
        "duration_ms": output.duration_ms,
        "cwd": output.cwd,
        "error_analysis": output.error_analysis,
        "suggested_fix": output.suggested_fix,
    }


@router.post("/suggest-command")
async def suggest_command(request: CommandSuggestionRequest):
    """Get appropriate command to run or test a file."""
    terminal = get_terminal_integration()
    
    if request.action == "run":
        command = terminal.get_run_command(request.file_path)
    elif request.action == "test":
        command = terminal.get_test_command()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    
    return {
        "success": True,
        "command": command,
        "action": request.action,
        "file_path": request.file_path,
    }


@router.get("/allowed-commands")
async def get_allowed_commands():
    """Get list of allowed commands."""
    terminal = get_terminal_integration()
    
    return {
        "success": True,
        "allowed_commands": sorted(list(terminal.allowed_commands)),
        "blocked_patterns": terminal.blocked_patterns,
    }
