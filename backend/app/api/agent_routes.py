"""
Multi-Agent API Routes

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
