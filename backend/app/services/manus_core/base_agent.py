"""
Base Agent Class for Manus-Core Architecture

This module defines the foundational agent class that all specialized agents inherit from.
Each agent has a defined role, capabilities, and communication protocol.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from datetime import datetime


class AgentRole(Enum):
    """Enumeration of agent roles in the Manus-Core architecture."""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    CODER = "coder"
    WEB_INTERACTION = "web_interaction"
    SELF_REFLECTION = "self_reflection"
    SELF_IMPROVEMENT = "self_improvement"
    DEBUGGER = "debugger"
    RESEARCH = "research"


class TaskStatus(Enum):
    """Enumeration of task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class AgentMessage:
    """Represents a message exchanged between agents."""
    sender_role: AgentRole
    recipient_role: Optional[AgentRole]
    message_type: str  # e.g., "task_request", "task_result", "query", "response"
    content: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))


@dataclass
class Task:
    """Represents a task to be executed by an agent."""
    task_id: str
    description: str
    assigned_agent: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10, where 10 is highest priority
    dependencies: list[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Manus-Core architecture.
    
    Each agent has:
    - A defined role (e.g., ORCHESTRATOR, CODER, WEB_INTERACTION)
    - A set of capabilities
    - A communication interface for inter-agent messaging
    - A task execution loop
    """

    def __init__(self, role: AgentRole, name: str, capabilities: list[str]):
        """
        Initialize a base agent.
        
        Args:
            role: The agent's role in the system
            name: A human-readable name for the agent
            capabilities: A list of capabilities this agent provides
        """
        self.role = role
        self.name = name
        self.capabilities = capabilities
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self.active_tasks: dict[str, Task] = {}
        self.completed_tasks: list[Task] = []
        self.message_history: list[AgentMessage] = []
        self.is_running = False
        self.progress_callback: Optional[Callable] = None

    async def start(self):
        """Start the agent's main loop."""
        self.is_running = True
        await self._run_loop()

    async def stop(self):
        """Stop the agent's main loop."""
        self.is_running = False

    async def _run_loop(self):
        """Main agent execution loop."""
        while self.is_running:
            try:
                # Process incoming messages
                try:
                    message = self.message_queue.get_nowait()
                    await self._handle_message(message)
                except asyncio.QueueEmpty:
                    pass

                # Process tasks
                try:
                    task = self.task_queue.get_nowait()
                    await self._execute_task(task)
                except asyncio.QueueEmpty:
                    pass

                await asyncio.sleep(0.1)
            except Exception as e:
                await self._handle_error(e)

    async def send_message(self, message: AgentMessage):
        """Send a message to another agent or broadcast."""
        self.message_history.append(message)
        # In a real implementation, this would route to the appropriate agent
        # For now, we'll just log it
        print(f"[{self.name}] Sending message to {message.recipient_role}: {message.message_type}")

    async def receive_message(self, message: AgentMessage):
        """Receive a message from another agent."""
        await self.message_queue.put(message)

    async def submit_task(self, task: Task):
        """Submit a task for execution."""
        await self.task_queue.put(task)

    async def _handle_message(self, message: AgentMessage):
        """Handle an incoming message. Override in subclasses."""
        await self._on_message(message)

    async def _execute_task(self, task: Task):
        """Execute a task. This is the main task execution method."""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        self.active_tasks[task.task_id] = task

        try:
            # Call the abstract method that subclasses implement
            result = await self.execute(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            if self.progress_callback:
                await self.progress_callback({
                    "type": "task_completed",
                    "task_id": task.task_id,
                    "agent": self.name,
                    "result": result
                })
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            
            if self.progress_callback:
                await self.progress_callback({
                    "type": "task_failed",
                    "task_id": task.task_id,
                    "agent": self.name,
                    "error": str(e)
                })

        self.completed_tasks.append(task)
        del self.active_tasks[task.task_id]

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """
        Execute a task. Must be implemented by subclasses.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of task execution
        """
        pass

    @abstractmethod
    async def _on_message(self, message: AgentMessage):
        """Handle an incoming message. Must be implemented by subclasses."""
        pass

    async def _handle_error(self, error: Exception):
        """Handle an error that occurred in the agent loop."""
        print(f"[{self.name}] Error: {str(error)}")

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the agent."""
        return {
            "name": self.name,
            "role": self.role.value,
            "is_running": self.is_running,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "capabilities": self.capabilities,
            "message_history_length": len(self.message_history)
        }


class AgentPool:
    """
    Manages a pool of agents and coordinates communication between them.
    """

    def __init__(self):
        """Initialize the agent pool."""
        self.agents: dict[AgentRole, BaseAgent] = {}
        self.message_router: dict[AgentRole, asyncio.Queue] = {}

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the pool."""
        self.agents[agent.role] = agent
        self.message_router[agent.role] = agent.message_queue

    def get_agent(self, role: AgentRole) -> Optional[BaseAgent]:
        """Get an agent by role."""
        return self.agents.get(role)

    async def broadcast_message(self, message: AgentMessage):
        """Broadcast a message to all agents."""
        for agent in self.agents.values():
            await agent.receive_message(message)

    async def send_message_to_agent(self, message: AgentMessage):
        """Send a message to a specific agent."""
        if message.recipient_role and message.recipient_role in self.agents:
            agent = self.agents[message.recipient_role]
            await agent.receive_message(message)

    async def start_all_agents(self):
        """Start all registered agents."""
        tasks = [agent.start() for agent in self.agents.values()]
        await asyncio.gather(*tasks)

    async def stop_all_agents(self):
        """Stop all registered agents."""
        for agent in self.agents.values():
            await agent.stop()

    def get_pool_status(self) -> dict[str, Any]:
        """Get the status of all agents in the pool."""
        return {
            "agents": {
                role.value: agent.get_status()
                for role, agent in self.agents.items()
            },
            "total_agents": len(self.agents)
        }
