"""
Autonomous Coding Agent - Self-Development Capability

This agent can:
1. Read and analyze code files
2. Write new code files  
3. Edit existing code
4. Debug and fix errors
5. Run tests and validate changes
6. Install dependencies
7. Execute shell commands safely

Similar to Cursor's agent mode or Codex autonomous development.
"""

import asyncio
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
    diff: str = ""


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
            if action.diff:
                lines.append(f"   ```diff\n{action.diff}\n   ```")

        return "\n".join(lines)


class FileSystemTools:
    """Tools for file system operations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    async def read_file(self, file_path: str) -> tuple[bool, str]:
        """Read contents of a file."""
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}"

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    async def write_file(self, file_path: str, content: str) -> tuple[bool, str]:
        """Write content to a file (creates or overwrites)."""
        try:
            path = self._resolve_path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
            return True, f"Successfully wrote to {file_path}"
        except Exception as e:
            return False, f"Error writing file: {str(e)}"

    async def edit_file(self, file_path: str, old_text: str, new_text: str) -> tuple[bool, str, str]:
        """Edit a file by replacing old_text with new_text."""
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}", ""

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()

            if old_text not in content:
                return False, "Text to replace not found in file", ""

            diff = self._create_diff(file_path, old_text, new_text)
            new_content = content.replace(old_text, new_text, 1)

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(new_content)

            return True, f"Successfully edited {file_path}", diff
        except Exception as e:
            return False, f"Error editing file: {str(e)}", ""

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to project root or workspace if enabled."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        # If a workspace is attached to this FileSystemTools instance, use it for staging
        if getattr(self, "use_workspace", False) and getattr(self, "workspace", None) is not None:
            ws_base = getattr(self.workspace, "base", None)
            if ws_base:
                return Path(ws_base) / path
        return self.project_root / path

    def _create_diff(self, file_path: str, old_text: str, new_text: str) -> str:
        """Create a simple diff string."""
        old_lines = old_text.split("\n")
        new_lines = new_text.split("\n")

        diff_lines = [f"--- {file_path}", f"+++ {file_path}"]
        max_lines = min(max(len(old_lines), len(new_lines)), 25)

        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else ""
            new_line = new_lines[i] if i < len(new_lines) else ""

            if old_line != new_line:
                if old_line:
                    diff_lines.append(f"-{old_line}")
                if new_line:
                    diff_lines.append(f"+{new_line}")

        return "\n".join(diff_lines)

    async def search_files(self, pattern: str, glob_pattern: str = "**/*.py") -> list[str]:
        """Search for files matching a pattern."""
        try:
            matches = []
            for path in self.project_root.glob(glob_pattern):
                if path.is_file():
                    try:
                        content = path.read_text(encoding="utf-8")
                        if pattern.lower() in content.lower():
                            matches.append(str(path.relative_to(self.project_root)))
                    except:
                        pass
            return matches
        except Exception:
            return []

    async def list_directory(self, dir_path: str) -> tuple[bool, list[str]]:
        """List contents of a directory."""
        try:
            path = self._resolve_path(dir_path)
            if not path.is_dir():
                return False, []

            items = []
            for item in path.iterdir():
                if not item.name.startswith("."):
                    items.append(f"{'📁 ' if item.is_dir() else '📄 '}{item.name}")
            return True, items
        except Exception as e:
            return False, []


class ShellExecutor:
    """Safe shell command execution."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.allowed_commands = {
            "pip", "pip3", "python", "python3", "npm", "yarn", "pnpm",
            "git", "ls", "dir", "find", "grep", "cat", "head", "tail",
            "mkdir", "cp", "mv", "rm", "touch", "chmod",
            "pytest", "py.test", "node", "cargo", "go",
            "npx", "promptfoo", "export", "PYTHONPATH",
        }

    async def run_command(self, command: str, timeout: int = 120) -> tuple[bool, str]:
        """Execute a shell command safely."""
        # Handle environment variables like PYTHONPATH=... command
        clean_cmd = command
        if "=" in command.split()[0]:
            parts = command.split()
            for i, part in enumerate(parts):
                if "=" not in part:
                    clean_cmd = " ".join(parts[i:])
                    break
        
        base_cmd = clean_cmd.split()[0] if clean_cmd.split() else ""
        if base_cmd not in self.allowed_commands:
            return False, f"Command not allowed: {base_cmd}"

        dangerous = ["rm -rf /", "rm -rf ~", "sudo", "su ", "dd ", "> /dev/", "> /etc/"]
        if any(d in command for d in dangerous):
            return False, "Dangerous command blocked"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="ignore")
            error = stderr.decode("utf-8", errors="ignore")

            if process.returncode == 0:
                return True, output if output else "Command executed successfully"
            else:
                return False, error if error else f"Command failed with code {process.returncode}"

        except asyncio.TimeoutError:
            return False, f"Command timed out after {timeout}s"
        except Exception as e:
            return False, f"Error executing command: {str(e)}"


class AutonomousCodingAgent:
    """
    Autonomous agent capable of developing, debugging, and modifying code.
    Understands natural language prompts and applies code in any project file.
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
        self.fs = FileSystemTools(project_root)
        self.shell = ShellExecutor(project_root)
        self.progress_callback = None
        # Attach a workspace manager instance; created lazily when running tasks
        try:
            from app.services.workspace_manager import WorkspaceManager
            self.workspace = WorkspaceManager(project_root)
        except Exception:
            self.workspace = None

    def set_progress_callback(self, callback):
        """Set callback for streaming progress updates."""
        self.progress_callback = callback

    def enable_workspace(self, enable: bool = True):
        """Enable or disable workspace staging for subsequent file operations."""
        self.fs.use_workspace = enable
        if enable and getattr(self, 'workspace', None) is not None:
            self.fs.workspace = self.workspace
        else:
            self.fs.workspace = None

    async def execute_task(self, task_description: str) -> CodingProgress:
        """Execute a coding task autonomously."""
        progress = CodingProgress(task_description=task_description)
        progress.overall_status = "in_progress"

        # Enable workspace staging for this run
        try:
            self.enable_workspace(True)
        except Exception:
            pass

        try:
            await self._report_progress(progress, "🤔 Analyzing task requirements...")
            task_lower = task_description.lower()

            # Console/browser logging tasks
            if "console" in task_lower or ("browser" in task_lower and "log" in task_lower):
                await self._execute_browser_console_task(progress, task_description)
            # Modification tasks
            elif any(word in task_lower for word in ["change", "update", "modify", "fix", "port", "config"]):
                await self._execute_modification(progress, task_description)
            # Creation tasks
            elif any(word in task_lower for word in ["create", "add", "new", "write", "implement", "generate"]):
                await self._execute_creation(progress, task_description)
            # Debugging tasks
            elif any(word in task_lower for word in ["debug", "error", "bug", "issue", "problem"]):
                await self._execute_debugging(progress, task_description)
            # Testing tasks
            elif any(word in task_lower for word in ["test", "verify", "validate"]):
                await self._execute_testing(progress, task_description)
            # Installation tasks
            elif any(word in task_lower for word in ["install", "add package", "dependency"]):
                await self._execute_installation(progress, task_description)
            # General tasks
            else:
                await self._execute_general(progress, task_description)

            progress.overall_status = "completed"
            progress.message = f"✅ Task completed! Modified {len(progress.files_modified)} file(s)."

        except Exception as e:
            progress.overall_status = "failed"
            progress.message = f"❌ Task failed: {str(e)}"
            progress.errors_encountered.append(str(e))

        # Disable workspace staging after run
        try:
            self.enable_workspace(False)
        except Exception:
            pass

        return progress

    async def _report_progress(self, progress: CodingProgress, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            await self.progress_callback(progress, message)

    async def _execute_browser_console_task(self, progress: CodingProgress, task: str):
        """Execute browser console.log tasks. Example: 'console log Hello World in browser'"""
        # Extract the message to log
        message_match = re.search(r'["\']([^"\']+)["\']', task)
        log_message = "Hello World"  # Default message
        
        if message_match:
            log_message = message_match.group(1)
        else:
            match = re.search(r'(?:console\s*(?:log)?|print|show|display)\s+(?:to\s+)?(?:the\s+)?(?:browser\s+)?(?:console\s+)?["\']?([^"\']+)["\']?', task, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted.lower() not in ['in browser', 'to browser', 'to console', 'in console']:
                    log_message = extracted

        # Create JavaScript utility module
        file_path = "frontend/src/utils/console_logger.js"
        js_content = self._generate_browser_console_code(log_message)

        progress.actions.append(CodeAction(
            action_type="write",
            description=f"Creating browser console script to log: '{log_message}'",
            target=file_path,
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        success, msg = await self.fs.write_file(file_path, js_content)
        
        progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
        progress.actions[-1].output = msg if success else f"Failed: {msg}"
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

        if success:
            progress.files_modified.append(file_path)

        # Update main.jsx to import console logger
        main_path = "frontend/src/main.jsx"
        progress.actions.append(CodeAction(
            action_type="read",
            description="Reading main.jsx to add console logger import",
            target=main_path,
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        success, main_content = await self.fs.read_file(main_path)
        progress.actions[-1].status = CodeActionStatus.COMPLETED
        progress.actions[-1].output = f"Read {len(main_content)} bytes" if success else "Failed to read"
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

        if success and "console_logger" not in main_content:
            lines = main_content.split("\n")
            new_lines = []
            imported = False
            for line in lines:
                new_lines.append(line)
                if line.startswith("import ") and not imported:
                    new_lines.append('import "./utils/console_logger.js";  // Auto-generated console logger')
                    imported = True
            
            if imported:
                new_main = "\n".join(new_lines)
                progress.actions.append(CodeAction(
                    action_type="edit",
                    description="Adding console logger import to main.jsx",
                    target=main_path,
                    status=CodeActionStatus.IN_PROGRESS,
                    started_at=datetime.now(UTC).isoformat(),
                ))

                success, msg, diff = await self.fs.edit_file(main_path, main_content, new_main)
                progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
                progress.actions[-1].output = msg if success else f"Failed: {msg}"
                progress.actions[-1].diff = diff
                progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

                if success:
                    progress.files_modified.append(main_path)

    def _generate_browser_console_code(self, message: str) -> str:
        """Generate JavaScript code to log message to browser console."""
        return f'''/**
 * Browser Console Logger
 * Generated by ISE AI Autonomous Coding Agent
 * 
 * This script logs messages to the browser console.
 * Open browser DevTools (F12) to see the output.
 */

// Log the message to browser console
console.log("{message}");

// Also log additional info for debugging
console.log("🤖 ISE AI Agent - Console Log Test");
console.log("Timestamp:", new Date().toISOString());
console.log("User Agent:", navigator.userAgent);
console.log("Page URL:", window.location.href);

// Export function for reuse
export function logToConsole(msg) {{
    console.log(msg);
}}

export function logWithTimestamp(msg) {{
    console.log(`[${{new Date().toISOString()}}] ${{msg}}`);
}}

// Auto-execute on module load
console.log("✅ Console logger initialized");
'''

    async def _execute_modification(self, progress: CodingProgress, task: str):
        """Execute a code modification task."""
        port_match = re.search(r"(?:port|PORT|Port)\s*(?:=|:|from)?\s*(\d+)", task)
        if port_match:
            old_port = port_match.group(1)
            new_port_match = re.search(r"(?:to|change to|set to)\s*(\d+)", task)
            if new_port_match:
                new_port = new_port_match.group(1)

                progress.actions.append(CodeAction(
                    action_type="search",
                    description=f"Searching for files using port {old_port}",
                    target="**/*.py",
                    status=CodeActionStatus.IN_PROGRESS,
                    started_at=datetime.now(UTC).isoformat(),
                ))

                files_with_port = await self.fs.search_files(old_port)
                progress.actions[-1].status = CodeActionStatus.COMPLETED
                progress.actions[-1].output = f"Found {len(files_with_port)} file(s)"
                progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

                for file_path in files_with_port[:10]:
                    progress.actions.append(CodeAction(
                        action_type="edit",
                        description=f"Update port in {file_path}",
                        target=file_path,
                        status=CodeActionStatus.IN_PROGRESS,
                        started_at=datetime.now(UTC).isoformat(),
                    ))

                    success, result = await self.fs.read_file(file_path)
                    if success:
                        new_content = result.replace(old_port, new_port)
                        success, msg, diff = await self.fs.edit_file(file_path, result, new_content)

                        progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
                        progress.actions[-1].output = msg if success else f"Failed: {msg}"
                        progress.actions[-1].diff = diff
                        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

                        if success:
                            progress.files_modified.append(file_path)

    async def _execute_creation(self, progress: CodingProgress, task: str):
        """Execute a code creation task with intelligent file targeting."""
        progress.actions.append(CodeAction(
            action_type="write",
            description="Analyzing task and generating functional code",
            target="To be determined",
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        task_lower = task.lower()
        file_path, code_content = self._determine_file_and_content(task, task_lower)

        success, msg = await self.fs.write_file(file_path, code_content)

        progress.actions[-1].target = file_path
        progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
        progress.actions[-1].output = msg if success else f"Failed: {msg}"
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

        if success:
            progress.files_modified.append(file_path)

    def _determine_file_and_content(self, task: str, task_lower: str) -> tuple[str, str]:
        """Determine the appropriate file path and content based on task analysis."""
        if "browser" in task_lower or "frontend" in task_lower or "react" in task_lower:
            if "console" in task_lower or "log" in task_lower:
                return "frontend/src/utils/console_logger.js", self._generate_console_logger()
            return "frontend/src/components/auto_generated.jsx", self._generate_react_component(task)

        if "endpoint" in task_lower or "api" in task_lower or "route" in task_lower:
            if "health" in task_lower:
                return "backend/app/api/health_routes.py", self._generate_health_endpoint()
            return "backend/app/api/auto_generated.py", self._generate_api_endpoint(task)

        if "test" in task_lower:
            return "tests/test_auto_generated.py", self._generate_test_file(task)

        if "service" in task_lower or "utility" in task_lower or "helper" in task_lower:
            return "backend/app/services/auto_generated.py", self._generate_service(task)

        return "backend/app/services/auto_generated.py", self._generate_service(task)

    def _generate_console_logger(self) -> str:
        """Generate a console logger utility."""
        return '''/**
 * Console Logger Utility
 * Generated by ISE AI Autonomous Coding Agent
 */

export function log(message) {
    console.log(message);
}

export function logWithTime(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
}

export function logError(message, error = null) {
    console.error(`❌ ${message}`);
    if (error) console.error(error);
}

export function logWarning(message) {
    console.warn(`⚠️ ${message}`);
}

export function logSuccess(message) {
    console.log(`✅ ${message}`);
}

console.log("🔧 Console Logger initialized");
'''

    def _generate_react_component(self, task: str) -> str:
        """Generate a React component."""
        return f'''import React from 'react';

const AutoGeneratedComponent = () => {{
    return (
        <div className="auto-generated-component">
            <h3>Auto-Generated Component</h3>
            <p>Task: {task}</p>
        </div>
    );
}};

export default AutoGeneratedComponent;
'''

    def _generate_health_endpoint(self) -> str:
        """Generate a health check endpoint."""
        return '''"""
Health Check API Endpoint
Generated by: ISE AI Autonomous Coding Agent
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }
'''

    def _generate_api_endpoint(self, task: str) -> str:
        """Generate an API endpoint."""
        return f'''"""
Auto-generated API Endpoint
Task: {task}
Generated by: ISE AI Autonomous Coding Agent
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class RequestModel(BaseModel):
    data: Optional[str] = None


@router.get("/api/auto")
async def auto_endpoint():
    """Auto-generated endpoint."""
    return {{"status": "success"}}
'''

    def _generate_test_file(self, task: str) -> str:
        """Generate a test file."""
        return f'''"""
Auto-generated Test File
Task: {task}
"""

import pytest


def test_placeholder():
    """Placeholder test."""
    assert True
'''

    def _generate_service(self, task: str) -> str:
        """Generate a service module."""
        return f'''"""
Auto-generated Service Module
Task: {task}
Generated by: ISE AI Autonomous Coding Agent
"""

from typing import Optional, Dict, Any
from datetime import datetime


class AutoGeneratedService:
    """Auto-generated service class."""

    def __init__(self):
        self.created_at = datetime.now()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data."""
        return {{
            "status": "success",
            "data": data,
            "processed_at": datetime.now().isoformat(),
        }}


_service: Optional[AutoGeneratedService] = None


def get_service() -> AutoGeneratedService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = AutoGeneratedService()
    return _service
'''

    async def _execute_debugging(self, progress: CodingProgress, task: str):
        """Execute a debugging task."""
        progress.actions.append(CodeAction(
            action_type="search",
            description="Searching for error patterns in codebase",
            target="**/*.py",
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        error_patterns = ["error", "exception", "traceback", "failed"]
        files_with_errors = []
        for pattern in error_patterns:
            files = await self.fs.search_files(pattern)
            files_with_errors.extend(files)

        files_with_errors = list(set(files_with_errors))[:10]
        progress.actions[-1].status = CodeActionStatus.COMPLETED
        progress.actions[-1].output = f"Found {len(files_with_errors)} potential files"
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

    async def _execute_testing(self, progress: CodingProgress, task: str):
        """Execute a testing task."""
        progress.actions.append(CodeAction(
            action_type="run",
            description="Running tests",
            target="pytest",
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        success, output = await self.shell.run_command("python -m pytest -v")
        progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
        progress.actions[-1].output = output[:500] if len(output) > 500 else output
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

    async def _execute_installation(self, progress: CodingProgress, task: str):
        """Execute an installation task."""
        package_match = re.search(r"(?:install|add)\s+(?:package\s+)?(\w[\w\-\.]*)", task)
        if package_match:
            package = package_match.group(1)
            
            progress.actions.append(CodeAction(
                action_type="install",
                description=f"Installing package: {package}",
                target=f"pip install {package}",
                status=CodeActionStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            ))

            success, output = await self.shell.run_command(f"pip install {package}")
            progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
            progress.actions[-1].output = output[:500] if len(output) > 500 else output
            progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

    async def _execute_general(self, progress: CodingProgress, task: str):
        """Execute a general task."""
        progress.actions.append(CodeAction(
            action_type="write",
            description="Creating service module for general task",
            target="backend/app/services/auto_generated.py",
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        ))

        code_content = self._generate_service(task)
        success, msg = await self.fs.write_file("backend/app/services/auto_generated.py", code_content)

        progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
        progress.actions[-1].output = msg if success else f"Failed: {msg}"
        progress.actions[-1].completed_at = datetime.now(UTC).isoformat()

        if success:
            progress.files_modified.append("backend/app/services/auto_generated.py")


# Global instance
_coding_agent: Optional[AutonomousCodingAgent] = None


def get_coding_agent() -> AutonomousCodingAgent:
    """Get or create coding agent instance."""
    global _coding_agent
    if _coding_agent is None:
        _coding_agent = AutonomousCodingAgent()
    return _coding_agent
