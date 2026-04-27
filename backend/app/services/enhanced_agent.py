"""
Enhanced agent with improved reasoning, task decomposition, and feedback loops.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskAnalysis:
    """Result of task analysis."""
    task: str
    complexity: str  # simple, moderate, complex
    estimated_steps: int
    requires_verification: bool
    suggested_agents: List[str]
    reasoning: str


@dataclass
class TaskDecomposition:
    """Decomposed task into subtasks."""
    main_task: str
    subtasks: List[Dict[str, Any]]
    orchestration_strategy: str  # sequential, parallel, adaptive
    verification_points: List[str]
    fallback_strategies: List[str]


class TaskAnalyzer:
    """Analyzes task complexity and determines optimal approach."""

    COMPLEXITY_KEYWORDS = {
        "simple": [
            "what is", "explain", "summarize", "list", "define",
            "when", "where", "who", "how many"
        ],
        "moderate": [
            "compare", "analyze", "evaluate", "implement", "create",
            "fix", "improve", "refactor", "optimize", "merge"
        ],
        "complex": [
            "architect", "design system", "multi-step", "integration",
            "performance tuning", "security", "scalability", "large refactor"
        ],
    }

    AGENT_KEYWORDS = {
        "planning": ["plan", "design", "architecture", "strategy", "roadmap"],
        "coding": ["code", "implement", "fix", "debug", "refactor"],
        "research": ["research", "analyze", "investigate", "explore", "find"],
        "review": ["review", "audit", "check", "validate", "test"],
        "documentation": ["document", "explain", "describe", "guide"],
        "testing": ["test", "verify", "validate", "check"],
    }

    def __init__(self):
        self.logger = logger

    async def analyze_task(self, task: str) -> TaskAnalysis:
        """
        Analyze task to determine complexity and required approach.
        """
        task_lower = task.lower()
        complexity = self._determine_complexity(task_lower)
        estimated_steps = self._estimate_steps(complexity)
        suggested_agents = self._suggest_agents(task_lower)
        requires_verification = complexity != "simple"

        reasoning = self._build_reasoning(task, complexity, estimated_steps)

        return TaskAnalysis(
            task=task,
            complexity=complexity,
            estimated_steps=estimated_steps,
            requires_verification=requires_verification,
            suggested_agents=suggested_agents,
            reasoning=reasoning,
        )

    def _determine_complexity(self, task: str) -> str:
        """Determine task complexity level."""
        for complexity_level, keywords in self.COMPLEXITY_KEYWORDS.items():
            if any(kw in task for kw in keywords):
                return complexity_level
        return "moderate"

    def _estimate_steps(self, complexity: str) -> int:
        """Estimate number of steps needed."""
        estimates = {
            "simple": 1,
            "moderate": 3,
            "complex": 5,
        }
        return estimates.get(complexity, 3)

    def _suggest_agents(self, task: str) -> List[str]:
        """Suggest which agents would be best for this task."""
        suggestions = []
        for agent, keywords in self.AGENT_KEYWORDS.items():
            if any(kw in task for kw in keywords):
                suggestions.append(agent)
        return suggestions or ["planning"]  # Default to planner

    def _build_reasoning(self, task: str, complexity: str, steps: int) -> str:
        """Build reasoning explanation for the analysis."""
        return (
            f"Task complexity: {complexity} "
            f"(estimated {steps} step{'s' if steps != 1 else ''}). "
            f"Will require verification and structured approach."
        )


class TaskDecomposer:
    """Decomposes complex tasks into manageable subtasks."""

    def __init__(self, analyzer: Optional[TaskAnalyzer] = None):
        self.analyzer = analyzer or TaskAnalyzer()
        self.logger = logger

    async def decompose(self, task: str, analysis: Optional[TaskAnalysis] = None) -> TaskDecomposition:
        """
        Decompose task into subtasks.
        """
        if analysis is None:
            analysis = await self.analyzer.analyze_task(task)

        subtasks = await self._generate_subtasks(task, analysis)
        strategy = self._determine_strategy(analysis.complexity, len(subtasks))
        verification_points = self._identify_verification_points(subtasks)
        fallbacks = self._plan_fallbacks(subtasks)

        return TaskDecomposition(
            main_task=task,
            subtasks=subtasks,
            orchestration_strategy=strategy,
            verification_points=verification_points,
            fallback_strategies=fallbacks,
        )

    async def _generate_subtasks(self, task: str, analysis: TaskAnalysis) -> List[Dict[str, Any]]:
        """Generate subtasks based on analysis."""
        subtasks = []

        if analysis.complexity == "simple":
            subtasks.append({
                "id": "main",
                "description": task,
                "agent": analysis.suggested_agents[0] if analysis.suggested_agents else "chat",
                "depends_on": [],
                "priority": "high",
            })
        else:
            # Break down by suggested agents
            for i, agent in enumerate(analysis.suggested_agents[:3]):  # Max 3 agents
                subtasks.append({
                    "id": f"task_{i+1}",
                    "description": f"Handle {agent} aspects of: {task[:50]}...",
                    "agent": agent,
                    "depends_on": [f"task_{i}"] if i > 0 else [],
                    "priority": "high" if i == 0 else "normal",
                })

        return subtasks

    def _determine_strategy(self, complexity: str, subtask_count: int) -> str:
        """Determine orchestration strategy."""
        if subtask_count <= 1:
            return "sequential"
        elif complexity == "complex" and subtask_count > 3:
            return "adaptive"  # Mix of parallel and sequential
        else:
            return "sequential"  # Safer for most cases

    def _identify_verification_points(self, subtasks: List[Dict[str, Any]]) -> List[str]:
        """Identify where verification is needed."""
        points = []
        for i, task in enumerate(subtasks):
            if i > 0 or len(subtasks) > 1:  # Verify after each task except single simple ones
                points.append(f"After {task['id']}")
        return points

    def _plan_fallbacks(self, subtasks: List[Dict[str, Any]]) -> List[str]:
        """Plan fallback strategies for task failures."""
        fallbacks = []
        if len(subtasks) > 1:
            fallbacks.append("Skip failed subtask and continue")
            fallbacks.append("Retry with different agent")
            fallbacks.append("Escalate to human review")
        else:
            fallbacks.append("Return partial results")
            fallbacks.append("Suggest alternative approach")
        return fallbacks


class AgentMemory:
    """Short-term memory system for agents within a session."""

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self.memory: List[Dict[str, Any]] = []
        self.logger = logger

    def remember(self, key: str, value: Any, context: str = ""):
        """Store something in memory."""
        entry = {
            "key": key,
            "value": value,
            "context": context,
            "timestamp": self._get_timestamp(),
        }
        self.memory.append(entry)

        if len(self.memory) > self.max_entries:
            self.memory.pop(0)  # Remove oldest

        self.logger.debug(f"Remembered: {key}")

    def recall(self, key: str) -> Any:
        """Retrieve from memory."""
        for entry in reversed(self.memory):  # Search most recent first
            if entry["key"] == key:
                return entry["value"]
        return None

    def recall_context(self, context: str) -> List[Dict[str, Any]]:
        """Retrieve all memories from a specific context."""
        return [e for e in self.memory if e["context"] == context]

    def clear(self):
        """Clear all memory."""
        self.memory.clear()

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class FeedbackCollector:
    """Collects and analyzes feedback for agent improvement."""

    def __init__(self):
        self.feedback_history: List[Dict[str, Any]] = []
        self.logger = logger

    def collect_feedback(self, interaction_id: str, feedback_type: str, content: str, rating: Optional[int] = None):
        """
        Collect feedback on an interaction.
        
        Args:
            interaction_id: ID of the interaction
            feedback_type: Type of feedback (positive, negative, suggestion)
            content: Feedback content
            rating: Optional 1-5 rating
        """
        entry = {
            "interaction_id": interaction_id,
            "type": feedback_type,
            "content": content,
            "rating": rating,
            "timestamp": self._get_timestamp(),
        }
        self.feedback_history.append(entry)
        self.logger.info(f"Feedback collected: {feedback_type}")

    def get_improvement_suggestions(self) -> List[str]:
        """Analyze feedback to suggest improvements."""
        suggestions = []

        # Count feedback types
        positive = sum(1 for f in self.feedback_history if f["type"] == "positive")
        negative = sum(1 for f in self.feedback_history if f["type"] == "negative")
        total = len(self.feedback_history)

        if total == 0:
            return suggestions

        positive_ratio = positive / total
        if positive_ratio < 0.6:
            suggestions.append("Consider improving response quality and accuracy")

        if negative >= total * 0.3:
            suggestions.append("High rate of negative feedback - review common issues")

        return suggestions

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class ReasoningBooster:
    """Enhances agent reasoning through better prompting and analysis."""

    # Prompts for different reasoning styles
    REASONING_STYLES = {
        "analytical": """
Use logical, step-by-step analysis. Break down the problem systematically.
Identify assumptions, gather relevant information, and reason through to conclusions.
""",
        "creative": """
Consider multiple creative approaches. Think outside conventional solutions.
Explore novel connections and unconventional wisdom.
""",
        "systematic": """
Use structured, methodical approaches. Follow established processes and patterns.
Ensure completeness and consistency.
""",
        "intuitive": """
Use pattern recognition and experience-based judgment.
Consider implicit knowledge and contextual understanding.
""",
    }

    def __init__(self):
        self.logger = logger

    def get_reasoning_prompt(self, style: str = "analytical") -> str:
        """Get a prompt to enhance reasoning for a specific style."""
        base = """
Think carefully about this. Consider:
1. What is being asked?
2. What information is relevant?
3. What are the key assumptions?
4. What reasoning path leads to the answer?
5. Are there edge cases or exceptions?

{}
"""
        style_prompt = self.REASONING_STYLES.get(style, self.REASONING_STYLES["analytical"])
        return base.format(style_prompt)

    def generate_reasoning_chain(self, task: str, context: str = "") -> str:
        """Generate a chain-of-thought prompt for better reasoning."""
        return f"""
For the following task, provide step-by-step reasoning:

Task: {task}

{f"Context: {context}" if context else ""}

Reasoning steps:
1. [Define the problem clearly]
2. [Identify key information needed]
3. [Break into logical components]
4. [Reason through each component]
5. [Synthesize into solution]

Answer:
"""


class EnhancedAgentOrchestrator:
    """Enhanced orchestrator with better task routing and agent coordination."""

    def __init__(self):
        self.analyzer = TaskAnalyzer()
        self.decomposer = TaskDecomposer(self.analyzer)
        self.memory = AgentMemory()
        self.feedback = FeedbackCollector()
        self.boosting = ReasoningBooster()
        self.logger = logger

    async def orchestrate(self, task: str, agents: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate task execution across agents.
        """
        # Analyze task
        analysis = await self.analyzer.analyze_task(task)
        self.logger.info(f"Task analysis: {analysis.complexity} - {analysis.suggested_agents}")

        # Decompose if needed
        decomposition = await self.decomposer.decompose(task, analysis)

        # Prepare execution plan
        plan = {
            "task": task,
            "analysis": analysis,
            "decomposition": decomposition,
            "execution_steps": [],
            "verification_plan": decomposition.verification_points,
        }

        # Store in memory for reference
        self.memory.remember("current_plan", plan, context="execution")

        return plan

    def suggest_reasoning_approach(self, task_complexity: str) -> str:
        """Suggest best reasoning approach for task."""
        if task_complexity == "simple":
            return self.boosting.get_reasoning_prompt("intuitive")
        elif task_complexity == "complex":
            return self.boosting.get_reasoning_prompt("analytical")
        else:
            return self.boosting.get_reasoning_prompt("systematic")
