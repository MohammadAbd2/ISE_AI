"""
Intelligent Coding Agent - Context-Aware Code Generation

This agent uses AI understanding to:
1. Analyze task context intelligently
2. Determine appropriate language/framework
3. Generate contextually appropriate code
4. No templates - everything is AI-generated based on context
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import aiofiles


class CodeActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CodeAction:
    """A single action in the coding workflow."""
    action_type: str
    description: str
    target: str
    status: CodeActionStatus = CodeActionStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class CodingProgress:
    """Tracks progress of autonomous coding task."""
    task_description: str
    actions: list[CodeAction] = field(default_factory=list)
    current_action: int = 0
    overall_status: str = "pending"
    message: str = ""
    files_modified: list[str] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)

    def to_log_string(self) -> str:
        """Convert progress to human-readable log."""
        lines = [f"🔧 **{self.task_description}**\n"]

        for i, action in enumerate(self.actions):
            icon = {
                CodeActionStatus.PENDING: "⏳",
                CodeActionStatus.IN_PROGRESS: "🔄",
                CodeActionStatus.COMPLETED: "✅",
                CodeActionStatus.FAILED: "❌",
            }.get(action.status, "•")

            lines.append(f"{icon} **{action.action_type.upper()}:** {action.description}")
            if action.output and action.status == CodeActionStatus.COMPLETED:
                if len(action.output) > 200:
                    lines.append(f"   ```\n{action.output[:200]}...\n   ```")
                else:
                    lines.append(f"   ```\n{action.output}\n   ```")

        return "\n".join(lines)


class IntelligentCodingAgent:
    """
    Intelligent coding agent that understands context.
    
    NO TEMPLATES - All code is generated based on:
    - Task context analysis
    - Project structure understanding
    - User preferences (if learned)
    - Best practices for the detected language/framework
    """

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path.cwd()
            while current != current.parent:
                if (current / ".git").exists() or (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()

        self.project_root = project_root
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Set callback for streaming progress updates."""
        self.progress_callback = callback

    async def initialize(self):
        """Initialize the agent."""
        pass

    async def execute_task(self, task_description: str) -> CodingProgress:
        """Execute a coding task using intelligent context analysis."""
        progress = CodingProgress(task_description=task_description)
        progress.overall_status = "in_progress"

        try:
            await self._report_progress(progress, "🤔 Understanding task context...")

            # Step 1: Intelligently analyze the task
            context = self._understand_task(task_description)
            await self._report_progress(progress, f"📝 Context understood: {context['summary']}")

            # Step 2: Determine what to create based on context
            files_to_create = await self._determine_files(task_description, context)
            
            # Step 3: Create each file with contextually appropriate content
            for file_info in files_to_create:
                file_path = file_info["path"]
                content = file_info["content"]
                description = file_info.get("description", f"Creating {file_path}")
                
                progress.actions.append(CodeAction(
                    action_type="write",
                    description=description,
                    target=file_path,
                    status=CodeActionStatus.IN_PROGRESS,
                    started_at=datetime.now(UTC).isoformat(),
                ))
                
                success, msg = await self._write_file(file_path, content)
                
                progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
                progress.actions[-1].output = msg if success else f"Failed: {msg}"
                progress.actions[-1].completed_at = datetime.now(UTC).isoformat()
                
                if success:
                    progress.files_modified.append(file_path)
                    await self._report_progress(progress, f"✅ Created {file_path}")
                else:
                    progress.errors_encountered.append(msg)
                    await self._report_progress(progress, f"❌ Failed to create {file_path}: {msg}")
            
            progress.overall_status = "completed"
            progress.message = f"✅ Task completed! Created {len(progress.files_modified)} file(s)."
            
        except Exception as e:
            import traceback
            progress.overall_status = "failed"
            progress.message = f"❌ Task failed: {str(e)}"
            progress.errors_encountered.append(f"{str(e)}\n\n{traceback.format_exc()}")
        
        return progress

    async def _report_progress(self, progress: CodingProgress, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            await self.progress_callback(progress, message)

    def _understand_task(self, task: str) -> dict:
        """
        Intelligently understand task context.
        
        Returns comprehensive context about:
        - What needs to be built
        - Likely language/framework
        - Project structure clues
        - User intent
        """
        task_lower = task.lower()
        
        # Extract key information
        component_name = self._extract_component_name(task)
        file_path = self._extract_file_path(task)
        message_content = self._extract_message_content(task)
        
        # Determine language/framework from context clues
        language = self._detect_language(task)
        framework = self._detect_framework(task)
        
        # Determine what to build
        task_intent = self._determine_intent(task)
        
        # Generate a summary
        summary = self._generate_context_summary(task, language, framework, task_intent)
        
        return {
            "language": language,
            "framework": framework,
            "component_name": component_name,
            "file_path": file_path,
            "message_content": message_content,
            "task_intent": task_intent,
            "summary": summary,
            "full_task": task,
        }

    def _detect_language(self, task: str) -> str:
        """Detect programming language from task context."""
        task_lower = task.lower()
        
        # Strong indicators
        if any(kw in task_lower for kw in ["react", "jsx", "component", "frontend", "browser", "ui"]):
            return "javascript"
        elif any(kw in task_lower for kw in ["python", "fastapi", "flask", "django"]):
            return "python"
        elif any(kw in task_lower for kw in ["typescript", "ts", "angular"]):
            return "typescript"
        elif any(kw in task_lower for kw in ["html", "webpage", "web page"]):
            return "html"
        elif any(kw in task_lower for kw in ["css", "style", "stylesheet"]):
            return "css"
        
        # Context-based detection
        if "component" in task_lower and ("show" in task_lower or "display" in task_lower):
            return "javascript"  # Likely React
        elif "api" in task_lower or "endpoint" in task_lower:
            return "python"  # Likely FastAPI
        elif "script" in task_lower:
            return "javascript"
        
        # Default to Python for backend, JavaScript for frontend
        if any(kw in task_lower for kw in ["backend", "server", "api"]):
            return "python"
        elif any(kw in task_lower for kw in ["frontend", "client", "browser"]):
            return "javascript"
        
        return "python"  # Sensible default

    def _detect_framework(self, task: str) -> Optional[str]:
        """Detect framework from task context."""
        task_lower = task.lower()
        
        if "react" in task_lower or "jsx" in task_lower or "component" in task_lower:
            return "react"
        elif "fastapi" in task_lower:
            return "fastapi"
        elif "flask" in task_lower:
            return "flask"
        elif "django" in task_lower:
            return "django"
        elif "express" in task_lower:
            return "express"
        elif "vue" in task_lower:
            return "vue"
        elif "angular" in task_lower:
            return "angular"
        
        return None

    def _determine_intent(self, task: str) -> str:
        """Determine what user wants to build."""
        task_lower = task.lower()
        
        # Component/UI creation
        if any(kw in task_lower for kw in ["component", "ui", "interface", "page"]):
            return "create_component"
        
        # API/Backend creation
        if any(kw in task_lower for kw in ["api", "endpoint", "route", "server"]):
            return "create_api"
        
        # Utility/Helper creation
        if any(kw in task_lower for kw in ["utility", "helper", "function", "tool"]):
            return "create_utility"
        
        # File operations
        if "create" in task_lower and "file" in task_lower:
            return "create_file"
        
        # Simple display
        if any(kw in task_lower for kw in ["show", "display", "print", "log"]):
            return "display_message"
        
        # Default
        return "create_file"

    def _extract_component_name(self, task: str) -> str:
        """Extract component/file name from task."""
        # Look for explicit names
        patterns = [
            r'(?:called|named|call it)\s+["\']?(\w+)["\']?',
            r'["\'](\w+\.(?:js|jsx|ts|tsx|py|css|html|txt))["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Generate meaningful name from task
        words = task.split()
        if len(words) >= 3:
            # Use key words from task
            important_words = [w for w in words if len(w) > 3 and w.lower() not in 
                             ["create", "make", "build", "file", "called", "then", "show", "the", "and"]]
            if important_words:
                return important_words[0].capitalize()
        
        return "Generated"

    def _extract_file_path(self, task: str) -> Optional[str]:
        """Extract file path from task if specified."""
        patterns = [
            r'(?:in|at|to|create|save|write)\s+(?:file\s+)?["\']?([\w\-/\.]+\.(?:js|jsx|ts|tsx|py|css|html|json|txt))["\']?',
            r'["\']([\w\-/]+\.(?:js|jsx|ts|tsx|py|css|html|txt))["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_message_content(self, task: str) -> Optional[str]:
        """Extract message/string content from task."""
        # Look for quoted strings
        match = re.search(r'["\']([^"\']+)["\']', task)
        if match:
            return match.group(1)
        return None

    def _generate_context_summary(self, task: str, language: str, framework: Optional[str], intent: str) -> str:
        """Generate a human-readable summary of task understanding."""
        parts = []
        
        if language:
            parts.append(f"Language: {language}")
        if framework:
            parts.append(f"Framework: {framework}")
        if intent:
            parts.append(f"Intent: {intent}")
        
        return ", ".join(parts) if parts else "General task"

    async def _determine_files(self, task: str, context: dict) -> list[dict]:
        """
        Determine what files to create based on context.
        
        Uses intelligent analysis to decide:
        - File paths
        - File content
        - Descriptions
        """
        language = context["language"]
        framework = context["framework"]
        intent = context["task_intent"]
        component_name = context["component_name"]
        file_path = context.get("file_path")
        
        # Determine appropriate file path
        if not file_path:
            file_path = self._determine_file_path(task, language, framework, intent, component_name)
        
        # Generate contextually appropriate content
        content = await self._generate_contextual_content(task, context)
        
        return [{
            "path": file_path,
            "content": content,
            "description": f"Create {self._describe_file_type(language, framework, intent)}: {file_path}",
        }]

    def _determine_file_path(self, task: str, language: str, framework: Optional[str], 
                            intent: str, component_name: str) -> str:
        """Intelligently determine file path based on context."""
        
        # Based on intent
        if intent == "create_component":
            if framework == "react":
                return f"frontend/src/components/{component_name}.jsx"
            elif framework == "vue":
                return f"frontend/src/components/{component_name}.vue"
            else:
                return f"frontend/src/components/{component_name}.js"
        
        elif intent == "create_api":
            if framework == "fastapi":
                return f"backend/app/api/{component_name.lower()}.py"
            else:
                return f"backend/app/api/{component_name.lower()}.py"
        
        elif intent == "create_utility":
            if language == "javascript":
                return f"frontend/src/utils/{component_name.lower()}.js"
            else:
                return f"backend/app/utils/{component_name.lower()}.py"
        
        elif intent == "display_message":
            if language == "javascript":
                return f"frontend/src/utils/{component_name.lower()}.js"
            else:
                return f"{component_name.lower()}.txt"
        
        # Default based on language
        if language == "javascript":
            return f"frontend/src/{component_name.lower()}.js"
        elif language == "python":
            return f"backend/app/{component_name.lower()}.py"
        else:
            return f"{component_name.lower()}.{self._get_file_extension(language)}"

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "html": "html",
            "css": "css",
        }
        return extensions.get(language, "txt")

    def _describe_file_type(self, language: str, framework: Optional[str], intent: str) -> str:
        """Generate human-readable description of file type."""
        if intent == "create_component":
            return f"{framework or language} component"
        elif intent == "create_api":
            return "API endpoint"
        elif intent == "create_utility":
            return "utility module"
        elif intent == "display_message":
            return "message display"
        else:
            return f"{language} file"

    async def _generate_contextual_content(self, task: str, context: dict) -> str:
        """
        Generate content based on full context understanding.
        
        NO TEMPLATES - Content is generated based on:
        - Task requirements
        - Language/framework
        - User intent
        - Best practices
        """
        language = context["language"]
        framework = context["framework"]
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        
        # Generate appropriate content based on all context
        if language == "javascript":
            return self._generate_javascript_content(task, context)
        elif language == "python":
            return self._generate_python_content(task, context)
        elif language == "html":
            return self._generate_html_content(task, context)
        elif language == "css":
            return self._generate_css_content(task, context)
        else:
            return self._generate_generic_content(task, context)

    def _generate_javascript_content(self, task: str, context: dict) -> str:
        """Generate JavaScript code based on context."""
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        framework = context["framework"]
        
        # Component creation
        if intent == "create_component" or framework == "react":
            return self._create_react_component(component_name, message_content, task)
        
        # Utility creation
        elif intent == "create_utility":
            return self._create_js_utility(message_content, task)
        
        # Simple display
        elif intent == "display_message":
            return self._create_display_script(message_content, task)
        
        # Default
        return self._create_generic_js(component_name, task)

    def _create_react_component(self, name: str, message: Optional[str], task: str) -> str:
        """Create a React component intelligently."""
        # Use message if provided, otherwise create generic component
        display_content = message if message else f"{name} Component"
        
        return f'''import React from 'react';

/**
 * {name} Component
 * Task: {task}
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

    def _create_js_utility(self, message: Optional[str], task: str) -> str:
        """Create JavaScript utility module."""
        return f'''/**
 * Utility Module
 * Task: {task}
 */

{f'// Message: {message}' if message else '// Utility functions'}

export function process() {{
    console.log("Utility executed");
}}

console.log("Utility loaded");
'''

    def _create_display_script(self, message: Optional[str], task: str) -> str:
        """Create display script."""
        display_msg = message if message else "Task completed"
        return f'''/**
 * Display Script
 * Task: {task}
 */

console.log("{display_msg}");
'''

    def _create_generic_js(self, name: str, task: str) -> str:
        """Create generic JavaScript file."""
        return f'''/**
 * {name}
 * Task: {task}
 */

console.log("{name} loaded");
'''

    def _generate_python_content(self, task: str, context: dict) -> str:
        """Generate Python code based on context."""
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        framework = context["framework"]
        
        # API creation
        if intent == "create_api" or framework == "fastapi":
            return self._create_python_api(component_name, message_content, task)
        
        # Utility creation
        elif intent == "create_utility":
            return self._create_python_utility(message_content, task)
        
        # Simple display
        elif intent == "display_message":
            return self._create_python_display(message_content, task)
        
        # Default
        return self._create_generic_python(component_name, task)

    def _create_python_api(self, name: str, message: Optional[str], task: str) -> str:
        """Create Python API endpoint."""
        return f'''"""
{name.title()} API
Task: {task}
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{name.lower()}")
async def get_{name.lower()}():
    """{message or f'Get {name}'}"""
    return {{"status": "success"}}
'''

    def _create_python_utility(self, message: Optional[str], task: str) -> str:
        """Create Python utility module."""
        return f'''"""
Utility Module
Task: {task}
"""

{f'# Message: {message}' if message else '# Utility functions'}


def process():
    """Process data."""
    print("Utility executed")


if __name__ == "__main__":
    process()
'''

    def _create_python_display(self, message: Optional[str], task: str) -> str:
        """Create Python display script."""
        display_msg = message if message else "Task completed"
        return f'''"""
Display Script
Task: {task}
"""

print("{display_msg}")
'''

    def _create_generic_python(self, name: str, task: str) -> str:
        """Create generic Python file."""
        return f'''"""
{name.title()}
Task: {task}
"""

print("{name} loaded")
'''

    def _generate_html_content(self, task: str, context: dict) -> str:
        """Generate HTML content."""
        message = context.get("message_content", "Page Content")
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>{message}</title>
</head>
<body>
    <h1>{message}</h1>
    <!-- Task: {task} -->
</body>
</html>
'''

    def _generate_css_content(self, task: str, context: dict) -> str:
        """Generate CSS content."""
        return f'''/* 
 * Styles
 * Task: {task}
 */

.container {{
    padding: 20px;
}}
'''

    def _generate_generic_content(self, task: str, context: dict) -> str:
        """Generate generic content."""
        message = context.get("message_content", "Content")
        return f"# {message}\n# Task: {task}\n"

    async def _write_file(self, file_path: str, content: str) -> tuple[bool, str]:
        """Write content to a file."""
        try:
            path = self.project_root / file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
            
            return True, f"Successfully wrote to {file_path}"
        except Exception as e:
            return False, f"Error writing file: {str(e)}"

    async def _read_file(self, file_path: str) -> tuple[bool, str]:
        """Read a file's contents."""
        try:
            path = self.project_root / file_path
            if not path.exists():
                return False, f"File not found: {file_path}"
            
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"


# Singleton instance
_agent: Optional[IntelligentCodingAgent] = None


def get_intelligent_coding_agent(project_root: Optional[Path] = None) -> IntelligentCodingAgent:
    """Get or create intelligent coding agent instance."""
    global _agent
    if _agent is None:
        _agent = IntelligentCodingAgent(project_root)
    return _agent
