from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.programming_agi_runtime import get_programming_agi_runtime
from app.services.agi_tool_router import ToolRouter

router = APIRouter(prefix="/api/programming-agi", tags=["Programming AGI"])


class TaskPayload(BaseModel):
    request: str = Field(..., min_length=3)
    source_path: str | None = None
    export_zip: bool = True
    preview_base_url: str | None = None


class RememberPathPayload(BaseModel):
    label: str = Field(default="default")
    path: str = Field(..., min_length=2)


class MergePayload(BaseModel):
    run_id: str
    target_path: str


class ClearMemoryPayload(BaseModel):
    include_path_memory: bool = False


@router.get("/roadmap")
async def roadmap():
    return get_programming_agi_runtime().roadmap()


@router.get("/paths")
async def paths():
    return get_programming_agi_runtime().list_paths()


@router.post("/remember-path")
async def remember_path(payload: RememberPathPayload):
    return get_programming_agi_runtime().remember_path(payload.label, payload.path)


@router.post("/clear-stale-memory")
async def clear_stale_memory(payload: ClearMemoryPayload):
    return get_programming_agi_runtime().clear_stale_memory(payload.include_path_memory)


@router.get("/memory-context")
async def memory_context():
    return get_programming_agi_runtime().get_memory_context()


@router.post("/plan")
async def plan(payload: TaskPayload):
    return get_programming_agi_runtime().plan(payload.request, payload.source_path)


@router.post("/run")
async def run(payload: TaskPayload):
    try:
        return get_programming_agi_runtime().run(payload.request, payload.source_path, payload.export_zip, payload.preview_base_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    data = get_programming_agi_runtime().get_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return data


@router.post("/merge")
async def merge(payload: MergePayload):
    try:
        return get_programming_agi_runtime().merge(payload.run_id, payload.target_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tool-routes")
async def tool_routes(payload: TaskPayload):
    return {"routes": ToolRouter().routes_for(payload.request)}
