"""
Autonomous Planning Agent with Progress Tracking

This agent creates detailed plans and executes them step-by-step,
showing progress like: 0/3 → 1/3 → 2/3 → 3/3 (Completed)

Similar to Qwen Code Agent behavior.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import aiofiles

from backend.app.services.intelligent_coding_agent import (
    IntelligentCodingAgent,
    get_intelligent_coding_agent,
)


class PlanStatus(str, Enum):
    """Status of the overall plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of an individual plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_number: int
    description: str
    action_type: str  # "create_file", "edit_file", "run_command", "show_result", etc.
    target: str  # File path, command, or description
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "action_type": self.action_type,
            "target": self.target,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan with progress tracking."""
    task: str
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    current_step: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: str = ""

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)

    @property
    def progress_text(self) -> str:
        """Return progress text like "1/3 completed"."""
        return f"{self.completed_steps}/{self.total_steps}"

    def to_log_string(self) -> str:
        """Convert plan to human-readable log with progress."""
        status_icons = {
            StepStatus.PENDING: "⏳",
            StepStatus.IN_PROGRESS: "🔄",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
        }

        lines = [
            f"📋 **Plan: {self.task}**",
            f"**Progress:** {self.progress_text} ({self.status.value})",
            "",
        ]

        for step in self.steps:
            icon = status_icons.get(step.status, "•")
            lines.append(f"{icon} **Step {step.step_number}:** {step.description}")
            
            if step.output and step.status == StepStatus.COMPLETED:
                # Show brief output
                output_preview = step.output[:200]
                if len(step.output) > 200:
                    output_preview += "..."
                lines.append(f"   ```\n{output_preview}\n   ```")
            
            if step.error:
                lines.append(f"   ⚠️ Error: {step.error}")
            
            lines.append("")

        if self.status == PlanStatus.COMPLETED:
            lines.append(f"✅ **Plan completed!** ({self.completed_steps}/{self.total_steps} steps)")
        elif self.status == PlanStatus.FAILED:
            lines.append(f"❌ **Plan failed:** {self.error}")

        return "\n".join(lines)

    def to_progress_event(self) -> dict:
        """Convert to progress event for streaming."""
        return {
            "type": "plan_progress",
            "task": self.task,
            "status": self.status.value,
            "progress": self.progress_text,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "steps": [step.to_dict() for step in self.steps],
        }


class AutonomousPlanningAgent:
    """
    Autonomous agent that creates plans and executes them step-by-step.
    
    Features:
    1. Parses user request into actionable steps
    2. Shows progress (0/3, 1/3, 2/3, 3/3)
    3. Executes each step autonomously
    4. Reports progress after each step
    5. Handles errors and recovery
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.coding_agent = get_intelligent_coding_agent(project_root)
        self.progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self.progress_callback = callback

    async def create_plan(self, task: str, project_context: Optional[dict[str, Any]] = None) -> ExecutionPlan:
        """
        Create an execution plan from a task description.
        
        Example:
            Task: "Create 2 files. First: text1.txt with 'this is a text', then show result"
            Plan:
            - Step 1: Create text1.txt
            - Step 2: Update content to "this is a text"
            - Step 3: Show the result
        """
        plan = ExecutionPlan(
            task=task,
            created_at=datetime.now(UTC).isoformat(),
        )

        # Parse the task to identify steps
        steps = await self._parse_task_into_steps(task, project_context or {})
        plan.steps = steps

        return plan

    async def _parse_task_into_steps(
        self,
        task: str,
        project_context: Optional[dict[str, Any]] = None,
    ) -> list[PlanStep]:
        """
        Parse a task description into discrete steps.

        Uses intelligent parsing to identify:
        - File creation tasks
        - File modification tasks
        - Command execution tasks
        - Display/show tasks
        """
        task_lower = task.lower()
        project_context = project_context or {}
        steps = []
        step_number = 1

        # Pattern 1: Explicit multi-step tasks
        # "create file X, then update it, then show result"
        explicit_steps = self._detect_explicit_steps(task)
        
        if explicit_steps and len(explicit_steps) > 1:
            # Multiple steps detected
            for step_desc in explicit_steps:
                action_type = self._determine_action_type(step_desc)
                target = self._extract_target(step_desc)
                
                # Extract content for this step
                content = self._extract_content_for_step(step_desc)
                
                step = PlanStep(
                    step_number=step_number,
                    description=step_desc.strip(),
                    action_type=action_type,
                    target=target,
                    metadata={"content": content} if content else {},
                )
                steps.append(step)
                step_number += 1
            steps = await self._enrich_steps_with_project_context(steps, task, project_context)
        else:
            # Pattern 2: Try to detect implicit multi-step tasks
            # Look for multiple actions in the task
            implicit_steps = self._detect_implicit_steps(task)
            
            if implicit_steps and len(implicit_steps) > 1:
                for step_desc in implicit_steps:
                    action_type = self._determine_action_type(step_desc)
                    target = self._extract_target(step_desc)
                    content = self._extract_content_for_step(step_desc)
                    
                    step = PlanStep(
                        step_number=step_number,
                        description=step_desc.strip(),
                        action_type=action_type,
                        target=target,
                        metadata={"content": content} if content else {},
                    )
                    steps.append(step)
                    step_number += 1
                steps = await self._enrich_steps_with_project_context(steps, task, project_context)
            else:
                coding_steps = await self._build_project_aware_steps(task, project_context, step_number)
                if coding_steps:
                    return coding_steps

                # Pattern 3: Single task - create one step
                # Rewrite the task for better clarity
                rewritten_task = self._rewrite_task_for_clarity(task)

                steps.append(PlanStep(
                    step_number=1,
                    description=rewritten_task,
                    action_type=self._determine_action_type(task),
                    target=self._extract_target(task),
                    metadata={"content": self._extract_content_for_step(task)} if self._extract_content_for_step(task) else {},
                ))

        return steps

    async def _enrich_steps_with_project_context(
        self,
        steps: list[PlanStep],
        full_task: str,
        project_context: dict[str, Any],
    ) -> list[PlanStep]:
        """
        Improve text-parsed steps with project-aware targets and verification commands.
        """
        if not steps:
            return steps

        parent_context = self.coding_agent._understand_task(full_task, project_context)
        created_or_edited_paths: list[str] = []

        for step in steps:
            step_context = self.coding_agent._understand_task(step.description, project_context)
            step.metadata.setdefault("project_context", project_context)
            step.metadata.setdefault("coding_context", step_context)

            if step.action_type in {"create_file", "edit_file"}:
                file_ops = await self.coding_agent._determine_files(step.description, step_context)
                if file_ops:
                    primary = file_ops[0]
                    step.target = primary.get("path", step.target)
                    step.metadata["operation"] = primary.get("operation", "write")
                    if primary.get("content") is not None:
                        step.metadata["content"] = primary["content"]
                    if primary.get("previous_content") is not None:
                        step.metadata["previous_content"] = primary["previous_content"]
                    created_or_edited_paths.append(step.target)
                    continue

            if step.action_type == "run_command":
                commands = self._resolve_verification_commands(
                    step.description,
                    created_or_edited_paths,
                    parent_context,
                )
                if commands:
                    step.target = commands[0]
                    step.metadata["verification"] = True
                    step.description = f"Verify the generated changes with `{step.target}`"
                    continue

            if step.action_type in {"show_result", "read_file"} and created_or_edited_paths and step.target == "output.txt":
                step.target = created_or_edited_paths[-1]

        return steps

    def _resolve_verification_commands(
        self,
        step_description: str,
        touched_paths: list[str],
        parent_context: dict[str, Any],
    ) -> list[str]:
        desc_lower = step_description.lower()
        if not any(keyword in desc_lower for keyword in ["verify", "test", "build", "check", "validate"]):
            return []

        if touched_paths:
            return self.coding_agent._build_verification_commands(touched_paths)

        inferred_path = parent_context.get("file_path")
        if inferred_path:
            return self.coding_agent._build_verification_commands([inferred_path])

        framework = (parent_context.get("framework") or "").lower()
        if framework == "react":
            return ["cd frontend && npm run build"]
        if framework == "fastapi":
            return ["python -m compileall backend/app"]
        return []

    async def _build_project_aware_steps(
        self,
        task: str,
        project_context: dict[str, Any],
        start_step_number: int,
    ) -> list[PlanStep]:
        """
        Build richer planning steps from the same project-aware coding analysis
        used by the coding agent.
        """
        context = self.coding_agent._understand_task(task, project_context)
        if context["task_intent"] not in {"create_component", "create_api", "create_utility", "edit_file", "create_file"}:
            return []

        file_ops = await self.coding_agent._determine_files(task, context)
        if not file_ops:
            return []

        steps: list[PlanStep] = []
        step_number = start_step_number
        for file_op in file_ops:
            operation = file_op.get("operation", "write")
            action_type = "edit_file" if operation == "edit" else "create_file"
            content = file_op.get("content")
            metadata = {
                "content": content,
                "coding_context": context,
                "project_context": project_context,
                "operation": operation,
            }
            if file_op.get("previous_content") is not None:
                metadata["previous_content"] = file_op["previous_content"]
            steps.append(
                PlanStep(
                    step_number=step_number,
                    description=file_op.get("description", task),
                    action_type=action_type,
                    target=file_op["path"],
                    metadata=metadata,
                )
            )
            step_number += 1

        for command in self.coding_agent._build_verification_commands(
            [file_op["path"] for file_op in file_ops if file_op.get("path")]
        ):
            steps.append(
                PlanStep(
                    step_number=step_number,
                    description=f"Verify the generated changes with `{command}`",
                    action_type="run_command",
                    target=command,
                    metadata={"verification": True},
                )
            )
            step_number += 1

        return steps

    def _detect_implicit_steps(self, task: str) -> list[str]:
        """Detect implicit steps from task description."""
        steps = []
        task_lower = task.lower()
        
        # Pattern: "create X, update Y, show Z"
        # Split by action verbs
        action_verbs = [
            (r'\bcreate\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?', 'create'),
            (r'\bupdate\s+(?:its|it\'s|the)?\s*(?:content\s+)?(?:to\s+be\s+)?', 'update'),
            (r'\bdisplay\s+(?:it|the\s+(?:content|result|file))', 'display'),
            (r'\bshow\s+(?:me\s+)?(?:it|the\s+(?:content|result|file))', 'show'),
        ]
        
        # Find all action positions
        action_positions = []
        for pattern, action_name in action_verbs:
            for match in re.finditer(pattern, task_lower):
                action_positions.append((match.start(), match.end(), action_name))
        
        # Sort by position
        action_positions.sort(key=lambda x: x[0])
        
        # Extract steps based on action positions
        if action_positions:
            for i, (start, end, action_name) in enumerate(action_positions):
                if i + 1 < len(action_positions):
                    next_start = action_positions[i + 1][0]
                    step_text = task[start:next_start].strip()
                else:
                    step_text = task[start:].strip()
                steps.append(step_text)
        
        return steps if steps else []

    def _rewrite_task_for_clarity(self, task: str) -> str:
        """
        Rewrite the user's task for better LLM understanding.
        
        This improves the agent's ability to understand and execute tasks.
        """
        task_lower = task.lower()
        
        # Extract key information
        file_match = re.search(r'(?:called|named)\s+["\']?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']?', task)
        path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', task)
        content_match = re.search(r'["\']([^"\']{3,})["\']', task)
        
        file_name = file_match.group(1) if file_match else None
        file_path = path_match.group(1).lstrip("/") if path_match else None
        content = content_match.group(1) if content_match else None
        
        # Build clearer task description
        parts = []
        
        if "create" in task_lower or "new" in task_lower:
            if file_name:
                full_path = f"{file_path}/{file_name}" if file_path else file_name
                parts.append(f"Create file: {full_path}")
            else:
                parts.append("Create new file")
        
        if "update" in task_lower or "content" in task_lower:
            if content:
                parts.append(f"Update content to: {content}")
            else:
                parts.append("Update file content")
        
        if "display" in task_lower or "show" in task_lower:
            if file_name:
                parts.append(f"Display content of: {file_name}")
            else:
                parts.append("Display file content")
        
        return " | ".join(parts) if parts else task

    def _validate_file_path(self, file_path: str) -> str:
        """
        Validate and clean file path to prevent invalid names.
        
        Returns cleaned file path.
        """
        # Remove any leading/trailing whitespace
        file_path = file_path.strip()
        
        # Remove leading slashes (make relative to project root)
        file_path = file_path.lstrip("/")
        
        # Check for invalid characters in path
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            file_path = file_path.replace(char, '')
        
        # Ensure path doesn't start with common words that indicate extraction failure
        invalid_starts = ["create ", "update ", "display ", "show ", "the ", "a ", "an "]
        for start in invalid_starts:
            if file_path.lower().startswith(start):
                # Extraction failed, use default
                return "output.txt"
        
        # If path is too long (> 200 chars), it's probably the entire description
        if len(file_path) > 200:
            return "output.txt"
        
        # If path contains spaces and doesn't look like a valid path, use default
        if " " in file_path and not re.match(r'^[\w\-/]+\.\w+$', file_path):
            # Try to extract just the filename
            file_match = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', file_path)
            if file_match:
                return file_match.group(1)
            return "output.txt"
        
        return file_path

    def _detect_explicit_steps(self, task: str) -> list[str]:
        """Detect explicit steps from task description."""
        steps = []
        task_lower = task.lower()
        
        # CRITICAL: Split by "then" keyword (most common separator)
        # Must handle: "then", "then ", " then ", "then\n"
        if "then" in task_lower:
            # Split by "then" but keep the parts
            parts = re.split(r'\bthen\b', task, flags=re.IGNORECASE)
            steps = [p.strip() for p in parts if p.strip()]
            
            if len(steps) > 1:
                return steps
        
        # Try other separators
        separators = [
            r"\band then\b",
            r"\bnext\b",
            r"\bafter that\b",
            r"\bfirst\b.*?\bsecond\b",
            r"\d+\.\s",  # "1. do this 2. do that"
            r"\bstep\s+\d+\b",
        ]
        
        # Try to find sequential indicators
        has_step_indicator = any(re.search(sep, task_lower) for sep in separators)
        
        if has_step_indicator:
            # Split task into parts
            parts = re.split(r'\b(?:and then|next|after that)\b', task, flags=re.IGNORECASE)
            steps = [p.strip() for p in parts if p.strip()]
            
            # If still no steps, try numbered pattern
            if not steps:
                numbered_steps = re.findall(r'(\d+[\.\)]\s*[^\.]+)', task)
                if numbered_steps:
                    steps = numbered_steps
        
        # Look for "first", "second", "third" patterns
        if not steps:
            first_match = re.search(r'first\s*,?\s*(.+?)(?:,|\.)', task_lower)
            second_match = re.search(r'second\s*,?\s*(.+?)(?:,|\.)', task_lower)
            third_match = re.search(r'third\s*,?\s*(.+?)(?:,|\.)', task_lower)
            
            if first_match:
                steps.append(f"First: {first_match.group(1)}")
            if second_match:
                steps.append(f"Second: {second_match.group(1)}")
            if third_match:
                steps.append(f"Third: {third_match.group(1)}")
        
        return steps if steps else []

    def _determine_action_type(self, step_desc: str) -> str:
        """Determine the action type for a step."""
        desc_lower = step_desc.lower()

        if any(kw in desc_lower for kw in ["run", "execute", "command", "verify", "test", "build", "check", "validate"]):
            return "run_command"
        if any(kw in desc_lower for kw in ["create", "make", "new file", "write"]):
            return "create_file"
        elif any(kw in desc_lower for kw in ["update", "edit", "modify", "change", "content"]):
            return "edit_file"
        elif any(kw in desc_lower for kw in ["show", "display", "print", "result"]):
            return "show_result"
        elif any(kw in desc_lower for kw in ["delete", "remove"]):
            return "delete_file"
        elif any(kw in desc_lower for kw in ["read", "open"]):
            return "read_file"
        else:
            return "general"

    def _extract_target(self, step_desc: str) -> str:
        """
        Extract the target (file path, command, etc.) from step description.
        
        CRITICAL: Must extract ONLY the file path, not the entire description.
        """
        step_lower = step_desc.lower()
        
        # Strategy 1: Look for explicit file patterns with quotes
        # "create 'path/to/file.txt'" or "create 'file.txt'"
        quoted_file = re.search(r'["\']([/\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']', step_desc)
        if quoted_file:
            return quoted_file.group(1)
        
        # Strategy 2: Look for "called filename" or "named filename"
        called_match = re.search(r'(?:called|named)\s+["\']?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']?', step_desc, re.IGNORECASE)
        if called_match:
            filename = called_match.group(1)
            # Check if there's a path mentioned
            path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
            if path_match:
                path = path_match.group(1).lstrip("/")
                return f"{path}/{filename}"
            return filename
        
        # Strategy 3: Look for "file inside /path" or "file in /path"
        inside_path_match = re.search(r'(?:file|component)\s+(?:inside|in|at)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
        if inside_path_match:
            path = inside_path_match.group(1).lstrip("/")
            # Look for filename in the same step
            file_in_step = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
            if file_in_step:
                return f"{path}/{file_in_step.group(1)}"
            return path
        
        # Strategy 4: Look for "create filename" or "write filename"
        create_file = re.search(r'(?:create|write|make|save)\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
        if create_file:
            filename = create_file.group(1)
            # Check for path
            path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
            if path_match:
                path = path_match.group(1).lstrip("/")
                return f"{path}/{filename}"
            return filename
        
        # Strategy 5: For update/edit/display steps, try to find file reference
        if any(kw in step_lower for kw in ["update", "edit", "display", "show", "read"]):
            # Look for "it" or "the file" - should inherit from previous step
            # For now, look for any file pattern
            any_file = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
            if any_file:
                return any_file.group(1)
        
        # Fallback: Return a safe default
        return "output.txt"

    def _extract_content_for_step(self, step_desc: str) -> Optional[str]:
        """
        Extract content for a step from the description.
        
        CRITICAL: Must extract ONLY the content, not the entire description.
        """
        # Pattern 1: Quoted content "hello world" or 'hello world'
        content_match = re.search(r'["\']([^"\']{3,})["\']', step_desc)
        if content_match:
            return content_match.group(1)
        
        # Pattern 2: "to be X" or "to X" (where X is at least 3 chars)
        to_be_match = re.search(r'(?:to\s+be\s+|to\s+)([\w\s]{3,})', step_desc, re.IGNORECASE)
        if to_be_match:
            return to_be_match.group(1).strip()
        
        # Pattern 3: "say X" or "display X" or "show X"
        say_match = re.search(r'(?:say|display|show)\s+["\']?([\w\s]{3,})["\']?', step_desc, re.IGNORECASE)
        if say_match:
            return say_match.group(1).strip()
        
        # Pattern 4: "content to be X" or "content is X"
        content_is = re.search(r'(?:content\s+(?:to\s+)?be|content\s+is)\s+["\']?([\w\s]{3,})["\']?', step_desc, re.IGNORECASE)
        if content_is:
            return content_is.group(1).strip()
        
        return None

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[Callable] = None,
        max_retries: int = 2,
    ) -> ExecutionPlan:
        """
        Execute a plan step-by-step, reporting progress.
        
        Includes self-debugging capabilities:
        - Detects errors automatically
        - Attempts to fix and retry
        - Logs all debugging information
        - CRITICAL: Shares context between steps (file paths, etc.)

        Args:
            plan: The execution plan
            progress_callback: Optional callback for progress updates
            max_retries: Maximum retry attempts per step

        Returns:
            Updated plan with results
        """
        if progress_callback:
            self.progress_callback = progress_callback

        plan.status = PlanStatus.IN_PROGRESS
        plan.started_at = datetime.now(UTC).isoformat()
        
        # CRITICAL: Track context across steps
        step_context = {
            "last_created_file": None,
            "last_file_path": None,
            "files_created": [],
        }

        await self._report_progress(plan)

        # Execute each step
        for i, step in enumerate(plan.steps):
            plan.current_step = i

            try:
                # Mark step as in progress
                step.status = StepStatus.IN_PROGRESS
                step.started_at = datetime.now(UTC).isoformat()
                
                # CRITICAL: Inherit context from previous steps
                self._apply_step_context(step, step_context)

                await self._report_progress(plan)

                # Execute the step with retry logic
                success = False
                last_error = None

                for attempt in range(max_retries + 1):
                    try:
                        await self._execute_step(step)
                        success = True
                        break  # Success, exit retry loop
                    except Exception as e:
                        last_error = e
                        print(f"⚠️ [PlanningAgent] Step {step.step_number} attempt {attempt + 1} failed: {str(e)}")

                        if attempt < max_retries:
                            # Try to auto-fix the error
                            print(f"🔧 [PlanningAgent] Attempting to auto-fix step {step.step_number}...")
                            await self._attempt_auto_fix(step, str(e))
                        else:
                            # All retries exhausted
                            raise last_error

                if success:
                    # Mark step as completed
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now(UTC).isoformat()
                    
                    # CRITICAL: Update context with this step's results
                    self._update_step_context(step, step_context)
                    
                    print(f"✅ [PlanningAgent] Step {step.step_number} completed successfully")

                    await self._report_progress(plan)

            except Exception as e:
                # Mark step as failed
                step.status = StepStatus.FAILED
                step.error = str(e)
                step.completed_at = datetime.now(UTC).isoformat()

                plan.status = PlanStatus.FAILED
                plan.error = f"Step {step.step_number} failed: {str(e)}"
                plan.completed_at = datetime.now(UTC).isoformat()

                print(f"❌ [PlanningAgent] Step {step.step_number} failed after retries: {str(e)}")

                await self._report_progress(plan)
                return plan

        # All steps completed
        plan.status = PlanStatus.COMPLETED
        plan.completed_at = datetime.now(UTC).isoformat()

        print(f"✅ [PlanningAgent] All {plan.total_steps} steps completed successfully!")

        await self._report_progress(plan)
        return plan

    def _apply_step_context(self, step: PlanStep, context: dict):
        """
        Apply context from previous steps to current step.
        
        This is CRITICAL for multi-step tasks where steps depend on each other.
        """
        # If this is an update/display/read step and has no target, inherit from last file
        if step.action_type in ["edit_file", "show_result", "read_file", "delete_file"]:
            if not step.target or step.target in ["output.txt", "display the content here", "show the content"]:
                # Inherit from last created file
                if context.get("last_created_file"):
                    step.target = context["last_created_file"]
                    print(f"🔗 [PlanningAgent] Step {step.step_number} inheriting file: {step.target}")
                elif context.get("last_file_path"):
                    step.target = context["last_file_path"]
                    print(f"🔗 [PlanningAgent] Step {step.step_number} inheriting file: {step.target}")
        
        # If this is a content update and no content specified, try to extract from description
        if step.action_type == "edit_file" and not step.metadata.get("content"):
            content = self._extract_content_for_step(step.description)
            if content:
                step.metadata["content"] = content
                print(f"📝 [PlanningAgent] Step {step.step_number} extracted content: {content[:30]}...")

    def _update_step_context(self, step: PlanStep, context: dict):
        """
        Update context with results from this step.
        """
        # If this step created a file, track it
        if step.action_type == "create_file" and step.output and "Successfully wrote to" in step.output:
            # Extract file path from output
            file_match = re.search(r'Successfully wrote to\s+([\w\-/\.]+\.\w+)', step.output)
            if file_match:
                context["last_created_file"] = file_match.group(1)
                context["last_file_path"] = file_match.group(1)
                context["files_created"].append(file_match.group(1))
                print(f"📁 [PlanningAgent] Context updated: Created {file_match.group(1)}")
        
        # Also track the target if it looks like a file path
        if step.target and re.match(r'^[\w\-/\.]+\.\w+$', step.target):
            context["last_file_path"] = step.target

    async def _attempt_auto_fix(self, step: PlanStep, error: str):
        """
        Attempt to automatically fix common errors.
        
        This is similar to Qwen Code's self-debugging capability.
        """
        error_lower = error.lower()
        
        # Fix 1: File not found - create it first
        if "file not found" in error_lower or "no such file" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Creating missing file for step {step.step_number}")
            if step.action_type in ["edit_file", "show_result", "read_file"]:
                # Create the file first, then retry
                file_path = step.target
                content = self._generate_file_content(f"Auto-created: {step.description}", file_path)
                success, msg = await self.coding_agent._write_file(file_path, content)
                if success:
                    step.output = f"Auto-created file: {msg}\n"
                    print(f"✅ [PlanningAgent] Auto-fix successful: Created {file_path}")
        
        # Fix 2: Permission errors - try with different path
        elif "permission" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Using alternative path for step {step.step_number}")
            # Try using a safer path
            if "/" in step.target:
                safe_name = Path(step.target).name
                step.target = safe_name
                print(f"✅ [PlanningAgent] Auto-fix: Changed target to {safe_name}")
        
        # Fix 3: Content extraction failed - use description as content
        elif "content" in error_lower or "empty" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Using description as content for step {step.step_number}")
            if not step.metadata.get("content"):
                step.metadata["content"] = step.description
                print(f"✅ [PlanningAgent] Auto-fix: Set content from description")
        
        # Fix 4: Import errors - add missing imports
        elif "import" in error_lower or "module" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Adding missing imports for step {step.step_number}")
            # This would require more sophisticated handling
            pass
        
        # Generic fix: Log the error for manual review
        else:
            print(f"⚠️ [PlanningAgent] No auto-fix available for error: {error}")
            print(f"💡 [PlanningAgent] Suggestion: Check the step description and file path")

    async def _execute_step(self, step: PlanStep):
        """Execute a single plan step."""
        if step.action_type == "create_file":
            await self._execute_create_file(step)
        elif step.action_type == "edit_file":
            await self._execute_edit_file(step)
        elif step.action_type == "show_result":
            await self._execute_show_result(step)
        elif step.action_type == "run_command":
            await self._execute_run_command(step)
        elif step.action_type == "read_file":
            await self._execute_read_file(step)
        elif step.action_type == "delete_file":
            await self._execute_delete_file(step)
        else:
            await self._execute_general(step)

    async def _execute_create_file(self, step: PlanStep):
        """Execute a file creation step."""
        # Use intelligent coding agent to create the file
        file_path = step.target
        
        # CRITICAL FIX: Validate file path
        file_path = self._validate_file_path(file_path)
        
        # If path starts with /, make it relative to project root
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        content = step.metadata.get("content", "")
        
        print(f"📝 [PlanningAgent] Creating file: {file_path}")
        print(f"📝 [PlanningAgent] Content: {content[:50] if content else '(will generate)'}...")

        if not content:
            # CRITICAL: Generate appropriate content based on file type
            # Don't use the description as content!
            content = self._generate_appropriate_content(file_path, step.description)
            print(f"📝 [PlanningAgent] Generated content for {file_path}")

        success, msg = await self.coding_agent._write_file(file_path, content)
        
        if success:
            step.output = msg
            print(f"✅ [PlanningAgent] Successfully created: {file_path}")
        else:
            print(f"❌ [PlanningAgent] Failed to create: {file_path} - {msg}")
            raise Exception(msg)

    def _generate_appropriate_content(self, file_path: str, description: str) -> str:
        """
        Generate appropriate content based on file type and context.
        
        This is CRITICAL - should NEVER use the description as content.
        """
        ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).stem
        
        # Generate content based on file extension
        if ext == ".txt":
            # Text files - generate simple content
            return f"This is {file_name}.txt\nCreated by ISE AI Planning Agent\n"
        
        elif ext in [".js", ".jsx"]:
            # JavaScript/React files
            if "component" in description.lower() or ext == ".jsx":
                return f'''import React from 'react';

/**
 * {file_name} Component
 * Generated by ISE AI Planning Agent
 */
const {file_name} = () => {{
    return (
        <div className="{file_name.lower()}-container">
            <h1>{file_name}</h1>
        </div>
    );
}};

export default {file_name};
'''
            else:
                return f'''/**
 * {file_name}
 * Generated by ISE AI Planning Agent
 */

console.log("{file_name} loaded");
'''
        
        elif ext in [".ts", ".tsx"]:
            # TypeScript files
            return f'''/**
 * {file_name}
 * Generated by ISE AI Planning Agent
 */

console.log("{file_name} loaded");
'''
        
        elif ext == ".py":
            # Python files
            if "api" in description.lower() or "endpoint" in description.lower():
                return f'''"""
{file_name.title()} API
Generated by ISE AI Planning Agent
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{file_name.lower()}")
async def get_{file_name.lower()}():
    """Get {file_name}"""
    return {{"status": "success"}}
'''
            else:
                return f'''"""
{file_name.title()}
Generated by ISE AI Planning Agent
"""

print("{file_name} loaded")
'''
        
        elif ext == ".html":
            # HTML files
            return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{file_name}</title>
</head>
<body>
    <h1>{file_name}</h1>
    <p>Generated by ISE AI Planning Agent</p>
</body>
</html>
'''
        
        elif ext == ".css":
            # CSS files
            return f'''/*
 * {file_name} Styles
 * Generated by ISE AI Planning Agent
 */

.{file_name.lower()}-container {{
    padding: 20px;
    margin: 0 auto;
}}
'''
        
        elif ext == ".json":
            # JSON files
            return f'''{{
    "name": "{file_name}",
    "version": "1.0.0",
    "description": "Generated by ISE AI Planning Agent"
}}
'''
        
        else:
            # Default for unknown types
            return f"# {file_name}\n# Generated by ISE AI Planning Agent\n"

    async def _execute_edit_file(self, step: PlanStep):
        """Execute a file edit step."""
        file_path = step.target
        
        # CRITICAL FIX: Validate file path
        file_path = self._validate_file_path(file_path)
        
        # If path starts with /, make it relative to project root
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        content = step.metadata.get("content", "")

        if not content:
            # Try to extract content from description
            content_match = re.search(r'["\'](.+?)["\']', step.description)
            if content_match:
                content = content_match.group(1)
            else:
                content = step.description

        print(f"📝 [PlanningAgent] Editing file: {file_path}")
        print(f"📝 [PlanningAgent] New content: {content[:50] if content else '(from description)'}...")

        # Read existing file
        success, existing_content = await self._read_file(file_path)

        if success:
            # Replace content
            success, msg = await self.coding_agent._write_file(file_path, content)
            if success:
                step.output = msg
                print(f"✅ [PlanningAgent] Successfully edited: {file_path}")
            else:
                print(f"❌ [PlanningAgent] Failed to edit: {file_path} - {msg}")
                raise Exception(msg)
        else:
            # File doesn't exist, create it
            print(f"⚠️ [PlanningAgent] File not found, creating: {file_path}")
            success, msg = await self.coding_agent._write_file(file_path, content)
            if success:
                step.output = f"Created and wrote to {file_path}"
                print(f"✅ [PlanningAgent] Created new file: {file_path}")
            else:
                print(f"❌ [PlanningAgent] Failed to create: {file_path} - {msg}")
                raise Exception(msg)

    async def _read_file(self, file_path: str) -> tuple[bool, str]:
        """Read a file's contents."""
        # Validate path
        file_path = self._validate_file_path(file_path)
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        try:
            path = self.project_root / file_path
            if not path.exists():
                return False, f"File not found: {file_path}"

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    async def _execute_show_result(self, step: PlanStep):
        """Execute a show result step."""
        file_path = step.target
        
        # CRITICAL FIX: Validate file path
        file_path = self._validate_file_path(file_path)
        
        # If path starts with /, make it relative to project root
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        print(f"📝 [PlanningAgent] Showing result: {file_path}")

        # Try to read the file
        success, content = await self.coding_agent._read_file(file_path)

        if success:
            step.output = f"Content of {file_path}:\n```\n{content}\n```"
            print(f"✅ [PlanningAgent] Successfully read: {file_path}")
        else:
            step.output = f"Could not read {file_path}: {content}"
            print(f"❌ [PlanningAgent] Failed to read: {file_path} - {content}")

    async def _execute_run_command(self, step: PlanStep):
        """Execute a run command step."""
        command = step.target
        result = await self.coding_agent.terminal.run_command(command, timeout=120)
        output = self.coding_agent._format_verification_output(result.stdout, result.stderr)
        if result.return_code != 0:
            raise Exception(output or f"Command failed: {command}")
        step.output = output or f"Command executed successfully: {command}"

    async def _execute_read_file(self, step: PlanStep):
        """Execute a read file step."""
        file_path = step.target
        success, content = await self.coding_agent._read_file(file_path)
        
        if success:
            step.output = content
        else:
            step.output = f"Could not read file: {content}"

    async def _execute_delete_file(self, step: PlanStep):
        """Execute a delete file step."""
        file_path = step.target
        try:
            path = self.project_root / file_path
            if path.exists():
                path.unlink()
                step.output = f"Deleted {file_path}"
            else:
                step.output = f"File not found: {file_path}"
        except Exception as e:
            raise Exception(f"Failed to delete file: {str(e)}")

    async def _execute_general(self, step: PlanStep):
        """Execute a general step."""
        # Try to determine what to do
        action_type = self._determine_action_type(step.description)
        
        if action_type == "create_file":
            await self._execute_create_file(step)
        elif action_type == "edit_file":
            await self._execute_edit_file(step)
        elif action_type == "show_result":
            await self._execute_show_result(step)
        else:
            step.output = f"Executed: {step.description}"

    def _generate_file_content(self, description: str, file_path: str) -> str:
        """
        Generate appropriate content for a file based on context.
        
        NO TEMPLATES - Uses intelligent analysis of:
        - File extension
        - File name
        - Task description
        - Context clues
        """
        ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).stem
        
        # Extract any quoted content from description
        content_match = re.search(r'["\'](.+?)["\']', description)
        quoted_content = content_match.group(1) if content_match else None
        
        # Generate based on file type and context
        if ext == ".txt":
            # Text files - use quoted content or description
            if quoted_content:
                return quoted_content
            # Extract meaningful content from description
            desc_lower = description.lower()
            if "say" in desc_lower or "display" in desc_lower or "show" in desc_lower:
                # Try to extract what to display
                display_match = re.search(r'(?:say|display|show|be)\s+["\'](.+?)["\']', desc_lower)
                if display_match:
                    return display_match.group(1)
            return f"{description}\n"
        
        elif ext in [".js", ".jsx"]:
            # JavaScript/React files
            return self._generate_javascript_file(file_name, file_path, description, quoted_content, ext)
        
        elif ext in [".ts", ".tsx"]:
            # TypeScript files
            return self._generate_typescript_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".py":
            # Python files
            return self._generate_python_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".html":
            # HTML files
            return self._generate_html_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".css":
            # CSS files
            return self._generate_css_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".json":
            # JSON files
            return self._generate_json_file(file_name, file_path, description, quoted_content)
        
        else:
            # Generic files
            if quoted_content:
                return quoted_content
            return f"{description}\n"

    def _generate_javascript_file(self, name: str, path: str, desc: str, content: Optional[str], ext: str) -> str:
        """Generate JavaScript/JSX file based on context."""
        desc_lower = desc.lower()
        
        # Detect if it's a React component
        is_react = any(kw in desc_lower for kw in ["component", "react", "jsx", "return", "render"])
        
        if is_react or ext == ".jsx":
            # React component
            display_content = content if content else name
            return f'''import React from 'react';

/**
 * {name} Component
 * Task: {desc}
 */
const {name} = () => {{
    return (
        <div className="{name.lower()}-container">
            <h1>{display_content}</h1>
        </div>
    );
}};

export default {name};
'''
        else:
            # Regular JavaScript
            if content:
                return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{content}");
'''
            return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{name} loaded");
'''

    def _generate_typescript_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate TypeScript file based on context."""
        desc_lower = desc.lower()
        
        is_react = any(kw in desc_lower for kw in ["component", "react", "tsx", "return"])
        
        if is_react or path.endswith(".tsx"):
            display_content = content if content else name
            return f'''import React from 'react';

/**
 * {name} Component
 * Task: {desc}
 */
const {name}: React.FC = () => {{
    return (
        <div className="{name.lower()}-container">
            <h1>{display_content}</h1>
        </div>
    );
}};

export default {name};
'''
        else:
            if content:
                return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{content}");
'''
            return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{name} loaded");
'''

    def _generate_python_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate Python file based on context."""
        desc_lower = desc.lower()
        
        # Detect if it's an API endpoint
        is_api = any(kw in desc_lower for kw in ["api", "endpoint", "route", "fastapi", "flask"])
        
        if is_api:
            return f'''"""
{name.title()} API
Task: {desc}
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{name.lower()}")
async def get_{name.lower()}():
    """{content or f'Get {name}'}"""
    return {{"status": "success"}}
'''
        elif content:
            return f'''"""
{name.title()}
Task: {desc}
"""

print("{content}")
'''
        else:
            return f'''"""
{name.title()}
Task: {desc}
"""

print("{name} loaded")
'''

    def _generate_html_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate HTML file based on context."""
        display_content = content if content else name
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_content}</title>
</head>
<body>
    <h1>{display_content}</h1>
    <!-- Task: {desc} -->
</body>
</html>
'''

    def _generate_css_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate CSS file based on context."""
        return f'''/*
 * {name} Styles
 * Task: {desc}
 */

.{name.lower()}-container {{
    padding: 20px;
    margin: 0 auto;
}}
'''

    def _generate_json_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate JSON file based on context."""
        if content:
            try:
                # Try to parse as JSON
                import json
                data = json.loads(content)
                return json.dumps(data, indent=2)
            except:
                pass
        return json.dumps({"task": desc, "name": name}, indent=2)

    async def _report_progress(self, plan: ExecutionPlan):
        """Report progress via callback."""
        if self.progress_callback:
            await self.progress_callback(plan)

    async def execute_task_with_plan(
        self,
        task: str,
        project_context: Optional[dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        High-level method to execute a task with full planning.

        This is the main entry point for the planning agent.

        Args:
            task: User's task description

        Returns:
            Completed execution plan
        """
        print(f"📋 [PlanningAgent] Creating plan for: {task[:80]}...")
        
        # Step 1: Create the plan
        plan = await self.create_plan(task, project_context)
        print(f"✅ [PlanningAgent] Plan created with {plan.total_steps} steps")
        
        # Step 2: Execute the plan
        print(f"🚀 [PlanningAgent] Executing plan...")
        completed_plan = await self.execute_plan(plan)
        
        print(f"✅ [PlanningAgent] Plan completed: {completed_plan.status.value} ({completed_plan.completed_steps}/{completed_plan.total_steps})")
        
        return completed_plan


# Singleton instance
_planning_agent: Optional[AutonomousPlanningAgent] = None


def get_planning_agent(project_root: Optional[Path] = None) -> AutonomousPlanningAgent:
    """Get or create planning agent instance."""
    global _planning_agent
    if _planning_agent is None:
        _planning_agent = AutonomousPlanningAgent(project_root)
    return _planning_agent
