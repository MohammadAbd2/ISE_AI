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

from backend.app.services.self_learning import get_learning_system, SelfLearningSystem
from backend.app.services.planning_agent import get_planning_agent, AutonomousPlanningAgent


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
