"""
Manus-Core Architecture Module

This module implements the core multi-agent orchestration framework for ISE_AI,
enabling it to achieve Manus-level autonomy and problem-solving capabilities.
"""

from app.services.manus_core.base_agent import (
    BaseAgent,
    AgentRole,
    Task,
    TaskStatus,
    AgentMessage,
    AgentPool
)

from app.services.manus_core.orchestrator_agent import (
    OrchestratorAgent,
    ExecutionPlan
)

from app.services.manus_core.specialized_agents import (
    CodingAgent,
    WebInteractionAgent,
    DebuggerAgent,
    PlanningAgent,
    SelfReflectionAgent
)

from app.services.manus_core.persistent_memory import (
    PersistentMemorySystem,
    MemoryEntry
)

from app.services.manus_core.self_improvement_engine import (
    SelfImprovementEngine,
    SelfImprovementAgent,
    CodePatch,
    ImprovementProposal
)

from app.services.manus_core.prompt_optimizer import (
    PromptOptimizer,
    PromptTemplate,
    PromptAnalysis
)

from app.services.manus_core.communication_protocol import (
    CommunicationBus,
    MessageRouter,
    EnhancedAgentMessage,
    MessagePriority,
    MessageStatus
)

from app.services.manus_core.response_formatter import (
    ResponseFormatter,
    ResponseType,
    IconLibrary,
    Suggestion
)

__all__ = [
    "BaseAgent",
    "AgentRole",
    "Task",
    "TaskStatus",
    "AgentMessage",
    "AgentPool",
    "OrchestratorAgent",
    "ExecutionPlan",
    "CodingAgent",
    "WebInteractionAgent",
    "DebuggerAgent",
    "PlanningAgent",
    "SelfReflectionAgent",
    "PersistentMemorySystem",
    "MemoryEntry",
    "SelfImprovementEngine",
    "SelfImprovementAgent",
    "CodePatch",
    "ImprovementProposal",
    "PromptOptimizer",
    "PromptTemplate",
    "PromptAnalysis",
    "CommunicationBus",
    "MessageRouter",
    "EnhancedAgentMessage",
    "MessagePriority",
    "MessageStatus",
    "ResponseFormatter",
    "ResponseType",
    "IconLibrary",
    "Suggestion"
]
