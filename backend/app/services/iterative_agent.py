"""
Iterative Agent Loop - Modern Autonomous AI Execution

Follows the Thought -> Action -> Observation pattern.
Capable of using all registered tools and skills to solve complex tasks.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import httpx
from pathlib import Path

from app.core.config import settings
from app.services.dynamic_tool_registry import get_dynamic_tool_registry
from app.services.skill_service import get_skill_service
from app.services.cost_tracker import get_cost_tracker


@dataclass
class AgentMessage:
    """A message in the agent's internal history."""
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_outputs: Optional[List[Dict]] = None
    thought: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class IterativeAgent:
    """
    Advanced agent that operates in an iterative loop.
    Self-correcting, tool-using, and skill-aware.
    """

    MAX_ITERATIONS = 15

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(settings.backend_root).parent.parent
        self.tool_registry = get_dynamic_tool_registry()
        self.skill_service = get_skill_service(self.project_root)
        self.cost_tracker = get_cost_tracker(self.project_root)
        self.history: List[AgentMessage] = []
        self.active_skills: List[str] = []

    async def execute_task(self, task: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Run the iterative loop to solve a task."""
        self.history = []
        self.active_skills = []
        self.cost_tracker.start_new_session()
        
        # Build initial system prompt
        system_prompt = self._build_system_prompt()
        self.history.append(AgentMessage(role="system", content=system_prompt))
        
        # Add CLAUDE.md context if exists
        claude_md_path = self.project_root / "CLAUDE.md"
        if claude_md_path.exists():
            content = claude_md_path.read_text(encoding="utf-8")
            self.history.append(AgentMessage(role="system", content=f"PROJECT CONVENTIONS (from CLAUDE.md):\n\n{content}"))
        
        # Add user task
        self.history.append(AgentMessage(role="user", content=task))
        
        iteration = 0
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            
            # 1. Thought: Ask LLM what to do next
            response, raw_data = await self._call_llm()
            
            # Parse thought and tool calls
            thought, tool_calls, is_complete, final_result = self._parse_llm_response(response)
            
            # Record usage from response if available (Ollama doesn't always provide it, but we can mock/estimate)
            self._record_llm_usage(raw_data)

            # Log thought clearly
            self.history.append(AgentMessage(role="assistant", content=response, tool_calls=tool_calls, thought=thought))
            
            if is_complete:
                return {
                    "status": "completed",
                    "result": final_result,
                    "iterations": iteration,
                    "cost_summary": self.cost_tracker.get_session_summary(),
                    "history": [m.__dict__ for m in self.history]
                }
            
            if not tool_calls:
                # If no tool calls and not complete, LLM might be stuck
                self.history.append(AgentMessage(role="user", content="You didn't call any tools. If you're done, please state your final result and set is_complete to true."))
                continue

            # 2. Action: Execute tool calls
            tool_outputs = []
            paused = False
            pause_reason = ""
            for tool_call in tool_calls:
                # Special handling for ask_permission and ask_user - if they're called, we must stop the loop
                if tool_call.get("name") in ["ask_permission", "ask_user"]:
                    output = await self._execute_tool_call(tool_call, session_id)
                    tool_outputs.append(output)
                    paused = True
                    pause_reason = "awaiting_permission" if tool_call.get("name") == "ask_permission" else "awaiting_user_input"
                    break

                output = await self._execute_tool_call(tool_call, session_id)
                tool_outputs.append(output)
            
            if paused:
                # Return partial result so UI can handle the pause
                return {
                    "status": "paused",
                    "reason": pause_reason,
                    "iterations": iteration,
                    "history": [m.__dict__ for m in self.history],
                    "tool_outputs": tool_outputs
                }

            # 3. Observation: Feed tool outputs back to LLM
            observation_content = "\n\n".join([
                f"Tool: {o['tool']}\nOutput: {json.dumps(o['output'], indent=2)}"
                for o in tool_outputs
            ])
            self.history.append(AgentMessage(role="user", content=f"OBSERVATION:\n{observation_content}", tool_outputs=tool_outputs))
            
        return {
            "status": "failed",
            "error": "Max iterations reached",
            "history": [m.__dict__ for m in self.history]
        }

    def _build_system_prompt(self) -> str:
        """Construct the system prompt with tool definitions and skills."""
        tools_schema = self.tool_registry.to_openai_schema()
        skills = self.skill_service.list_skills()
        
        prompt = f"""You are ISE Advanced Agent, a highly capable autonomous developer.
You operate in an iterative Thought -> Action -> Observation loop.

AVAILABLE TOOLS:
{json.dumps(tools_schema, indent=2)}

AVAILABLE SKILLS:
{json.dumps(skills, indent=2)}
To use a skill, mention it in your thought.

AGENT PROTOCOLS:
1. THINK before you act. Explain your reasoning clearly.
2. ALWAYS provide COMPLETE, FUNCTIONAL code. Avoid placeholders.
3. If a tool fails, analyze the error and try a different approach.
4. GIT SAFETY: 
   - NEVER update git config.
   - NEVER run destructive commands (force push, reset --hard) unless explicitly asked.
   - Prefer adding specific files by name rather than "git add .".
   - ALWAYS use a HEREDOC for commit messages to ensure correct formatting:
     git commit -m "$(cat <<'EOF'
     Your commit message here.
     EOF
     )"
5. FILE EDITING:
   - Use the smallest unique old_string to identify the target for edits.
   - Prefer editing existing files over creating new ones.
6. PERMISSIONS:
   - Use `ask_permission` for sensitive operations (deletion, package install, major system change).
   - Use `ask_user` for clarification or general questions.
7. ADVANCED CAPABILITIES:
   - Use `enter_worktree` for safe, isolated experimentation on a new branch.
   - Use `spawn_subagent` to delegate large or distinct sub-tasks (e.g., "design a UI" or "write a research report").
   - Use `rip_grep` for professional-grade code search across the entire project.
   - Use `repl_execute` to test Python logic or perform complex data manipulation.

RESPONSE FORMAT:
Your response MUST be a JSON object:
{{
    "thought": "Your internal reasoning",
    "tool_calls": [
        {{"name": "tool_name", "parameters": {{...}}}}
    ],
    "is_complete": false,
    "final_result": "Optional summary when done"
}}
"""
        return prompt

    async def _call_llm(self) -> tuple:
        """Call the LLM with current history."""
        messages = [
            {"role": m.role, "content": m.content}
            for m in self.history
        ]
        
        payload = {
            "model": settings.default_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4096}
        }

        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=300.0) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return content, data
        except Exception as e:
            err_msg = json.dumps({
                "thought": f"LLM Call failed: {str(e)}",
                "is_complete": True,
                "final_result": f"Error: {str(e)}"
            })
            return err_msg, {}

    def _record_llm_usage(self, raw_data: Dict):
        """Record token usage from LLM response."""
        # Ollama usage stats
        prompt_eval_count = raw_data.get("prompt_eval_count", 0)
        eval_count = raw_data.get("eval_count", 0)
        model = raw_data.get("model", settings.default_model)
        
        if prompt_eval_count > 0 or eval_count > 0:
            self.cost_tracker.record_usage(model, prompt_eval_count, eval_count)

    def _parse_llm_response(self, response: str) -> tuple:
        """Parse JSON response from LLM."""
        try:
            # Try to find JSON block
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
                
            return (
                data.get("thought", ""),
                data.get("tool_calls", []),
                data.get("is_complete", False),
                data.get("final_result", "")
            )
        except Exception:
            return (response, [], False, "")

    async def _execute_tool_call(self, tool_call: Dict, session_id: Optional[str]) -> Dict:
        """Execute a tool call using the registry."""
        name = tool_call.get("name")
        params = tool_call.get("parameters", {})
        
        # Inject session_id if needed by the tool
        tool = self.tool_registry.get_tool(name)
        if tool and "session_id" in tool.parameters and session_id:
            params["session_id"] = session_id
            
        try:
            output = await self.tool_registry.execute_tool_async(name, **params)
            return {"tool": name, "output": output, "success": True}
        except Exception as e:
            return {"tool": name, "output": str(e), "success": False}


# Global instance
_agent: Optional[IterativeAgent] = None


def get_iterative_agent(project_root: Optional[Path] = None) -> IterativeAgent:
    """Get or create iterative agent instance."""
    global _agent
    if _agent is None:
        _agent = IterativeAgent(project_root)
    return _agent
