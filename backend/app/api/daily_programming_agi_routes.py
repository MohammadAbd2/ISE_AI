from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.daily_programming_agi import get_daily_programming_agi
from app.services.full_stack_restaurant_blueprint import build_restaurant_fullstack_files

router = APIRouter(prefix="/api/daily-programming-agi", tags=["Daily Programming AGI"])


class AnalyzeRequest(BaseModel):
    request: str = Field(..., min_length=3)


class ValidateRequest(BaseModel):
    request: str
    files: dict[str, str] = Field(default_factory=dict)


@router.get("/roadmap")
async def roadmap():
    return get_daily_programming_agi().roadmap()


@router.post("/analyze")
async def analyze(payload: AnalyzeRequest):
    agi = get_daily_programming_agi()
    spec = agi.analyze(payload.request)
    return {
        "spec": spec.to_dict(),
        "summary": f"{spec.product_type} for {spec.domain} using {', '.join(spec.stacks)}",
        "next_action": "Generate a task-specific artifact and block export until every requested stack is represented.",
    }


@router.post("/validate")
async def validate(payload: ValidateRequest):
    return get_daily_programming_agi().validate_generated_artifact(payload.request, payload.files)


@router.post("/simulate-restaurant-project")
async def simulate_restaurant_project(payload: AnalyzeRequest):
    """Returns the deterministic file contract used by the sandbox for restaurant/full-stack examples."""
    spec = get_daily_programming_agi().analyze(payload.request).to_dict()
    files = {path: content for path, content, _description in build_restaurant_fullstack_files(payload.request)}
    validation = get_daily_programming_agi().validate_generated_artifact(payload.request, files)
    return {"spec": spec, "file_count": len(files), "files": list(files), "validation": validation}
