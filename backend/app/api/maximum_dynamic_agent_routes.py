from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.maximum_dynamic_agent import get_maximum_dynamic_agent

router = APIRouter(prefix="/api/maximum-dynamic-agent", tags=["Maximum Dynamic Agent"])


class RunRequest(BaseModel):
    request: str = Field(..., min_length=3)
    project_path: str | None = None
    export_requested: bool = True
    max_repairs: int = Field(default=5, ge=0, le=20)
    preview_base_url: str | None = None
    preview_port: int | None = Field(default=None, ge=1, le=65535)


class QuarantineRequest(BaseModel):
    project_path: str = Field(..., min_length=1)


@router.get("/roadmap")
async def roadmap():
    return get_maximum_dynamic_agent().roadmap()


@router.post("/plan")
async def plan(payload: RunRequest):
    return get_maximum_dynamic_agent().plan(payload.request, payload.project_path, payload.export_requested)


@router.post("/run")
async def run(payload: RunRequest):
    return get_maximum_dynamic_agent().run(
        payload.request,
        project_path=payload.project_path,
        export_requested=payload.export_requested,
        max_repairs=payload.max_repairs,
        preview_base_url=payload.preview_base_url,
        preview_port=payload.preview_port,
    )


@router.post("/quarantine-memory")
async def quarantine(payload: QuarantineRequest):
    return get_maximum_dynamic_agent().quarantine_memory(payload.project_path)
