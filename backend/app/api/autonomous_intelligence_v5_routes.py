from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.autonomous_intelligence_v5 import get_autonomous_intelligence_v5

router = APIRouter(prefix="/api/autonomous-v5", tags=["Autonomous Intelligence v21-v30"])

class RunRequest(BaseModel):
    task: str = Field(..., min_length=1)
    url: str | None = None

@router.get("/roadmap")
def roadmap() -> dict:
    return {
        "title": "Autonomous Intelligence Roadmap v21-v30",
        "status": "implemented_foundation",
        "goal": "Make the Agent feel like watching an AI engineer work while enforcing truth, self-repair, design intelligence, and autonomous software building.",
        "phases": [
            {"id": "P21", "name": "Execution Truth Layer", "status": "implemented"},
            {"id": "P22", "name": "Persistent Autonomous Loop", "status": "implemented"},
            {"id": "P23", "name": "Self-Improvement Engine", "status": "implemented"},
            {"id": "P24", "name": "Multi-Agent Collaboration Brain", "status": "implemented"},
            {"id": "P25", "name": "Real Web + Browser Intelligence", "status": "implemented_scaffold"},
            {"id": "P26", "name": "Advanced Design System Engine", "status": "implemented"},
            {"id": "P27", "name": "Real Dev Environment Control", "status": "implemented"},
            {"id": "P28", "name": "Reasoning Engine Upgrade", "status": "implemented"},
            {"id": "P29", "name": "Intelligence Dashboard / AI Engineer Workbench", "status": "implemented"},
            {"id": "P30", "name": "Autonomous Software Builder", "status": "implemented"},
        ],
    }

@router.post("/run")
def run(payload: RunRequest) -> dict:
    return get_autonomous_intelligence_v5().run(payload.task, payload.url)

@router.get("/status")
def status() -> dict:
    return {"status": "ready", "label": "Autonomous Agent ready", "detail": "Truth layer, engineer workbench, and v21-v30 services loaded."}
