from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.agentic_visual_runtime import (
    agent_panel_state,
    debug_repair_plan,
    design_from_url,
    render_contract_for_task,
    roadmap,
    save_panel_event,
    visual_capabilities,
)

from app.services.critical_agent_quality import (
    build_ide_patch,
    build_static_html_from_message,
    make_preview_result_contract,
    quality_roadmap,
    repair_plan_for_error,
)
from app.services.downloadable_files import generate_downloadable_file

router = APIRouter(prefix="/api/agentic-visual", tags=["Agentic AGI Visual Components"])

class RenderRequest(BaseModel):
    task: str = Field(..., min_length=1)
    artifacts: list[dict] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)
    data: list[dict] = Field(default_factory=list)

class DesignRequest(BaseModel):
    url: str = Field(..., min_length=3)
    prompt: str = "Create a similar website with original assets and production-ready UI."

class DebugRequest(BaseModel):
    error_text: str = Field(..., min_length=1)
    context: str = ""

class PanelEventRequest(BaseModel):
    event: dict = Field(default_factory=dict)

class StaticHtmlRequest(BaseModel):
    session_id: str = "default"
    message: str = Field(..., min_length=1)
    filename: str = "index.html"

class IdePatchRequest(BaseModel):
    file_path: str = Field(..., min_length=1)
    original_content: str = ""
    request: str = Field(..., min_length=1)

@router.get("/roadmap")
async def get_roadmap():
    return roadmap()

@router.get("/components")
async def get_components():
    return visual_capabilities()

@router.get("/panel")
async def get_panel():
    return agent_panel_state()

@router.post("/panel/event")
async def save_event(payload: PanelEventRequest):
    return save_panel_event(payload.event)

@router.post("/render-contract")
async def render_contract(payload: RenderRequest):
    return render_contract_for_task(payload.task, artifacts=payload.artifacts, images=payload.images, data=payload.data)

@router.post("/design/from-url")
async def design(payload: DesignRequest):
    return design_from_url(payload.url, payload.prompt)

@router.post("/debug/repair-plan")
async def debug(payload: DebugRequest):
    return debug_repair_plan(payload.error_text, payload.context)


@router.get("/critical-roadmap")
async def get_critical_roadmap():
    return quality_roadmap()

@router.post("/debug/self-heal")
async def debug_self_heal(payload: DebugRequest):
    return repair_plan_for_error(payload.error_text, payload.context)

@router.post("/static-html/generate")
async def static_html_generate(payload: StaticHtmlRequest):
    html = build_static_html_from_message(payload.message)
    file_info = await generate_downloadable_file(payload.session_id, payload.filename, html, ".html", payload.filename)
    contract = make_preview_result_contract(payload.filename, html, file_info)
    return {"status": "generated", "html": html, "file": file_info, "result_contract": contract, "render_blocks": contract["blocks"]}

@router.post("/ide/patch")
async def ide_patch(payload: IdePatchRequest):
    return build_ide_patch(payload.file_path, payload.original_content, payload.request)

# v11 dynamic Agent output planning: every task gets a task-specific visual/execution contract.
class DynamicOutputRequest(BaseModel):
    task: str = Field(..., min_length=1)
    artifacts: list[dict] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)
    data: list[dict] = Field(default_factory=list)

@router.post("/dynamic-output-plan")
async def dynamic_output_plan(payload: DynamicOutputRequest):
    from app.services.dynamic_output_intelligence import build_dynamic_output_plan
    return build_dynamic_output_plan(payload.task, artifacts=payload.artifacts, images=payload.images, data=payload.data)
