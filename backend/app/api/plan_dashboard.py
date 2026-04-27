from fastapi import APIRouter, HTTPException, Body
from app.services.plan_checkpoint import load_checkpoint, list_checkpoints
from typing import Dict, Any
from datetime import datetime

router = APIRouter()


@router.get('/api/plans')
async def get_plans():
    ids = list_checkpoints()
    return {"plans": ids}


@router.get('/api/plans/pending_approvals')
async def get_pending_approvals() -> Dict[str, Any]:
    """Return list of plans that require human approval (checkpointed)."""
    ids = list_checkpoints()
    pending = []
    for pid in ids:
        try:
            data = load_checkpoint(pid)
        except Exception:
            continue
        if data.get("approved"):
            continue
        steps = data.get("steps", [])
        for idx, s in enumerate(steps):
            meta = s.get("metadata") or {}
            if meta.get("requires_approval"):
                pending.append({
                    "plan_id": pid,
                    "task": data.get("task"),
                    "step_index": idx,
                    "step_number": s.get("step_number"),
                    "step_description": s.get("description"),
                    "suggested_substeps": meta.get("suggested_substeps") or [],
                    "created_at": data.get("started_at") or data.get("created_at"),
                })
                break
    return {"pending": pending}


@router.get('/api/plans/approvals')
async def list_approvals() -> Dict[str, Any]:
    """Return an audit trail of approvals from plan checkpoints."""
    ids = list_checkpoints()
    approvals = []
    for pid in ids:
        try:
            data = load_checkpoint(pid)
        except Exception:
            continue
        if data.get('approved'):
            approvals.append({
                'plan_id': pid,
                'task': data.get('task'),
                'approved_by': data.get('approved_by'),
                'approved_at': data.get('approved_at'),
                'approved_message': data.get('approved_message'),
                'staged_diffs': data.get('staged_diffs', []),
            })
    # sort by approved_at desc
    approvals.sort(key=lambda x: x.get('approved_at') or '', reverse=True)
    return {'approvals': approvals}


@router.get('/api/plans/{plan_id}')
async def get_plan(plan_id: str):
    try:
        data = load_checkpoint(plan_id)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plan checkpoint not found")


@router.get('/api/plans/{plan_id}/progress')
async def get_plan_progress(plan_id: str) -> Dict[str, Any]:
    """Return a compact progress summary for a saved plan checkpoint."""
    try:
        data = load_checkpoint(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plan checkpoint not found")

    steps = data.get("steps", [])
    total = len(steps)
    completed = sum(1 for s in steps if (s.get("status") or "").lower() == "completed")
    progress_text = f"{completed}/{total}"

    return {
        "plan_id": plan_id,
        "task": data.get("task"),
        "status": data.get("status"),
        "progress": progress_text,
        "completed_steps": completed,
        "total_steps": total,
        "steps": steps,
    }


@router.get('/api/plans/{plan_id}/stream')
async def stream_plan_progress(plan_id: str):
    """Server-Sent Events (SSE) stream for live plan progress updates."""
    try:
        # Ensure checkpoint exists
        _ = load_checkpoint(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plan checkpoint not found")

    from fastapi import Response
    from starlette.responses import StreamingResponse
    from app.services.progress_broadcaster import subscribe
    import asyncio

    async def event_generator():
        # Subscribe to broadcaster
        async for data in subscribe(plan_id):
            # SSE format
            yield f"data: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post('/api/plans/{plan_id}/approve')
async def approve_plan(plan_id: str, payload: dict = Body(...)):
    """Approve a checkpointed plan/expansion so execution can continue.

    Expects JSON body: {"approved_by": "user", "message": "optional"}
    """
    try:
        data = load_checkpoint(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plan checkpoint not found")

    approved_by = payload.get("approved_by", "user")
    message = payload.get("message", "")

    # mark approved and persist
    data["approved"] = True
    data["approved_by"] = approved_by
    data["approved_message"] = message
    data["approved_at"] = datetime.utcnow().isoformat()
    # store accepted files (optional)
    accepted_files = payload.get('accepted_files') if isinstance(payload, dict) else None
    if accepted_files is not None:
        data['approved_files'] = accepted_files

    import json
    from app.services.plan_checkpoint import _checkpoint_path, CHECKPOINT_DIR

    path = CHECKPOINT_DIR / f"{plan_id}.json"
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save approval: {e}")

    # record audit log
    try:
        from app.services.approval_log import record_approval
        record_approval(plan_id, approved_by, message, accepted_files)
    except Exception:
        pass

    # Attempt to resume execution in a dedicated background thread.
    # Request-scoped event loops can cancel orphaned tasks before the plan completes.
    try:
        from app.services.planning_agent import AutonomousPlanningAgent
        import threading

        agent = AutonomousPlanningAgent()

        def _run() -> None:
            import asyncio
            import time

            # Give the caller a brief moment to finish any immediate state updates
            # before the resumed plan evaluates the next guarded step.
            time.sleep(0.15)
            asyncio.run(agent.execute_plan_from_checkpoint(plan_id))

        threading.Thread(target=_run, daemon=True).start()
    except Exception as e:
        # Log but don't fail the approval call
        try:
            print(f"⚠️ [PlanDashboard] Failed to start resume task: {e}")
        except Exception:
            pass

    return {"status": "approved", "plan_id": plan_id, "approved_by": approved_by, 'accepted_files': accepted_files}
