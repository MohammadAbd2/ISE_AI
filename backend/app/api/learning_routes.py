"""
Enhanced Routes for Self-Learning and Planning Features

Adds endpoints for:
- Self-learning system integration
- Planning agent status
- User preferences
- Learning analytics
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.services.execution_packet_history import (
    ExecutionPacketHistoryService,
    get_execution_packet_history_service,
)
from app.services.self_learning import get_learning_system, SelfLearningSystem
from app.services.self_improvement_planner import get_self_improvement_planner, SelfImprovementPlanner
from app.services.self_reflection import get_self_reflection_service, SelfReflectionService
from app.services.turn_diagnostics import get_turn_diagnostics_service, TurnDiagnosticsService
from app.services.memory_summary import get_memory_summary_service, MemorySummaryService
from app.services.planning_agent import get_planning_agent, AutonomousPlanningAgent
from app.services.promptfoo_service import get_promptfoo_service, PromptfooService
from app.services.self_upgrade_executor import SelfUpgradeExecutor


router = APIRouter()


# === Self-Learning Routes ===

class LearningStatsResponse(BaseModel):
    """Response model for learning statistics."""
    total_interactions: int = 0
    preferences_learned: int = 0
    code_styles: int = 0
    technologies: list[str] = []
    top_patterns: list[dict] = []


class UserPreference(BaseModel):
    """User preference model."""
    category: str
    preference: str
    confidence: float
    examples: list[str] = []


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""
    preferences: list[UserPreference] = []
    code_styles: dict = {}
    technologies: list[str] = []


class ResponsePreferenceRequest(BaseModel):
    style: str
    message_excerpt: str = ""


class ImprovementProposalResponse(BaseModel):
    title: str
    category: str
    priority: str
    score: float
    summary: str
    rationale: list[str] = []
    actions: list[str] = []


class ImprovementPlanResponse(BaseModel):
    overview: dict = {}
    signals: dict = {}
    proposals: list[ImprovementProposalResponse] = []


class ExecutionPacketResponse(BaseModel):
    ready: bool = False
    summary: str = ""
    subsystem: str = ""
    targets: list[str] = []
    checks: list[str] = []
    verification: list[str] = []
    steps: list[dict] = []
    agent_prompt: str = ""
    generated_at: str = ""
    packet_id: str = ""
    eval_score: float = 0.0
    max_age_minutes: int = 5
    is_stale: bool = False
    stale_reason: str = ""


class ExecutionPacketFreshnessRequest(BaseModel):
    packet_id: str = ""
    generated_at: str = ""
    ready: bool = False


class ExecutionPacketFreshnessResponse(BaseModel):
    is_stale: bool = False
    reason: str = ""
    latest_packet: ExecutionPacketResponse = ExecutionPacketResponse()


class ExecutionPacketLaunchRequest(BaseModel):
    ready: bool = False
    packet_id: str = ""
    subsystem: str = ""
    summary: str = ""
    targets: list[str] = []
    checks: list[str] = []
    verification: list[str] = []
    steps: list[dict] = []
    agent_prompt: str = ""
    generated_at: str = ""
    eval_score: float = 0.0
    session_id: str = ""


class ExecutionPacketLaunchResponse(BaseModel):
    launched_at: str = ""
    packet_id: str = ""
    subsystem: str = ""
    summary: str = ""
    targets: list[str] = []
    eval_score: float = 0.0
    session_id: str = ""
    status: str = ""
    score_delta: float = 0.0
    latest_score: float = 0.0
    eval_runs_after_launch: int = 0


class ExecutionPacketExecuteResponse(BaseModel):
    reply: str
    render_blocks: list[dict] = []
    used_agents: list[str] = []
    launch: ExecutionPacketLaunchResponse = ExecutionPacketLaunchResponse()


class TurnDiagnosticResponse(BaseModel):
    created_at: str
    message_preview: str
    mode: str
    intent_kind: str
    use_agent: bool
    used_agents: list[str] = []
    search_count: int = 0
    image_count: int = 0
    render_block_types: list[str] = []
    had_reply: bool = False


class StructuredMemoryResponse(BaseModel):
    user_memory: dict = {}
    project_memory: dict = {}
    research_memory: dict = {}
    execution_memory: dict = {}


class SelfReflectionResponse(BaseModel):
    reply: str
    render_blocks: list[dict] = []


@router.get("/api/learning/stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    learning_system: SelfLearningSystem = Depends(lambda: get_learning_system()),
) -> LearningStatsResponse:
    """Get learning statistics for the dashboard."""
    stats = await learning_system.get_learning_stats()
    
    # Convert top patterns to dicts
    top_patterns = [p.to_dict() for p in stats.get("top_patterns", [])]
    
    return LearningStatsResponse(
        total_interactions=stats.get("total_interactions", 0),
        preferences_learned=stats.get("preferences_learned", 0),
        code_styles=stats.get("code_styles", 0),
        technologies=stats.get("technologies", []),
        top_patterns=top_patterns,
    )


@router.get("/api/learning/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    learning_system: SelfLearningSystem = Depends(lambda: get_learning_system()),
) -> UserPreferencesResponse:
    """Get learned user preferences."""
    stats = await learning_system.get_learning_stats()
    
    # Convert patterns to preferences
    preferences = []
    for pattern in stats.get("top_patterns", []):
        preferences.append(UserPreference(
            category=pattern.category,
            preference=pattern.preference,
            confidence=pattern.confidence,
            examples=pattern.examples,
        ))
    
    return UserPreferencesResponse(
        preferences=preferences,
        code_styles=stats.get("code_styles", {}),
        technologies=stats.get("technologies", []),
    )


@router.post("/api/learning/track")
async def track_interaction(
    user_message: str,
    assistant_response: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
    learning_system: SelfLearningSystem = Depends(lambda: get_learning_system()),
) -> dict:
    """Track a user interaction for learning."""
    entries = await learning_system.learn_from_interaction(
        user_message=user_message,
        assistant_response=assistant_response,
        context=context or "",
        session_id=session_id,
    )
    
    return {
        "status": "tracked",
        "learned_preferences": len(entries),
        "preferences": [e.to_dict() for e in entries],
    }


@router.post("/api/learning/response-preference")
async def record_response_preference(
    payload: ResponsePreferenceRequest,
    learning_system: SelfLearningSystem = Depends(lambda: get_learning_system()),
) -> dict:
    entry = await learning_system.record_response_preference(
        style=payload.style,
        message_excerpt=payload.message_excerpt,
    )
    return {
        "status": "recorded",
        "preference": entry.preference,
        "category": entry.category,
        "confidence": entry.confidence,
    }


@router.get("/api/learning/improvement-plan", response_model=ImprovementPlanResponse)
async def get_improvement_plan(
    planner: SelfImprovementPlanner = Depends(lambda: get_self_improvement_planner()),
) -> ImprovementPlanResponse:
    report = await planner.build_plan()
    return ImprovementPlanResponse(**report)


@router.get("/api/learning/execution-packet", response_model=ExecutionPacketResponse)
async def get_execution_packet(
    planner: SelfImprovementPlanner = Depends(lambda: get_self_improvement_planner()),
) -> ExecutionPacketResponse:
    report = await planner.build_plan()
    return ExecutionPacketResponse(**report.get("signals", {}).get("execution_packet", {}))


@router.post("/api/learning/execution-packet/freshness", response_model=ExecutionPacketFreshnessResponse)
async def get_execution_packet_freshness(
    payload: ExecutionPacketFreshnessRequest,
    planner: SelfImprovementPlanner = Depends(lambda: get_self_improvement_planner()),
) -> ExecutionPacketFreshnessResponse:
    result = await planner.assess_execution_packet_freshness(payload.model_dump())
    latest_packet = ExecutionPacketResponse(**(result.get("latest_packet") or {}))
    return ExecutionPacketFreshnessResponse(
        is_stale=result.get("is_stale", False),
        reason=result.get("reason", ""),
        latest_packet=latest_packet,
    )


@router.post("/api/learning/execution-packet/launch", response_model=ExecutionPacketLaunchResponse)
async def launch_execution_packet(
    payload: ExecutionPacketLaunchRequest,
    history: ExecutionPacketHistoryService = Depends(lambda: get_execution_packet_history_service()),
) -> ExecutionPacketLaunchResponse:
    entry = history.record_launch(packet=payload.model_dump(), session_id=payload.session_id)
    return ExecutionPacketLaunchResponse(**entry)


@router.post("/api/learning/execution-packet/execute", response_model=ExecutionPacketExecuteResponse)
async def execute_execution_packet(
    payload: ExecutionPacketLaunchRequest,
    history: ExecutionPacketHistoryService = Depends(lambda: get_execution_packet_history_service()),
) -> ExecutionPacketExecuteResponse:
    entry = history.record_launch(packet=payload.model_dump(), session_id=payload.session_id)
    execution = await SelfUpgradeExecutor().execute_packet(payload.model_dump())
    return ExecutionPacketExecuteResponse(
        reply=execution.reply,
        render_blocks=execution.render_blocks,
        used_agents=execution.used_agents,
        launch=ExecutionPacketLaunchResponse(**entry),
    )


@router.get("/api/learning/execution-packet/history", response_model=list[ExecutionPacketLaunchResponse])
async def get_execution_packet_history(
    history: ExecutionPacketHistoryService = Depends(lambda: get_execution_packet_history_service()),
) -> list[ExecutionPacketLaunchResponse]:
    return [ExecutionPacketLaunchResponse(**entry) for entry in history.list_history_with_outcomes()]


@router.get("/api/learning/turn-diagnostics", response_model=list[TurnDiagnosticResponse])
async def get_turn_diagnostics(
    diagnostics: TurnDiagnosticsService = Depends(lambda: get_turn_diagnostics_service()),
) -> list[TurnDiagnosticResponse]:
    return [TurnDiagnosticResponse(**entry) for entry in diagnostics.recent()]


@router.get("/api/learning/memory-summary", response_model=StructuredMemoryResponse)
async def get_memory_summary(
    memory_summary: MemorySummaryService = Depends(lambda: get_memory_summary_service()),
) -> StructuredMemoryResponse:
    return StructuredMemoryResponse(**(await memory_summary.build_summary()))


@router.get("/api/learning/self-reflection", response_model=SelfReflectionResponse)
async def get_self_reflection(
    self_reflection: SelfReflectionService = Depends(lambda: get_self_reflection_service()),
) -> SelfReflectionResponse:
    return SelfReflectionResponse(**(await self_reflection.build_guidance()))


# === Promptfoo Routes ===

@router.post("/api/evals/run")
async def run_prompt_eval(
    prompts: list[str],
    tests: list[dict],
    providers: list[str] = ["openai:gpt-4o-mini"],
    promptfoo: PromptfooService = Depends(lambda: get_promptfoo_service()),
) -> dict:
    """Run a Promptfoo evaluation."""
    return await promptfoo.run_eval(prompts, providers, tests)


@router.get("/api/evals/history")
async def get_eval_history(
    promptfoo: PromptfooService = Depends(lambda: get_promptfoo_service()),
) -> list[dict]:
    """Get history of evaluation runs."""
    return await promptfoo.get_history()


# === Planning Agent Routes ===

class PlanRequest(BaseModel):
    """Request model for creating a plan."""
    task: str


class PlanStepResponse(BaseModel):
    """Response model for a plan step."""
    step_number: int
    description: str
    action_type: str
    target: str
    status: str
    output: str = ""
    error: str = ""


class PlanResponse(BaseModel):
    """Response model for a plan."""
    task: str
    status: str
    progress: str
    completed_steps: int
    total_steps: int
    steps: list[PlanStepResponse]


@router.post("/api/planning/create-plan", response_model=PlanResponse)
async def create_plan(
    request: PlanRequest,
    planning_agent: AutonomousPlanningAgent = Depends(lambda: get_planning_agent()),
) -> PlanResponse:
    """Create an execution plan from a task description."""
    plan = await planning_agent.create_plan(request.task)
    
    return PlanResponse(
        task=plan.task,
        status=plan.status.value,
        progress=plan.progress_text,
        completed_steps=plan.completed_steps,
        total_steps=plan.total_steps,
        steps=[
            PlanStepResponse(
                step_number=step.step_number,
                description=step.description,
                action_type=step.action_type,
                target=step.target,
                status=step.status.value,
                output=step.output,
                error=step.error,
            )
            for step in plan.steps
        ],
    )


@router.post("/api/planning/execute-plan", response_model=PlanResponse)
async def execute_plan(
    request: PlanRequest,
    planning_agent: AutonomousPlanningAgent = Depends(lambda: get_planning_agent()),
) -> PlanResponse:
    """Execute a task with full planning and progress tracking."""
    plan = await planning_agent.execute_task_with_plan(request.task)
    
    return PlanResponse(
        task=plan.task,
        status=plan.status.value,
        progress=plan.progress_text,
        completed_steps=plan.completed_steps,
        total_steps=plan.total_steps,
        steps=[
            PlanStepResponse(
                step_number=step.step_number,
                description=step.description,
                action_type=step.action_type,
                target=step.target,
                status=step.status.value,
                output=step.output,
                error=step.error,
            )
            for step in plan.steps
        ],
    )


@router.get("/api/planning/demo")
async def planning_demo() -> dict:
    """Demo endpoint showing planning capabilities."""
    return {
        "description": "Planning Agent Demo",
        "example_tasks": [
            "Create a file called text1.txt, then update the content to 'this is a text', and show me the result",
            "Create 2 files: hello.py and world.py, then run hello.py",
            "First create a React component, then add CSS styles, then show the result",
        ],
        "features": [
            "Multi-step task planning",
            "Progress tracking (0/3, 1/3, 2/3, 3/3)",
            "Autonomous execution",
            "Detailed progress logs",
            "Error handling and recovery",
        ],
    }
