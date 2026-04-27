from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.figma_agent_runtime import generate_prompt_prototype, inspect_figma_design, roadmap

router = APIRouter(prefix="/api/figma-agent", tags=["Figma Design Agent"])

class FigmaInspectRequest(BaseModel):
    url: str = Field(..., min_length=3)
    prompt: str = "Convert this Figma design into code."

class PromptPrototypeRequest(BaseModel):
    prompt: str = Field(..., min_length=3)
    title: str = "Agent prototype"

@router.get("/roadmap")
async def get_roadmap():
    return roadmap()

@router.post("/inspect")
async def inspect(payload: FigmaInspectRequest):
    return inspect_figma_design(payload.url, payload.prompt)

@router.post("/prototype")
async def prototype(payload: PromptPrototypeRequest):
    return generate_prompt_prototype(payload.prompt, payload.title)
