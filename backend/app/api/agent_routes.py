"""
Unified Agent API Routes

Provides REST endpoints for multi-agent orchestration,
task management, and agent status monitoring.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.multi_agent_orchestrator import (
    get_multi_agent_orchestrator,
    MultiAgentOrchestrator,
    AgentRole,
    AgentPriority,
    AgentTask,
)
from app.services.self_development_agent import get_self_development_agent
from app.services.iterative_agent import get_iterative_agent


router = APIRouter()


class TaskRequest(BaseModel):
    """Request model for creating a new agent task."""
    description: str = Field(..., description="Task description")
    role: Optional[AgentRole] = Field(None, description="Specific agent role to use")
    priority: AgentPriority = Field(AgentPriority.MEDIUM, description="Task priority")
    context: dict = Field(default_factory=dict, description="Additional context for the task")
    multi_agent: bool = Field(False, description="Use multi-agent workflow")


class TaskResponse(BaseModel):
    """Response model for task creation."""
    task_id: str
    status: str
    result: Optional[str] = None
    used_agents: list[str] = []
    error: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    description: str
    agent_role: str
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    agent_name: str
    role: str
    active_tasks: int
    completed_tasks: int
    capabilities: list[str]



class RouteTaskRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: str = "auto"
    has_attachments: bool = False


@router.post("/api/agents/route-task")
async def route_task(payload: RouteTaskRequest):
    """Return the stable frontend/backend routing decision for a user request."""
    from app.services.agent_task_router import classify_agent_task
    return classify_agent_task(
        payload.message,
        has_attachments=payload.has_attachments,
        mode=payload.mode,
    ).to_dict()


@router.get("/api/agents/health")
async def agent_health():
    """Small health payload used by the UI before expensive agent runs."""
    from app.services.agent_memory import get_agent_memory_store
    memory_ok = True
    memory_error = ""
    try:
        get_agent_memory_store().planning_context("health", limit=1)
    except Exception as exc:
        memory_ok = False
        memory_error = str(exc)
    return {
        "status": "ok" if memory_ok else "degraded",
        "memory": {"ok": memory_ok, "error": memory_error},
        "routes": ["memory_chat", "research_chat", "vision_chat", "agent_plan_execute"],
    }
@router.post("/api/agents/execute", response_model=TaskResponse)
async def execute_with_agent(
    payload: TaskRequest,
    orchestrator: MultiAgentOrchestrator = Depends(get_multi_agent_orchestrator),
):
    """
    Execute a task using the most appropriate agent or multi-agent workflow.
    """
    try:
        if payload.multi_agent:
            # Use multi-agent workflow
            result = await orchestrator.execute_multi_agent_workflow(
                payload.description,
                payload.context
            )
            
            return TaskResponse(
                task_id=f"workflow-{payload.description[:20]}",
                status="completed",
                result=result.direct_reply,
                used_agents=result.used_agents
            )
        else:
            # Use single agent routing
            result = await orchestrator.route_task(
                payload.description,
                payload.context
            )
            
            return TaskResponse(
                task_id=f"task-{payload.description[:20]}",
                status="completed",
                result=result.direct_reply,
                used_agents=result.used_agents
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/agents/iterative-execute")
async def iterative_execute(
    payload: dict,
):
    """
    Execute a task using the advanced iterative agent loop.
    """
    try:
        task = payload.get("description", payload.get("task", ""))
        session_id = payload.get("session_id")
        
        if not task:
            raise HTTPException(status_code=400, detail="Task description is required")
            
        agent = get_iterative_agent()
        result = await agent.execute_task(task, session_id)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/agents/status", response_model=list[AgentStatusResponse])
async def get_agents_status(
    orchestrator: MultiAgentOrchestrator = Depends(get_multi_agent_orchestrator),
):
    """Get status of all registered agents."""
    status = orchestrator.get_agent_status()
    
    return [
        AgentStatusResponse(
            agent_name=name,
            role=info["role"],
            active_tasks=info["active_tasks"],
            completed_tasks=info["completed_tasks"],
            capabilities=info["capabilities"]
        )
        for name, info in status.items()
    ]


@router.get("/api/agents/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    orchestrator: MultiAgentOrchestrator = Depends(get_multi_agent_orchestrator),
):
    """Get status of a specific task."""
    task = orchestrator.get_task_status(task_id)
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        description=task.description,
        agent_role=task.agent_role.value,
        created_at=task.created_at,
        completed_at=task.completed_at,
        result=str(task.result) if task.result else None,
        error=task.error
    )


@router.get("/api/agents/roles", response_model=dict)
async def get_agent_roles(
    orchestrator: MultiAgentOrchestrator = Depends(get_multi_agent_orchestrator),
):
    """Get all available agent roles and their capabilities."""
    return {
        role.value: agents
        for role, agents in orchestrator.agent_registry.items()
    }


@router.post("/api/agents/stream")
async def stream_agent_response(
    payload: TaskRequest,
    orchestrator: MultiAgentOrchestrator = Depends(get_multi_agent_orchestrator),
):
    """
    Stream agent responses (for future implementation).
    This will enable real-time progress updates.
    """
    # TODO: Implement streaming
    raise HTTPException(status_code=501, detail="Streaming not yet implemented")


# Self-Development Endpoints

class SelfImprovementRequest(BaseModel):
    """Request for self-improvement."""
    description: str = Field(..., description="What to improve/add")
    improvement_type: str = Field("auto", description="Type: new_skill, enhance_skill, add_tool, fix_issue, or auto")


class SelfImprovementResponse(BaseModel):
    """Response for self-improvement request."""
    task_id: str
    status: str
    description: str
    implementation_plan: str = ""
    code_changes: list[str] = []
    test_results: str = ""
    error: Optional[str] = None


@router.post("/api/agents/self-improve", response_model=SelfImprovementResponse)
async def self_improve(
    payload: SelfImprovementRequest,
):
    """
    Request the AI to improve itself by adding new capabilities.
    """
    try:
        from app.services.self_development_agent import SelfImprovementTask
        from datetime import UTC, datetime
        
        dev_agent = get_self_development_agent()
        
        task = SelfImprovementTask(
            task_id=f"self-improve-{datetime.now(UTC).isoformat()}",
            improvement_type=payload.improvement_type,
            description=payload.description,
            user_request=payload.description
        )
        
        result = await dev_agent.implement_improvement(task)
        
        return SelfImprovementResponse(
            task_id=result.task_id,
            status=result.status,
            description=result.description,
            implementation_plan=result.implementation_plan[:500] if result.implementation_plan else "",
            code_changes=result.code_changes,
            test_results=result.test_results[:500] if result.test_results else "",
            error=result.error
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/agents/self-improve/status")
async def get_self_improvement_status():
    """Get the current self-improvement status and capabilities."""
    try:
        dev_agent = get_self_development_agent()
        return dev_agent.get_improvement_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/agents/learn-from-feedback")
async def learn_from_feedback(
    payload: dict,
):
    """
    Teach the AI from user feedback.
    
    Payload:
    - user_message: Original user request
    - ai_response: AI's response
    - feedback: User's feedback on what was wrong/inadequate
    """
    try:
        dev_agent = get_self_development_agent()
        
        user_message = payload.get("user_message", "")
        ai_response = payload.get("ai_response", "")
        feedback = payload.get("feedback", "")
        
        if not all([user_message, ai_response, feedback]):
            raise HTTPException(status_code=400, detail="Missing required fields: user_message, ai_response, feedback")
        
        result = await dev_agent.learn_from_feedback(user_message, ai_response, feedback)
        
        return {
            "status": "success",
            "message": "AI learned from your feedback",
            "learning": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Unified Agent endpoint: planner + memory + execution + verification evidence.
class PlanExecuteRequest(BaseModel):
    request: str = Field(..., min_length=3)
    source_path: Optional[str] = None
    export_zip: bool = True
    preview_base_url: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/api/agents/plan-and-execute")
async def plan_and_execute(payload: PlanExecuteRequest):
    """Plan with the multi-agent layer, enrich with Chroma memory, then execute with Programming AGI.

    This gives the frontend one stable endpoint for coding/self-improvement tasks instead of
    deciding between chat, AGI, and agent APIs on its own.
    """
    from hashlib import sha256
    from datetime import UTC, datetime
    import asyncio

    from app.services.agent_memory import get_agent_memory_store
    from app.services.agent_result_normalizer import build_ui_contract
    from app.services.critical_agent_quality import repair_plan_for_error
    from app.services.programming_agi_runtime import ROOT, get_programming_agi_runtime

    run_id = sha256(f"{payload.request}:{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:12]
    timeline = []

    def event(agent: str, status: str, message: str, progress: int, data: dict | None = None):
        timeline.append({
            "agent": agent,
            "status": status,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data or {},
        })

    try:
        event("MemoryAgent", "running", "Searching short-term and long-term ChromaDB memory", 5)
        memory = get_agent_memory_store().planning_context(payload.request, limit=5)
        event("MemoryAgent", "completed", f"Loaded {len(memory.get('memories', []))} related runs and {len(memory.get('lessons', []))} lessons", 15, memory)

        runtime = get_programming_agi_runtime()
        effective_source_path = payload.source_path
        lower_request = payload.request.lower()
        if not effective_source_path and any(token in lower_request for token in ("yourself", "your self", "this app", "this project", "develop your", "improve your")):
            effective_source_path = str(ROOT)
            event("ProjectAgent", "completed", "Defaulted self-development request to the current project root", 20, {"source_path": effective_source_path})
        event("PlannerAgent", "running", "Creating an execution contract and safe implementation plan", 25)
        plan = await asyncio.to_thread(runtime.plan, payload.request, effective_source_path)
        event("PlannerAgent", "completed", f"Prepared {len(plan.get('steps', []))} implementation steps", 40, {"steps": plan.get("steps", [])})

        event("ExecutorAgent", "running", "Executing in sandbox with verification and export evidence", 50)
        execution = await asyncio.to_thread(
            runtime.run,
            payload.request,
            effective_source_path,
            payload.export_zip,
            payload.preview_base_url,
        )
        event("ExecutorAgent", execution.get("status", "completed"), execution.get("summary", "Execution finished"), 90, {"run_id": execution.get("run_id")})

        # Start a real local preview process when a frontend preview is available.
        # The old behavior only returned a command string; this registers a
        # managed process so Open Preview works on localhost.
        preview = execution.get("preview") if isinstance(execution.get("preview"), dict) else {}
        if preview.get("available") and preview.get("cwd"):
            try:
                from pathlib import Path
                from app.services.preview_runtime import get_preview_registry
                frontend_dir = Path(preview["cwd"]).expanduser().resolve()
                started = await get_preview_registry().start_vite_preview(frontend_dir.parent, frontend_dir.name, int(preview.get("port") or 0) or None)
                execution["preview"] = {**preview, **started.to_dict(), "available": started.status == "running", "managed": True}
                event("PreviewAgent", started.status, f"Preview process {started.status} on {started.url}", 91, started.to_dict())
            except Exception as preview_exc:
                execution["preview"] = {**preview, "managed": False, "status": "failed", "error": str(preview_exc)}
                event("PreviewAgent", "warning", f"Preview process could not start: {preview_exc}", 91)

        # Register exported ZIPs as first-class downloadable artifacts so the UI can show a real Download button.
        if isinstance(execution.get("export"), dict) and execution["export"].get("path") and not execution["export"].get("artifact_id"):
            try:
                from pathlib import Path
                from app.services.artifacts import get_artifact_service
                export_path = Path(execution["export"]["path"]).expanduser().resolve()
                artifact = await get_artifact_service().create_artifact(
                    session_id=payload.session_id or "agent-session",
                    kind="project-export",
                    title=execution["export"].get("filename") or f"Agent export {execution.get('run_id', '')}",
                    content=execution.get("summary") or "Agent generated downloadable ZIP export.",
                    metadata={
                        "filename": execution["export"].get("filename") or export_path.name,
                        "download_path": str(export_path),
                        "content_type": "application/zip",
                        "file_count": execution["export"].get("file_count", 0),
                        "size_bytes": execution["export"].get("size_bytes", 0),
                        "sha256": execution["export"].get("sha256", ""),
                        "preview": execution.get("summary") or "Downloadable ZIP generated by Agent.",
                        "verified": True,
                        "source": "plan-and-execute",
                    },
                )
                execution["export"]["artifact_id"] = artifact.get("id")
                execution["export"]["download_url"] = f"/api/artifacts/{artifact.get('id')}/download"
            except Exception as artifact_exc:
                event("ArtifactAgent", "warning", f"ZIP created but artifact registration failed: {artifact_exc}", 92)
        failed = execution.get("validation", {}).get("failed", []) if isinstance(execution.get("validation"), dict) else []
        if failed:
            repair_text = "Blocked gates: " + " · ".join(map(str, failed))
            repair = repair_plan_for_error(repair_text, context="plan-and-execute verifier")
            execution.setdefault("repairs", []).append(repair)
            execution.setdefault("render_blocks", []).append(repair["render_block"])
            event("DebuggingAgent", "repairing", f"Created self-healing repair plan for: {', '.join(map(str, failed))}", 94, repair)
            if isinstance(execution.get("validation"), dict):
                execution["validation"]["self_healing_attempted"] = True
                execution["validation"]["repair_policy"] = repair.get("policy")
        success = execution.get("status") == "completed" and not failed
        summary = (
            "Agent planned the task, reused ChromaDB memory, executed it in the Programming Agent runtime, "
            f"and {'verified the result' if success else 'returned repair evidence'}.")
        get_agent_memory_store().record_run(
            task=payload.request,
            success=success,
            summary=execution.get("summary") or summary,
            files=execution.get("files") or [],
            failures=failed,
            fixes=execution.get("repairs") or [],
            artifact_id=(execution.get("export") or {}).get("artifact_id") if isinstance(execution.get("export"), dict) else None,
            metadata={"source": "plan-and-execute", "session_id": payload.session_id or ""},
        )
        event("VerifierAgent", "completed" if success else "needs_repair", "Stored run outcome in ChromaDB memory", 100)
        ui_contract = build_ui_contract(task=payload.request, plan=plan, execution=execution, timeline=timeline, memory=memory)
        if execution.get("render_blocks"):
            ui_contract.setdefault("blocks", []).extend(execution.get("render_blocks", []))
        return {
            "run_id": run_id,
            "status": "completed" if success else execution.get("status", "needs_repair"),
            "summary": summary,
            "plan_summary": "Planner → Memory → Executor → Verifier",
            "memory": memory,
            "plan": plan,
            "timeline": timeline,
            "execution": execution,
            "ui_contract": ui_contract,
        }
    except Exception as exc:
        event("Runtime", "failed", str(exc), 100)
        raise HTTPException(status_code=500, detail={"error": str(exc), "timeline": timeline}) from exc

@router.get("/api/agents/programmer-roadmap")
async def programmer_agent_roadmap():
    """Return the active roadmap for the daily programmer Agent."""
    return {
        "title": "Unified Programmer Agent Roadmap",
        "status": "implementation_started",
        "phases": [
            {"id": "P1", "name": "Stabilize chat-to-agent contract", "status": "started"},
            {"id": "P2", "name": "Frontend result workspace", "status": "started"},
            {"id": "P3", "name": "Memory everywhere", "status": "planned"},
            {"id": "P4", "name": "Vision and image understanding", "status": "planned"},
            {"id": "P5", "name": "Real implementation loop", "status": "planned"},
            {"id": "P6", "name": "Programmer daily-life tools", "status": "planned"},
            {"id": "P7", "name": "Controlled autonomy", "status": "planned"},
            {"id": "P8", "name": "Downloadable output studio", "status": "started"},
            {"id": "P9", "name": "Dynamic diagram engine", "status": "started"},
            {"id": "P10", "name": "IDE workspace bridge", "status": "started"},
            {"id": "P11", "name": "Advanced image generation and vision", "status": "started"},
            {"id": "P12", "name": "Critical routing correctness", "status": "implemented"},
            {"id": "P13", "name": "Self-healing verifier loop", "status": "implemented"},
            {"id": "P14", "name": "Visual result contract", "status": "implemented"},
            {"id": "P15", "name": "IDE write-back bridge", "status": "implemented"},
        ],
    }

@router.get("/api/agents/latest-file-location")
async def latest_file_location(filename: str = "index.html"):
    """Return likely locations of the latest generated file without launching a new Agent run."""
    from pathlib import Path
    import os
    root = Path(__file__).resolve().parents[3]
    candidates = []
    for base in [root / "generated_artifacts", root / "AGI_Output" / "sandboxes", root / "AGI_Output" / "exports", root]:
        if not base.exists():
            continue
        try:
            for path in base.rglob(filename):
                if any(part in {"node_modules", ".git", ".chroma"} for part in path.parts):
                    continue
                stat = path.stat()
                candidates.append({
                    "path": str(path),
                    "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                    "preview": path.read_text(encoding="utf-8", errors="replace")[:2000] if path.suffix.lower() in {".html", ".txt", ".md", ".js", ".jsx", ".css", ".json"} else "",
                })
        except Exception:
            continue
    candidates.sort(key=lambda item: item["modified_at"], reverse=True)
    return {
        "filename": filename,
        "found": bool(candidates),
        "locations": candidates[:20],
        "message": (f"Found {len(candidates)} matching file location(s)." if candidates else f"No generated file named {filename!r} was found in known Agent output folders."),
    }
