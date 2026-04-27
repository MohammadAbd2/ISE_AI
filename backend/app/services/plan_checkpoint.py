import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

CHECKPOINT_DIR = Path("backend/.ise_ai_checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _checkpoint_path(plan_id: str) -> Path:
    return CHECKPOINT_DIR / f"{plan_id}.json"


def save_checkpoint(plan: Any, plan_id: str | None = None) -> str:
    """Save a plan (ExecutionPlan-like) to disk as JSON. Returns plan_id."""
    if plan_id is None:
        plan_id = getattr(plan, "_checkpoint_id", None) or str(uuid4())
    # Build serializable representation
    data = {
        "task": getattr(plan, "task", None),
        "status": getattr(plan, "status", None),
        "current_step": getattr(plan, "current_step", None),
        "started_at": getattr(plan, "started_at", None),
        "completed_at": getattr(plan, "completed_at", None),
        "files_modified": getattr(plan, "files_modified", []),
        "errors": getattr(plan, "error", None) or getattr(plan, "errors", []),
        "steps": [],
    }
    # Include staged diffs for approval UX. Always emit the key for schema stability.
    try:
        data['staged_diffs'] = getattr(plan, 'staged_diffs', []) or []
    except Exception:
        data['staged_diffs'] = []

    steps = getattr(plan, "steps", None)
    if steps:
        for s in steps:
            try:
                data["steps"].append(s.to_dict())
            except Exception:
                # Fallback: minimal serialization
                data["steps"].append({
                    "step_number": getattr(s, "step_number", None),
                    "description": getattr(s, "description", None),
                    "action_type": getattr(s, "action_type", None),
                    "target": getattr(s, "target", None),
                })

    path = _checkpoint_path(plan_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Attach id back to plan for convenience
    try:
        setattr(plan, "_checkpoint_id", plan_id)
    except Exception:
        pass

    return plan_id


def load_checkpoint(plan_id: str) -> dict:
    path = _checkpoint_path(plan_id)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {plan_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_checkpoints() -> list[str]:
    ids = []
    for p in CHECKPOINT_DIR.glob("*.json"):
        ids.append(p.stem)
    return ids


def delete_checkpoint(plan_id: str) -> None:
    path = _checkpoint_path(plan_id)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
