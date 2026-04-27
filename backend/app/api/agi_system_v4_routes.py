from __future__ import annotations

from fastapi import APIRouter, Body

from app.services.agi_system_v4 import get_agi_system_v4

router = APIRouter(prefix="/api/agi-system-v4", tags=["agi-system-v4"])


@router.get("/roadmap")
async def roadmap():
    return get_agi_system_v4().roadmap()


@router.post("/run")
async def run(payload: dict = Body(...)):
    return get_agi_system_v4().run(payload.get("task", "Improve the agent system"), payload.get("context", {}))


@router.post("/truth/ground")
async def ground(payload: dict = Body(...)):
    return get_agi_system_v4().truth.ground_claims(payload.get("claims", []), payload.get("context", {}))


@router.post("/trace")
async def trace(payload: dict = Body(...)):
    return get_agi_system_v4().execution_truth.make_trace(payload.get("run_id", "manual"), payload.get("events", []))


@router.post("/evaluate")
async def evaluate(payload: dict = Body(...)):
    return get_agi_system_v4().evals.score(payload)


@router.post("/skills/select")
async def skills(payload: dict = Body(...)):
    return get_agi_system_v4().skills.select(payload.get("task", ""))


@router.post("/adapt")
async def adapt(payload: dict = Body(...)):
    return get_agi_system_v4().adaptive.adapt(payload.get("task", ""), payload.get("observation", {}))


@router.post("/self-improve")
async def self_improve(payload: dict = Body(...)):
    return get_agi_system_v4().self_improve.propose(payload.get("history", []))


@router.post("/debate")
async def debate(payload: dict = Body(...)):
    return get_agi_system_v4().debate_engine.debate(payload.get("task", ""))


@router.get("/integrations")
async def integrations():
    return get_agi_system_v4().integrations.list()


@router.post("/certify")
async def certify(payload: dict = Body(...)):
    return get_agi_system_v4().trust.certify(payload.get("evaluation", {}), payload.get("evidence", {}), payload.get("trace", {}))


@router.get("/ownership")
async def ownership(project: str = "ISE AI"):
    return get_agi_system_v4().owner.status(project)
