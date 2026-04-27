from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.dynamic_agent_runtime import get_dynamic_agent_runtime

router = APIRouter(prefix="/api/dynamic-agent-runtime", tags=["Dynamic Agent Runtime"])


class TaskRequest(BaseModel):
    request: str = Field(..., min_length=3)


class ValidateRequest(BaseModel):
    request: str = Field(..., min_length=3)
    files: dict[str, str] = Field(default_factory=dict)


@router.get("/roadmap")
async def roadmap():
    return get_dynamic_agent_runtime().roadmap()


@router.post("/contract")
async def contract(payload: TaskRequest):
    runtime = get_dynamic_agent_runtime()
    return runtime.create_contract(payload.request).to_dict()


@router.post("/run")
async def run(payload: TaskRequest):
    return get_dynamic_agent_runtime().run_dynamic_workflow(payload.request)


@router.post("/validate")
async def validate(payload: ValidateRequest):
    return get_dynamic_agent_runtime().validate_artifact(payload.request, payload.files)
