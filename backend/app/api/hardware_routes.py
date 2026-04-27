"""Hardware info and model management routes."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.model_manager import get_model_manager

router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.get("/profile")
async def hardware_profile() -> dict:
    """Return detected hardware profile and recommended models."""
    mm = get_model_manager()
    return mm.get_hardware_info()


@router.get("/models")
async def available_models() -> dict:
    """Return currently configured models."""
    mm = get_model_manager()
    return {
        "default": mm.default_model,
        "coding": mm.coding_model,
        "reasoning": mm.reasoning_model,
        "fallbacks": mm.fallback_models,
        "hardware_tier": mm.hw.tier,
    }
