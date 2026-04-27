"""
Orchestrator Agent for Manus-Core Architecture

The Orchestrator Agent is the central brain of the system. It:
- Understands user intent
- Decomposes complex tasks into sub-tasks
- Selects appropriate specialized agents
- Manages workflow execution
- Handles inter-agent coordination
"""

import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field

from app.services.manus_core.base_agent import (
    BaseAgent, AgentRole, Task, TaskStatus, AgentMessage
)


@dataclass
class ExecutionPlan:
    """Represents a plan for executing a complex task."""
    plan_id: str
    user_goal: str
    sub_tasks: list[Task] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)  # task_ids in order
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None

    @property
    def id(self) -> str:
        """Compatibility alias used by other plan render/export paths."""
        return self.plan_id


class OrchestratorAgent(BaseAgent):
    """
    The Orchestrator Agent is responsible for:
    1. Understanding user intent and goals
    2. Decomposing goals into actionable sub-tasks
    3. Selecting the right agents for each sub-task
    4. Managing the execution flow
    5. Aggregating results from specialized agents
    """

    def __init__(self):
        """Initialize the Orchestrator Agent."""
        super().__init__(
            role=AgentRole.ORCHESTRATOR,
            name="OrchestratorAgent",
            capabilities=[
                "intent_recognition",
                "task_decomposition",
                "agent_selection",
                "workflow_management",
                "conflict_resolution",
                "result_aggregation"
            ]
        )
        self.active_plans: dict[str, ExecutionPlan] = {}
        self.agent_pool = None  # Will be set by the system

    async def execute(self, task: Task) -> Any:
        """
        Execute a task by decomposing it and delegating to specialized agents.
        
        Args:
            task: The task to execute
            
        Returns:
            The aggregated result from all sub-tasks
        """
        # Parse the task description to understand the user's intent
        intent = await self._recognize_intent(task.description)
        
        # Decompose the task into sub-tasks
        sub_tasks = await self._decompose_task(task.description, intent)
        
        # Create an execution plan
        plan = ExecutionPlan(
            plan_id=task.task_id,
            user_goal=task.description,
            sub_tasks=sub_tasks
        )
        self.active_plans[plan.plan_id] = plan
        
        # Execute the plan
        results = await self._execute_plan(plan)
        
        return results

    async def _recognize_intent(self, user_message: str) -> dict[str, Any]:
        """
        Recognize the user's intent from their message.
        
        This is a simplified implementation. In a real system, this would use
        an LLM to understand complex intents.
        """
        intent = {
            "type": "unknown",
            "primary_action": None,
            "entities": [],
            "constraints": []
        }
        
        # Simple intent detection based on keywords
        lower_msg = user_message.lower()
        
        if any(word in lower_msg for word in ["write", "create", "generate", "code"]):
            intent["type"] = "code_generation"
            intent["primary_action"] = "generate_code"
        elif any(word in lower_msg for word in ["debug", "fix", "error", "bug"]):
            intent["type"] = "debugging"
            intent["primary_action"] = "debug_code"
        elif any(word in lower_msg for word in ["research", "find", "search", "look up"]):
            intent["type"] = "research"
            intent["primary_action"] = "web_research"
        elif any(word in lower_msg for word in ["test", "verify", "validate"]):
            intent["type"] = "testing"
            intent["primary_action"] = "run_tests"
        elif any(word in lower_msg for word in ["refactor", "improve", "optimize"]):
            intent["type"] = "refactoring"
            intent["primary_action"] = "refactor_code"
        
        return intent

    async def _decompose_task(self, user_goal: str, intent: dict[str, Any]) -> list[Task]:
        """
        Decompose a complex task into sub-tasks.
        
        Args:
            user_goal: The user's goal
            intent: The recognized intent
            
        Returns:
            A list of sub-tasks
        """
        sub_tasks = []
        task_counter = 0
        
        # Based on intent, create appropriate sub-tasks
        if intent["type"] == "code_generation":
            # For code generation, we might need: planning, coding, testing
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Plan the code structure for: {user_goal}",
                assigned_agent=AgentRole.PLANNER,
                priority=9
            ))
            task_counter += 1
            
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Generate code for: {user_goal}",
                assigned_agent=AgentRole.CODER,
                priority=9,
                dependencies=[f"task_{task_counter - 1}"]
            ))
            task_counter += 1
            
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Test the generated code",
                assigned_agent=AgentRole.CODER,
                priority=8,
                dependencies=[f"task_{task_counter - 1}"]
            ))
        
        elif intent["type"] == "debugging":
            # For debugging: analyze error, propose fix, verify
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Analyze the error: {user_goal}",
                assigned_agent=AgentRole.DEBUGGER,
                priority=10
            ))
            task_counter += 1
            
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Propose a fix",
                assigned_agent=AgentRole.DEBUGGER,
                priority=10,
                dependencies=[f"task_{task_counter - 1}"]
            ))
            task_counter += 1
            
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Verify the fix",
                assigned_agent=AgentRole.CODER,
                priority=9,
                dependencies=[f"task_{task_counter - 1}"]
            ))
        
        elif intent["type"] == "research":
            # For research: search web, synthesize information
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Research: {user_goal}",
                assigned_agent=AgentRole.RESEARCH,
                priority=8
            ))
        
        elif intent["type"] == "refactoring":
            # For refactoring: analyze code, propose improvements, implement
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Analyze code for refactoring: {user_goal}",
                assigned_agent=AgentRole.CODER,
                priority=7
            ))
            task_counter += 1
            
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=f"Implement refactoring improvements",
                assigned_agent=AgentRole.CODER,
                priority=7,
                dependencies=[f"task_{task_counter - 1}"]
            ))
        
        else:
            # Default: create a single task for the coder
            sub_tasks.append(Task(
                task_id=f"task_{task_counter}",
                description=user_goal,
                assigned_agent=AgentRole.CODER,
                priority=5
            ))
        
        return sub_tasks

    async def _execute_plan(self, plan: ExecutionPlan) -> dict[str, Any]:
        """
        Execute an execution plan by delegating tasks to specialized agents.
        
        Args:
            plan: The execution plan
            
        Returns:
            Aggregated results from all sub-tasks
        """
        results = {}
        completed_tasks = set()
        
        while len(completed_tasks) < len(plan.sub_tasks):
            for sub_task in plan.sub_tasks:
                # Check if all dependencies are completed
                if all(dep in completed_tasks for dep in sub_task.dependencies):
                    if sub_task.task_id not in completed_tasks:
                        # Delegate to the appropriate agent
                        if self.agent_pool:
                            agent = self.agent_pool.get_agent(sub_task.assigned_agent)
                            if agent:
                                await agent.submit_task(sub_task)
                                
                                # Wait for the task to complete
                                while sub_task.status == TaskStatus.IN_PROGRESS:
                                    await asyncio.sleep(0.1)
                                
                                results[sub_task.task_id] = {
                                    "status": sub_task.status.value,
                                    "result": sub_task.result,
                                    "error": sub_task.error
                                }
                                completed_tasks.add(sub_task.task_id)
                        else:
                            # If no agent pool, just mark as completed
                            sub_task.status = TaskStatus.COMPLETED
                            sub_task.result = f"Simulated execution of: {sub_task.description}"
                            results[sub_task.task_id] = {
                                "status": TaskStatus.COMPLETED.value,
                                "result": sub_task.result
                            }
                            completed_tasks.add(sub_task.task_id)
            
            await asyncio.sleep(0.1)
        
        plan.status = TaskStatus.COMPLETED
        plan.result = results
        
        return results

    async def _on_message(self, message: AgentMessage):
        """Handle incoming messages."""
        if message.message_type == "task_result":
            # Process task result from a specialized agent
            task_id = message.content.get("task_id")
            result = message.content.get("result")
            # Update the plan with the result
            print(f"[OrchestratorAgent] Received result for task {task_id}: {result}")
        elif message.message_type == "task_failed":
            # Handle task failure
            task_id = message.content.get("task_id")
            error = message.content.get("error")
            print(f"[OrchestratorAgent] Task {task_id} failed: {error}")
