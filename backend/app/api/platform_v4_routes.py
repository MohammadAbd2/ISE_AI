from __future__ import annotations
import asyncio, json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from app.services.autonomous_dev_platform_v4 import get_platform_v4

router = APIRouter(prefix="/api/platform-v4", tags=["Autonomous Dev Platform v4"])

class JobRequest(BaseModel):
    task: str = Field(..., min_length=1)
    workspace_id: str | None = None
class ControlRequest(BaseModel):
    action: str
class CommandRequest(BaseModel):
    command: str
    cwd: str | None = None
    job_id: str | None = None
    timeout: int | None = None
class WorkspaceRequest(BaseModel):
    label: str = "default"
    path: str
class GitCommitRequest(BaseModel):
    path: str
    message: str = "Agent verified changes"
class DebugRequest(BaseModel):
    error_text: str
    context: str = ""
class CommentRequest(BaseModel):
    session_id: str = "default"
    author: str = "developer"
    message: str
    kind: str = "comment"
class PluginRequest(BaseModel):
    manifest: dict

@router.get("/roadmap")
async def roadmap(): return get_platform_v4().roadmap()
@router.get("/status")
async def status(): return get_platform_v4().status()
@router.post("/jobs")
async def create_job(payload: JobRequest): return get_platform_v4().create_job(payload.task, payload.workspace_id)
@router.get("/jobs")
async def list_jobs(): return get_platform_v4().list_jobs()
@router.post("/jobs/{job_id}/control")
async def control_job(job_id: str, payload: ControlRequest):
    try: return get_platform_v4().update_job_control(job_id, payload.action)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
@router.post("/terminal/run")
async def run_command(payload: CommandRequest): return get_platform_v4().run_command(payload.command, payload.cwd, payload.job_id, payload.timeout)
@router.post("/workspaces")
async def remember_workspace(payload: WorkspaceRequest): return get_platform_v4().remember_workspace(payload.label, payload.path)
@router.get("/workspaces")
async def list_workspaces(): return get_platform_v4().list_workspaces()
@router.get("/git/status")
async def git_status(path: str): return get_platform_v4().git_status(path)
@router.post("/git/commit")
async def git_commit(payload: GitCommitRequest): return get_platform_v4().git_commit(payload.path, payload.message)
@router.get("/codebase/index")
async def codebase_index(path: str): return get_platform_v4().index_codebase(path)
@router.post("/debug/explain")
async def debug_explain(payload: DebugRequest): return get_platform_v4().debug_error(payload.error_text, payload.context)
@router.get("/devtools")
async def devtools(path: str | None = None): return get_platform_v4().devtools_snapshot(path)
@router.post("/collaboration/comments")
async def comment(payload: CommentRequest): return get_platform_v4().add_collaboration_event(payload.session_id, payload.author, payload.message, payload.kind)
@router.post("/plugins")
async def plugin(payload: PluginRequest): return get_platform_v4().register_plugin(payload.manifest)
@router.get("/security/report")
async def security_report(): return get_platform_v4().security_report()
@router.post("/self-evolution/propose")
async def self_evolution(): return get_platform_v4().self_evolution_plan()

@router.websocket("/ws/{job_id}")
async def websocket_job_stream(ws: WebSocket, job_id: str):
    await ws.accept()
    try:
        await ws.send_json({"type": "connected", "job_id": job_id})
        for index, label in enumerate(["Thinking", "Planning", "Executing", "Verifying", "Ready"]):
            await asyncio.sleep(0.15)
            await ws.send_json({"type": "agent_event", "job_id": job_id, "step": label, "progress": min(100, (index + 1) * 25)})
        while True:
            msg = await ws.receive_text()
            try: data = json.loads(msg)
            except Exception: data = {"action": msg}
            await ws.send_json({"type": "ack", "job_id": job_id, "received": data})
    except WebSocketDisconnect:
        return
