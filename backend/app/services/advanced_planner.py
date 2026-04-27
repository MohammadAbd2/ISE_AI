"""
Advanced Planning and Orchestration Agent for ISE_AI

Provides sophisticated task planning, decomposition, and orchestration capabilities
for handling complex, multi-step problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(slots=True)
class SubTask:
    """Represents a sub-task within a plan."""

    id: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: int = 0
    actual_duration: int = 0
    assigned_tool: str | None = None
    result: str | None = None
    error: str | None = None


@dataclass(slots=True)
class ExecutionPlan:
    """Represents a complete execution plan for a complex task."""

    id: str
    goal: str
    description: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    estimated_total_duration: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    completed_at: str | None = None


class AdvancedPlanner:
    """Advanced planning agent for complex task decomposition and orchestration."""

    def __init__(self) -> None:
        self.plans: dict[str, ExecutionPlan] = {}

    def create_plan(
        self,
        goal: str,
        description: str,
        constraints: list[str] | None = None,
    ) -> ExecutionPlan:
        """Create a new execution plan."""
        from datetime import datetime
        import uuid

        plan_id = str(uuid.uuid4())
        plan = ExecutionPlan(
            id=plan_id,
            goal=goal,
            description=description,
            constraints=constraints or [],
            created_at=datetime.now().isoformat(),
        )
        self.plans[plan_id] = plan
        return plan

    def decompose_task(
        self,
        plan: ExecutionPlan,
        task_description: str,
    ) -> list[SubTask]:
        """Decompose a complex task into sub-tasks."""
        sub_tasks = []

        keywords = task_description.lower().split()
        task_types = self._classify_task_types(keywords)

        for i, task_type in enumerate(task_types):
            sub_task = SubTask(
                id=f"{plan.id}_task_{i}",
                description=self._generate_task_description(task_type, task_description),
                priority=self._determine_priority(task_type, i, len(task_types)),
                assigned_tool=self._suggest_tool(task_type),
            )
            sub_tasks.append(sub_task)

        self._resolve_dependencies(sub_tasks)
        plan.sub_tasks = sub_tasks
        plan.estimated_total_duration = sum(t.estimated_duration for t in sub_tasks)

        return sub_tasks

    def _classify_task_types(self, keywords: list[str]) -> list[str]:
        """Classify task types based on keywords."""
        task_types = []

        if any(kw in keywords for kw in ["create", "write", "generate", "build"]):
            task_types.append("code_generation")
        if any(kw in keywords for kw in ["test", "verify", "validate", "check"]):
            task_types.append("testing")
        if any(kw in keywords for kw in ["debug", "fix", "error", "issue"]):
            task_types.append("debugging")
        if any(kw in keywords for kw in ["refactor", "improve", "optimize", "clean"]):
            task_types.append("refactoring")
        if any(kw in keywords for kw in ["research", "find", "search", "analyze"]):
            task_types.append("research")
        if any(kw in keywords for kw in ["deploy", "push", "commit", "release"]):
            task_types.append("deployment")

        if not task_types:
            task_types.append("general")

        return task_types

    def _generate_task_description(self, task_type: str, original: str) -> str:
        """Generate a description for a sub-task."""
        descriptions = {
            "code_generation": f"Generate code for: {original}",
            "testing": f"Create and run tests for: {original}",
            "debugging": f"Debug and fix issues in: {original}",
            "refactoring": f"Refactor and improve: {original}",
            "research": f"Research and analyze: {original}",
            "deployment": f"Deploy and release: {original}",
            "general": f"Execute: {original}",
        }
        return descriptions.get(task_type, f"Execute: {original}")

    def _determine_priority(self, task_type: str, position: int, total: int) -> TaskPriority:
        """Determine the priority of a sub-task."""
        if task_type in ["testing", "debugging"]:
            return TaskPriority.HIGH
        if task_type in ["deployment"]:
            return TaskPriority.CRITICAL
        if position == 0:
            return TaskPriority.HIGH
        if position == total - 1:
            return TaskPriority.MEDIUM
        return TaskPriority.MEDIUM

    def _suggest_tool(self, task_type: str) -> str:
        """Suggest a tool for a task type."""
        tool_mapping = {
            "code_generation": "python_executor", # Use the new PythonExecutorTool
            "testing": "python_executor", # Can use python executor for running tests
            "debugging": "python_executor", # Can use python executor for debugging scripts
            "refactoring": "python_executor", # Can use python executor for refactoring scripts
            "research": "web_research_agent", # Use the new WebResearchTool
            "deployment": "orchestrator", # Placeholder, needs dedicated deployment tool
            "general": "orchestrator",
        }
        return tool_mapping.get(task_type, "orchestrator")

    def _resolve_dependencies(self, sub_tasks: list[SubTask]) -> None:
        """Resolve dependencies between sub-tasks."""
        for i, task in enumerate(sub_tasks):
            if i > 0:
                task.dependencies.append(sub_tasks[i - 1].id)

    def update_task_status(
        self,
        plan_id: str,
        task_id: str,
        status: TaskStatus,
        result: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Update the status of a sub-task."""
        plan = self.plans.get(plan_id)
        if not plan:
            return False

        for task in plan.sub_tasks:
            if task.id == task_id:
                task.status = status
                if result:
                    task.result = result
                if error:
                    task.error = error
                return True

        return False

    def get_next_executable_task(self, plan_id: str) -> SubTask | None:
        """Get the next task that can be executed."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None

        for task in plan.sub_tasks:
            if task.status != TaskStatus.PENDING:
                continue

            dependencies_met = all(
                any(t.id == dep_id and t.status == TaskStatus.COMPLETED for t in plan.sub_tasks)
                for dep_id in task.dependencies
            )

            if dependencies_met:
                return task

        return None

    def is_plan_complete(self, plan_id: str) -> bool:
        """Check if a plan is complete."""
        plan = self.plans.get(plan_id)
        if not plan:
            return False

        return all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for task in plan.sub_tasks)

    def get_plan_progress(self, plan_id: str) -> dict[str, Any]:
        """Get the progress of a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {}

        total = len(plan.sub_tasks)
        completed = sum(1 for t in plan.sub_tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.sub_tasks if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in plan.sub_tasks if t.status == TaskStatus.IN_PROGRESS)

        return {
            "plan_id": plan_id,
            "goal": plan.goal,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
            "status": plan.status,
        }

    def replan_on_failure(self, plan_id: str, failed_task_id: str) -> ExecutionPlan | None:
        """Replan when a task fails."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None

        failed_task = None
        for task in plan.sub_tasks:
            if task.id == failed_task_id:
                failed_task = task
                break

        if not failed_task:
            return None

        new_plan = self.create_plan(
            goal=f"Recovery plan for: {plan.goal}",
            description=f"Replanning after failure of task: {failed_task.description}",
            constraints=plan.constraints + [f"Previous failure: {failed_task.error}"],
        )

        recovery_task = SubTask(
            id=f"{new_plan.id}_recovery",
            description=f"Recover from failure: {failed_task.description}",
            priority=TaskPriority.CRITICAL,
            assigned_tool="debugger",
        )
        new_plan.sub_tasks = [recovery_task]

        return new_plan

    def export_plan(self, plan_id: str) -> dict[str, Any]:
        """Export a plan as a dictionary."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {}

        return {
            "id": plan.id,
            "goal": plan.goal,
            "description": plan.description,
            "status": plan.status.value,
            "tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "assigned_tool": task.assigned_tool,
                    "result": task.result,
                    "error": task.error,
                }
                for task in plan.sub_tasks
            ],
            "progress": self.get_plan_progress(plan_id),
        }
