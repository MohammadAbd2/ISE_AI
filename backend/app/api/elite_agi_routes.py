from __future__ import annotations
from fastapi import APIRouter
from app.services.elite_agi_runtime import get_elite_agi_runtime

router = APIRouter(prefix="/api/elite-agent", tags=["elite-agent"])

@router.get("/roadmap")
async def elite_agent_roadmap():
    return get_elite_agi_runtime().roadmap()

@router.get("/health-contract")
async def elite_agent_health_contract():
    return get_elite_agi_runtime().health_contract()
