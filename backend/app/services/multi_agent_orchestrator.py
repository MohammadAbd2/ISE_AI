"""
Multi-Agent Orchestration System

Provides a hierarchical agent architecture with specialized sub-agents
that can delegate tasks, collaborate, and share context.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Optional
from pathlib import Path

from backend.app.services.orchestrator import (
    OrchestratorResult,
    UtilityAgent,
    DocumentAgent,
    ResearchAgent,
    UrlAgent,
    ImageIntelAgent,
    ExecutionAgent,
    CapabilityAgent,
    CodingAgent,
    VideoGenerationAgent,
    ImageGenerationAgent,
)
from backend.app.services.planning_agent import get_planning_agent
from backend.app.services.intelligent_coding_agent import get_intelligent_coding_agent
from backend.app.services.intent_classifier import get_intent_classifier
from backend.app.services.artifacts import get_artifact_service
from backend.app.services.self_development_agent import get_self_development_agent, SelfImprovementTask


class AgentRole(str, Enum):
    """Role of an agent in the multi-agent system."""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    CODER = "coder"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTOR = "documentor"
    SPECIALIST = "specialist"


class AgentPriority(str, Enum):
    """Priority level for agent tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    task_id: str
    description: str
    agent_role: AgentRole
    priority: AgentPriority = AgentPriority.MEDIUM
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: str
    to_agent: str
    message_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    role: AgentRole
    description: str
    supported_intents: list[str]
    max_complexity: int = 5
    requires_context: bool = False
    can_delegate: bool = False


class BaseAgent:
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.capabilities: list[AgentCapability] = []
        self.message_queue: list[AgentMessage] = []
        self.active_tasks: list[AgentTask] = []
        self.completed_tasks: list[AgentTask] = []
        self._callbacks: list[Callable] = []
    
    def add_capability(self, capability: AgentCapability):
        self.capabilities.append(capability)
    
    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)
    
    async def notify(self, event_type: str, data: Any):
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def can_handle(self, task_description: str) -> float:
        """Return confidence score (0-1) that this agent can handle the task."""
        raise NotImplementedError
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute a task and return result."""
        raise NotImplementedError
    
    async def receive_message(self, message: AgentMessage):
        self.message_queue.append(message)
        await self.notify("message_received", message)
    
    async def process_messages(self) -> list[AgentMessage]:
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages


class PlanningAgentWrapper(BaseAgent):
    """Wrapper for the planning agent with multi-agent capabilities."""
    
    def __init__(self):
        super().__init__("planning-agent", AgentRole.PLANNER)
        self.planning_agent = get_planning_agent()
        self.add_capability(AgentCapability(
            name="task-planning",
            role=AgentRole.PLANNER,
            description="Creates detailed execution plans for complex tasks",
            supported_intents=["planning", "multi-step", "complex-task"],
            max_complexity=10,
            can_delegate=True
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        planning_indicators = [
            "plan", "steps", "first", "then", "next", "after that",
            "multi-step", "complex", "sequence", "workflow"
        ]
        if any(indicator in task_lower for indicator in planning_indicators):
            return 0.9
        return 0.3
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            project_context = task.context.get("project_context", {})
            plan = await self.planning_agent.create_plan(
                task.description,
                project_context=project_context
            )
            
            # Execute the plan
            if hasattr(self.planning_agent, 'execute_plan'):
                result = await self.planning_agent.execute_plan(plan)
            else:
                result = await self.planning_agent.execute_task_with_plan(
                    task.description,
                    project_context=project_context
                )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class CodingAgentWrapper(BaseAgent):
    """Wrapper for the intelligent coding agent."""
    
    def __init__(self):
        super().__init__("coding-agent", AgentRole.CODER)
        self.coding_agent = get_intelligent_coding_agent()
        self.add_capability(AgentCapability(
            name="code-generation",
            role=AgentRole.CODER,
            description="Generates, edits, and refactors code",
            supported_intents=["coding", "development", "implementation"],
            max_complexity=8
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        coding_indicators = [
            "create", "write", "implement", "code", "function", "class",
            "api", "endpoint", "component", "file", "script", "program"
        ]
        score = 0.0
        for indicator in coding_indicators:
            if indicator in task_lower:
                score += 0.15
        return min(score, 1.0)
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            await self.coding_agent.initialize()
            project_context = task.context.get("project_context", {})
            
            result = await self.coding_agent.execute_task(
                task.description,
                project_context=project_context
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class ResearchAgentWrapper(BaseAgent):
    """Wrapper for research capabilities."""
    
    def __init__(self):
        super().__init__("research-agent", AgentRole.RESEARCHER)
        from backend.app.services.orchestrator import ResearchAgent
        from backend.app.services.search import get_search_service
        self.research_agent = ResearchAgent(get_search_service())
        self.add_capability(AgentCapability(
            name="web-research",
            role=AgentRole.RESEARCHER,
            description="Searches web and documentation for information",
            supported_intents=["research", "search", "documentation"],
            max_complexity=6
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        research_indicators = [
            "search", "find", "research", "look up", "documentation",
            "how to", "what is", "explain", "information about"
        ]
        if any(indicator in task_lower for indicator in research_indicators):
            return 0.85
        return 0.2
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            session_id = task.context.get("session_id")
            result = await self.research_agent.run(session_id, task.description)
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class ReviewAgent(BaseAgent):
    """Agent that reviews code and plans for quality."""
    
    def __init__(self):
        super().__init__("review-agent", AgentRole.REVIEWER)
        self.add_capability(AgentCapability(
            name="code-review",
            role=AgentRole.REVIEWER,
            description="Reviews code for quality, security, and best practices",
            supported_intents=["review", "quality-check", "security-audit"],
            max_complexity=7
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        review_indicators = [
            "review", "check", "audit", "quality", "security",
            "best practices", "improve", "optimize"
        ]
        if any(indicator in task_lower for indicator in review_indicators):
            return 0.9
        return 0.3
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            # Analyze the code/context for review
            context = task.context.get("code", task.description)
            review_result = await self._review_code(context, task.context)
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = review_result
            await self.notify("task_completed", task)
            return review_result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise
    
    async def _review_code(self, code: str, context: dict) -> dict:
        """Perform code review using LLM."""
        from backend.app.services.chat import get_chat_service
        
        review_prompt = f"""Review the following code for:
1. Code quality and readability
2. Security vulnerabilities
3. Performance issues
4. Best practices
5. Potential bugs

Code:
```
{code}
```

Provide a structured review with specific issues and suggestions."""
        
        chat_service = get_chat_service()
        review_result = await chat_service.generate(
            messages=[{"role": "user", "content": review_prompt}]
        )
        
        return {
            "review": review_result,
            "issues_found": 0,  # Parse from result
            "suggestions": []
        }


class TestingAgent(BaseAgent):
    """Agent that generates and runs tests."""
    
    def __init__(self):
        super().__init__("testing-agent", AgentRole.TESTER)
        self.add_capability(AgentCapability(
            name="test-generation",
            role=AgentRole.TESTER,
            description="Generates and executes tests for code",
            supported_intents=["testing", "test-generation", "validation"],
            max_complexity=7
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        test_indicators = [
            "test", "unit test", "integration test", "validate",
            "verify", "test coverage", "write tests"
        ]
        if any(indicator in task_lower for indicator in test_indicators):
            return 0.9
        return 0.2
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            code = task.context.get("code", "")
            file_path = task.context.get("file_path", "")
            
            # Generate tests
            tests = await self._generate_tests(code, file_path)
            
            # Run tests if possible
            test_results = await self._run_tests(tests, file_path)
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = {"tests": tests, "results": test_results}
            await self.notify("task_completed", task)
            return task.result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise
    
    async def _generate_tests(self, code: str, file_path: str) -> str:
        """Generate tests for the given code."""
        from backend.app.services.chat import get_chat_service
        
        test_prompt = f"""Generate comprehensive unit tests for the following code.
File: {file_path}

Code:
```
{code}
```

Generate tests that cover:
1. Happy path scenarios
2. Edge cases
3. Error handling
4. Boundary conditions"""
        
        chat_service = get_chat_service()
        return await chat_service.generate(
            messages=[{"role": "user", "content": test_prompt}]
        )
    
    async def _run_tests(self, tests: str, file_path: str) -> dict:
        """Run the generated tests."""
        # This would integrate with test runners
        return {"status": "pending", "message": "Test execution not yet implemented"}


class DocumentationAgent(BaseAgent):
    """Agent that generates documentation."""
    
    def __init__(self):
        super().__init__("documentation-agent", AgentRole.DOCUMENTOR)
        self.add_capability(AgentCapability(
            name="doc-generation",
            role=AgentRole.DOCUMENTOR,
            description="Generates documentation for code and projects",
            supported_intents=["documentation", "docs", "readme"],
            max_complexity=6
        ))
    
    def can_handle(self, task_description: str) -> float:
        task_lower = task_description.lower()
        doc_indicators = [
            "document", "readme", "docs", "documentation",
            "comments", "explain", "describe"
        ]
        if any(indicator in task_lower for indicator in doc_indicators):
            return 0.9
        return 0.2
    
    async def execute(self, task: AgentTask) -> Any:
        task.status = "in_progress"
        try:
            code = task.context.get("code", "")
            project_context = task.context.get("project_context", {})
            
            docs = await self._generate_documentation(code, project_context, task.description)
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = docs
            await self.notify("task_completed", task)
            return docs
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise
    
    async def _generate_documentation(self, code: str, project_context: dict, request: str) -> str:
        """Generate documentation."""
        from backend.app.services.chat import get_chat_service
        
        doc_prompt = f"""Generate comprehensive documentation for the following code.

Project Context: {json.dumps(project_context, indent=2)}

Code:
```
{code}
```

Request: {request}

Generate clear, concise documentation that explains:
1. Purpose and functionality
2. Parameters and return values
3. Usage examples
4. Dependencies"""
        
        chat_service = get_chat_service()
        return await chat_service.generate(
            messages=[{"role": "user", "content": doc_prompt}]
        )


class SubAgent(BaseAgent):
    """Sub-agent that specializes in specific tasks under a parent agent."""
    
    def __init__(self, name: str, role: AgentRole, parent_agent: str, specialties: list[str]):
        super().__init__(name, role)
        self.parent_agent = parent_agent
        self.specialties = specialties  # List of specialty areas
    
    def can_handle(self, task_description: str) -> float:
        """Check if this sub-agent can handle the task based on specialties."""
        task_lower = task_description.lower()
        score = 0.0
        for specialty in self.specialties:
            if specialty.lower() in task_lower:
                score += 0.3
        return min(score, 1.0)


class PythonSubAgent(SubAgent):
    """Sub-agent specializing in Python development."""
    
    def __init__(self):
        super().__init__(
            "python-sub-agent",
            AgentRole.CODER,
            "coding-agent",
            ["python", "django", "flask", "fastapi", "asyncio", "pip"]
        )
        self.add_capability(AgentCapability(
            name="python-development",
            role=AgentRole.CODER,
            description="Specializes in Python code generation and best practices",
            supported_intents=["python", "py", "script"],
            max_complexity=9
        ))
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute Python-specific coding task."""
        task.status = "in_progress"
        try:
            from backend.app.services.intelligent_coding_agent import get_intelligent_coding_agent
            coding_agent = get_intelligent_coding_agent()
            await coding_agent.initialize()
            
            # Add Python-specific context
            task.context["language"] = "python"
            task.context["best_practices"] = [
                "PEP 8 style guide",
                "Type hints",
                "Async/await patterns",
                "Error handling with try/except"
            ]
            
            result = await coding_agent.execute_task(
                task.description,
                project_context=task.context
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class JavaScriptSubAgent(SubAgent):
    """Sub-agent specializing in JavaScript/TypeScript development."""
    
    def __init__(self):
        super().__init__(
            "javascript-sub-agent",
            AgentRole.CODER,
            "coding-agent",
            ["javascript", "typescript", "react", "node", "express", "vue", "angular"]
        )
        self.add_capability(AgentCapability(
            name="javascript-development",
            role=AgentRole.CODER,
            description="Specializes in JavaScript/TypeScript code generation",
            supported_intents=["javascript", "typescript", "js", "ts", "react", "node"],
            max_complexity=9
        ))
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute JavaScript/TypeScript coding task."""
        task.status = "in_progress"
        try:
            from backend.app.services.intelligent_coding_agent import get_intelligent_coding_agent
            coding_agent = get_intelligent_coding_agent()
            await coding_agent.initialize()
            
            # Add JS/TS-specific context
            task.context["language"] = "javascript"
            task.context["framework"] = "react" if "react" in task.description.lower() else "node"
            
            result = await coding_agent.execute_task(
                task.description,
                project_context=task.context
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class SecuritySubAgent(SubAgent):
    """Sub-agent specializing in security analysis."""
    
    def __init__(self):
        super().__init__(
            "security-sub-agent",
            AgentRole.REVIEWER,
            "review-agent",
            ["security", "vulnerability", "authentication", "authorization", "encryption", "xss", "csrf", "sql injection"]
        )
        self.add_capability(AgentCapability(
            name="security-audit",
            role=AgentRole.REVIEWER,
            description="Specializes in security vulnerability detection",
            supported_intents=["security", "vulnerability", "audit"],
            max_complexity=8
        ))
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute security review task."""
        task.status = "in_progress"
        try:
            from backend.app.services.chat import get_chat_service
            
            code = task.context.get("code", task.description)
            
            security_prompt = f"""Perform a comprehensive security audit of the following code:

```
{code}
```

Check for:
1. SQL injection vulnerabilities
2. XSS (Cross-Site Scripting) vulnerabilities
3. CSRF (Cross-Site Request Forgery) issues
4. Authentication/Authorization flaws
5. Sensitive data exposure
6. Insecure dependencies
7. Hardcoded secrets or API keys
8. Input validation issues

Provide a detailed security report with:
- Critical vulnerabilities (with severity)
- Recommended fixes
- Best practices for secure coding"""
            
            chat_service = get_chat_service()
            review_result = await chat_service.generate(
                messages=[{"role": "user", "content": security_prompt}]
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = {
                "type": "security_review",
                "review": review_result,
                "vulnerabilities_found": 0,
                "severity": "unknown"
            }
            await self.notify("task_completed", task)
            return task.result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class PerformanceSubAgent(SubAgent):
    """Sub-agent specializing in performance optimization."""
    
    def __init__(self):
        super().__init__(
            "performance-sub-agent",
            AgentRole.REVIEWER,
            "review-agent",
            ["performance", "optimization", "speed", "memory", "cpu", "bottleneck", "profiling"]
        )
        self.add_capability(AgentCapability(
            name="performance-optimization",
            role=AgentRole.REVIEWER,
            description="Specializes in performance analysis and optimization",
            supported_intents=["performance", "optimization", "speed"],
            max_complexity=8
        ))
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute performance review task."""
        task.status = "in_progress"
        try:
            from backend.app.services.chat import get_chat_service
            
            code = task.context.get("code", task.description)
            
            perf_prompt = f"""Analyze the following code for performance issues:

```
{code}
```

Check for:
1. Time complexity issues (O(n²) or worse that could be improved)
2. Memory leaks or inefficient memory usage
3. Unnecessary computations or redundant operations
4. Database query optimization (N+1 queries, missing indexes)
5. Caching opportunities
6. I/O bottlenecks
7. Algorithm improvements

Provide a detailed performance report with:
- Identified bottlenecks
- Optimization suggestions with code examples
- Expected performance improvements"""
            
            chat_service = get_chat_service()
            review_result = await chat_service.generate(
                messages=[{"role": "user", "content": perf_prompt}]
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = {
                "type": "performance_review",
                "review": review_result,
                "optimizations": []
            }
            await self.notify("task_completed", task)
            return task.result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class APISubAgent(SubAgent):
    """Sub-agent specializing in API development."""
    
    def __init__(self):
        super().__init__(
            "api-sub-agent",
            AgentRole.CODER,
            "coding-agent",
            ["api", "rest", "graphql", "endpoint", "route", "http", "webhook"]
        )
        self.add_capability(AgentCapability(
            name="api-development",
            role=AgentRole.CODER,
            description="Specializes in API design and implementation",
            supported_intents=["api", "rest", "graphql", "endpoint"],
            max_complexity=9
        ))
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute API development task."""
        task.status = "in_progress"
        try:
            from backend.app.services.intelligent_coding_agent import get_intelligent_coding_agent
            coding_agent = get_intelligent_coding_agent()
            await coding_agent.initialize()
            
            # Add API-specific context
            task.context["api_best_practices"] = [
                "RESTful design principles",
                "Proper HTTP status codes",
                "Input validation",
                "Error handling",
                "Authentication/Authorization",
                "Rate limiting",
                "API versioning"
            ]
            
            result = await coding_agent.execute_task(
                task.description,
                project_context=task.context
            )
            
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class SelfDevelopmentAgentWrapper(BaseAgent):
    """Wrapper for self-development capabilities."""
    
    def __init__(self):
        super().__init__("self-development-agent", AgentRole.SPECIALIST)
        self.development_agent = get_self_development_agent()
        self.add_capability(AgentCapability(
            name="self-improvement",
            role=AgentRole.SPECIALIST,
            description="Enables the AI to improve itself based on user requests",
            supported_intents=["add capability", "learn new", "improve yourself", "add skill"],
            max_complexity=10
        ))
    
    def can_handle(self, task_description: str) -> float:
        if self.development_agent.can_self_improve(task_description):
            return 0.95
        return 0.1
    
    async def execute(self, task: AgentTask) -> Any:
        """Execute self-improvement task."""
        task.status = "in_progress"
        try:
            from datetime import UTC, datetime
            
            # Create improvement task
            improvement_task = SelfImprovementTask(
                task_id=task.task_id,
                improvement_type="new_capability",
                description=task.description,
                user_request=task.description
            )
            
            # Implement the improvement
            result = await self.development_agent.implement_improvement(improvement_task)
            
            task.status = result.status
            task.completed_at = datetime.now(UTC).isoformat()
            task.result = result
            
            await self.notify("task_completed", task)
            return result
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await self.notify("task_failed", task)
            raise


class MultiAgentOrchestrator:
    """
    Advanced orchestrator that manages multiple specialized agents.
    
    Features:
    - Intelligent task routing to best agent
    - Multi-agent collaboration
    - Task decomposition and delegation
    - Context sharing between agents
    - Progress tracking across agents
    """
    
    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.agent_registry: dict[AgentRole, list[str]] = {}
        self.task_queue: list[AgentTask] = []
        self.active_tasks: dict[str, AgentTask] = {}
        self.completed_tasks: dict[str, AgentTask] = {}
        self.message_log: list[AgentMessage] = []
        
        # Initialize specialized agents
        self._register_agents()
        
        # Keep legacy agents for compatibility
        self.utility_agent = UtilityAgent(getattr(self, 'toolbox', None))
        self.document_agent = None  # Will be initialized
        self.research_agent = None
        self.url_agent = None
        self.image_intel_agent = None
        self.execution_agent = None
        self.capability_agent = CapabilityAgent()
        self.coding_agent = CodingAgent()
        self.video_agent = None
        self.image_gen_agent = None
    
    def _register_agents(self):
        """Register all specialized agents and sub-agents."""
        # Main agents
        agents = [
            PlanningAgentWrapper(),
            CodingAgentWrapper(),
            ResearchAgentWrapper(),
            ReviewAgent(),
            TestingAgent(),
            DocumentationAgent(),
            SelfDevelopmentAgentWrapper()  # NEW: Self-development agent
        ]

        # Sub-agents
        sub_agents = [
            PythonSubAgent(),
            JavaScriptSubAgent(),
            SecuritySubAgent(),
            PerformanceSubAgent(),
            APISubAgent()
        ]

        all_agents = agents + sub_agents

        for agent in all_agents:
            self.agents[agent.name] = agent

            # Register by role
            if agent.role not in self.agent_registry:
                self.agent_registry[agent.role] = []
            self.agent_registry[agent.role].append(agent.name)

            # Register callback for task updates
            agent.register_callback(self._on_agent_event)

        print(f"✅ Registered {len(all_agents)} agents ({len(agents)} main, {len(sub_agents)} sub-agents)")
    
    async def _on_agent_event(self, event_type: str, data: Any):
        """Handle events from agents."""
        if event_type == "task_completed":
            self.completed_tasks[data.task_id] = data
            if data.task_id in self.active_tasks:
                del self.active_tasks[data.task_id]
        elif event_type == "task_failed":
            if data.task_id in self.active_tasks:
                del self.active_tasks[data.task_id]
    
    def get_agent_for_task(self, task_description: str, required_role: Optional[AgentRole] = None) -> Optional[BaseAgent]:
        """Find the best agent for a task."""
        if required_role:
            # Use specific role if requested
            agent_names = self.agent_registry.get(required_role, [])
            if agent_names:
                return self.agents.get(agent_names[0])
        
        # Find best agent by confidence score
        best_agent = None
        best_score = 0.0
        
        for agent in self.agents.values():
            score = agent.can_handle(task_description)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent if best_score > 0.5 else None
    
    async def route_task(self, task_description: str, context: dict[str, Any] = None) -> OrchestratorResult:
        """Intelligently route a task to the best agent(s)."""
        context = context or {}
        
        # Create task
        task_id = f"task-{datetime.now(UTC).isoformat()}"
        task = AgentTask(
            task_id=task_id,
            description=task_description,
            agent_role=AgentRole.SPECIALIST,
            context=context
        )
        
        # Find best agent
        agent = self.get_agent_for_task(task_description)
        
        if agent is None:
            # Fall back to coding agent or return empty result
            return OrchestratorResult()
        
        # Assign and execute task
        self.active_tasks[task_id] = task
        self.task_queue.append(task)
        
        try:
            result = await agent.execute(task)
            
            # Convert result to OrchestratorResult
            if isinstance(result, OrchestratorResult):
                return result
            else:
                return OrchestratorResult(
                    direct_reply=str(result),
                    used_agents=[agent.name]
                )
        except Exception as e:
            return OrchestratorResult(
                direct_reply=f"Task failed: {str(e)}",
                used_agents=[agent.name]
            )
    
    async def execute_multi_agent_workflow(self, task_description: str, context: dict[str, Any] = None) -> OrchestratorResult:
        """
        Execute a workflow that may involve multiple agents collaborating.
        
        Example workflows:
        - Code → Review → Test → Deploy
        - Research → Plan → Implement
        - Code → Document → Test
        """
        context = context or {}
        workflow_id = f"workflow-{datetime.now(UTC).isoformat()}"
        
        # Analyze task to determine workflow
        workflow_steps = self._decompose_task(task_description)
        
        results = []
        used_agents = []
        
        for step in workflow_steps:
            agent = self.get_agent_for_task(step["description"], step.get("role"))
            
            if agent:
                task = AgentTask(
                    task_id=f"{workflow_id}-step-{step['step_number']}",
                    description=step["description"],
                    agent_role=step.get("role", AgentRole.SPECIALIST),
                    context={**context, "previous_results": results}
                )
                
                try:
                    result = await agent.execute(task)
                    results.append(result)
                    used_agents.append(agent.name)
                except Exception as e:
                    return OrchestratorResult(
                        direct_reply=f"Workflow failed at step {step['step_number']}: {str(e)}",
                        used_agents=used_agents
                    )
        
        # Combine results
        if not results:
            return OrchestratorResult()
        
        # Format combined result
        combined = "\n\n".join([str(r) for r in results])
        
        return OrchestratorResult(
            direct_reply=combined,
            used_agents=used_agents
        )
    
    def _decompose_task(self, task_description: str) -> list[dict]:
        """Decompose a complex task into sub-tasks for different agents."""
        task_lower = task_description.lower()

        # Intelligent decomposition based on task keywords
        steps = []
        step_number = 1

        # Detect if task needs planning
        if any(kw in task_lower for kw in ["complex", "multi-step", "plan", "first", "then", "create", "build", "implement"]):
            steps.append({
                "step_number": step_number,
                "description": f"Create detailed plan for: {task_description}",
                "role": AgentRole.PLANNER
            })
            step_number += 1

        # Detect language-specific tasks
        if any(kw in task_lower for kw in ["python", "django", "flask", "fastapi"]):
            steps.append({
                "step_number": step_number,
                "description": f"Implement Python solution: {task_description}",
                "role": AgentRole.CODER
            })
            step_number += 1
        elif any(kw in task_lower for kw in ["javascript", "typescript", "react", "node", "vue", "angular"]):
            steps.append({
                "step_number": step_number,
                "description": f"Implement JavaScript/TypeScript solution: {task_description}",
                "role": AgentRole.CODER
            })
            step_number += 1
        # Generic coding tasks
        elif any(kw in task_lower for kw in ["code", "create", "implement", "write", "function", "api", "endpoint"]):
            steps.append({
                "step_number": step_number,
                "description": f"Implement: {task_description}",
                "role": AgentRole.CODER
            })
            step_number += 1

        # Detect if task needs security review
        if any(kw in task_lower for kw in ["security", "vulnerability", "auth", "encrypt", "secure"]):
            steps.append({
                "step_number": step_number,
                "description": f"Perform security review",
                "role": AgentRole.REVIEWER
            })
            step_number += 1

        # Detect if task needs performance review
        if any(kw in task_lower for kw in ["performance", "optimize", "speed", "fast", "efficient"]):
            steps.append({
                "step_number": step_number,
                "description": f"Review performance and optimize",
                "role": AgentRole.REVIEWER
            })
            step_number += 1

        # Check if task needs general review
        if any(kw in task_lower for kw in ["review", "check", "quality", "best practices"]):
            steps.append({
                "step_number": step_number,
                "description": f"Review implementation for quality",
                "role": AgentRole.REVIEWER
            })
            step_number += 1

        # Check if task needs testing
        if any(kw in task_lower for kw in ["test", "validate", "verify", "unit test", "integration test"]):
            steps.append({
                "step_number": step_number,
                "description": f"Generate and run tests",
                "role": AgentRole.TESTER
            })
            step_number += 1

        # Check if task needs documentation
        if any(kw in task_lower for kw in ["document", "readme", "docs", "comment", "explain"]):
            steps.append({
                "step_number": step_number,
                "description": f"Generate documentation",
                "role": AgentRole.DOCUMENTOR
            })
            step_number += 1

        # If no steps were added, add a generic coding step
        if not steps:
            steps.append({
                "step_number": 1,
                "description": task_description,
                "role": AgentRole.SPECIALIST
            })

        return steps
    
    async def delegate_subtasks(self, main_task: AgentTask, subtasks: list[AgentTask]) -> list[Any]:
        """Delegate subtasks to appropriate agents and collect results."""
        results = []
        
        for subtask in subtasks:
            # Set dependencies
            subtask.dependencies = [main_task.task_id]
            
            # Find appropriate agent
            agent = self.get_agent_for_task(subtask.description, subtask.agent_role)
            
            if agent:
                self.active_tasks[subtask.task_id] = subtask
                try:
                    result = await agent.execute(subtask)
                    results.append(result)
                    self.completed_tasks[subtask.task_id] = subtask
                except Exception as e:
                    subtask.status = "failed"
                    subtask.error = str(e)
                    results.append(None)
            else:
                subtask.status = "failed"
                subtask.error = "No suitable agent found"
                results.append(None)
        
        return results
    
    def get_agent_status(self) -> dict:
        """Get status of all agents."""
        return {
            name: {
                "role": agent.role.value,
                "active_tasks": len([t for t in self.active_tasks.values() if t.agent_role == agent.role]),
                "completed_tasks": len([t for t in self.completed_tasks.values() if t.agent_role == agent.role]),
                "capabilities": [c.name for c in agent.capabilities]
            }
            for name, agent in self.agents.items()
        }
    
    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get status of a specific task."""
        return (
            self.active_tasks.get(task_id) or
            self.completed_tasks.get(task_id)
        )


# Singleton instance
_multi_agent_orchestrator: Optional[MultiAgentOrchestrator] = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    """Get or create the multi-agent orchestrator singleton."""
    global _multi_agent_orchestrator
    if _multi_agent_orchestrator is None:
        _multi_agent_orchestrator = MultiAgentOrchestrator()
    return _multi_agent_orchestrator
