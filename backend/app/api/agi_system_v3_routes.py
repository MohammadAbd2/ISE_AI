from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException
from app.services.agi_system_v3 import get_agi_system_v3

router = APIRouter(prefix="/api/agi-system-v3", tags=["agi-system-v3"])

@router.get("/roadmap")
async def roadmap(): return get_agi_system_v3().roadmap()
@router.post("/reason")
async def reason(payload: dict = Body(...)): return get_agi_system_v3().plan(payload.get("task", ""), payload.get("context", {}))
@router.post("/evaluate")
async def evaluate(payload: dict = Body(...)): return get_agi_system_v3().evaluate(payload)
@router.post("/debug")
async def debug(payload: dict = Body(...)): return get_agi_system_v3().diagnose(payload.get("error", ""))
@router.post("/compress-context")
async def compress_context(payload: dict = Body(...)): return get_agi_system_v3().compressor.compress(payload.get("context", payload), int(payload.get("budget", 1200)))
@router.get("/knowledge-graph")
async def knowledge_graph(): return get_agi_system_v3().graph.summary()
@router.post("/continuous-cycle")
async def continuous_cycle(payload: dict = Body(...)): return get_agi_system_v3().loop.next_cycle(payload.get("task", ""), payload.get("last_result", {}))
@router.get("/integrations")
async def integrations(): return get_agi_system_v3().integrations.list()
@router.patch("/integrations/{name}")
async def update_integration(name: str, payload: dict = Body(...)):
    try: return get_agi_system_v3().integrations.update(name, payload)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc))
@router.post("/risk")
async def risk(payload: dict = Body(...)): return get_agi_system_v3().safety.assess(payload.get("action", ""), payload.get("policy", {}))
@router.get("/mode/{mode}")
async def mode(mode: str): return get_agi_system_v3().mode.describe(mode)
@router.post("/ui/compact-card")
async def compact_card(payload: dict = Body(...)): return get_agi_system_v3().ui.compact_card(payload)
@router.get("/control-summary")
async def control_summary(): return get_agi_system_v3().control_summary()
