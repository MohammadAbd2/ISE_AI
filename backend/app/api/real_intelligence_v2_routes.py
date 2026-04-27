from __future__ import annotations
from fastapi import APIRouter, Body
from app.services.real_intelligence_v2 import get_real_intelligence_v2

router = APIRouter(prefix="/api/real-intelligence-v2", tags=["real-intelligence-v2"])

@router.get("/roadmap")
async def roadmap(): return get_real_intelligence_v2().roadmap()
@router.get("/lifecycle")
async def lifecycle(): return get_real_intelligence_v2().lifecycle_example()
@router.get("/policy")
async def get_policy(): return get_real_intelligence_v2().policy.get()
@router.patch("/policy")
async def update_policy(payload: dict = Body(...)): return get_real_intelligence_v2().policy.update(payload)
@router.post("/quality-check")
async def quality_check(payload: dict = Body(...)): return get_real_intelligence_v2().quality_check(payload.get("text", ""), payload.get("domain_terms", []))
@router.post("/format-result")
async def format_result(payload: dict = Body(...)):
    return get_real_intelligence_v2().formatter.format(plan=payload.get("plan", []), actions=payload.get("actions", []), files=payload.get("files", []), verification=payload.get("verification", []), result=payload.get("result", "Task complete"), artifact=payload.get("artifact"))
