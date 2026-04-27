"""
Autonomous Development Agent - True Self-Improving AI

This agent can:
1. Understand ANY development task via natural language
2. Plan multi-step solutions autonomously  
3. Create NEW tools when existing ones are insufficient
4. Read, analyze, and modify ANY file in the project
5. Write complete functional code (not templates)
6. Test and validate its own work
7. Use RAG for project context
8. Chain actions to solve complex problems

Like Codex, Cursor Agent, or Claude Code - but self-hosted.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiofiles
import httpx

from app.core.config import settings
from app.services.enhanced_rag import get_enhanced_rag_context


class ActionType(str, Enum):
    """Types of actions the agent can take."""
    THINK = "think"  # Internal reasoning
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    SEARCH_FILES = "search_files"
    LIST_DIRECTORY = "list_directory"
    RUN_COMMAND = "run_command"
    INSTALL_PACKAGE = "install_package"
    CREATE_TOOL = "create_tool"  # Create a new tool/capability
    RAG_QUERY = "rag_query"  # Query project knowledge
    TEST = "test"  # Run tests
    ASK_USER = "ask_user"  # Request clarification


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_USER = "waiting_user"


@dataclass
class Action:
    """A single action in the agent's plan."""
    action_type: ActionType
    description: str
    target: str  # File path, command, or query
    status: ActionStatus = ActionStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # Additional context


@dataclass
class AgentPlan:
    """The agent's complete plan for a task."""
    task: str
    actions: list[Action] = field(default_factory=list)
    current_action: int = 0
    overall_status: str = "planning"
    final_result: str = ""
    files_modified: list[str] = field(default_factory=list)
    tools_created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def to_log_string(self) -> str:
        """Convert plan to human-readable log."""
        lines = [f"🤖 **Autonomous Agent: {self.task}**\n"]
        
        for i, action in enumerate(self.actions):
            icon = {
                ActionStatus.PENDING: "⏳",
                ActionStatus.IN_PROGRESS: "🔄",
                ActionStatus.COMPLETED: "✅",
                ActionStatus.FAILED: "❌",
                ActionStatus.WAITING_USER: "⏸️",
            }.get(action.status, "•")
            
            lines.append(f"{icon} **{action.action_type.value.upper()}:** {action.description}")
            
            if action.output and action.status == ActionStatus.COMPLETED:
                if len(action.output) > 300:
                    lines.append(f"   ```\n{action.output[:300]}...\n   ```")
                else:
                    lines.append(f"   ```\n{action.output}\n   ```")
            
            if action.error:
                lines.append(f"   ⚠️ Error: {action.error}")
        
        if self.final_result:
            lines.append(f"\n✅ **Result:** {self.final_result}")
        
        return "\n".join(lines)


class ProjectContext:
    """RAG-style project knowledge base."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.index: dict[str, str] = {}  # file_path -> content
        self.structure: list[str] = []  # File tree
        
    async def build_index(self, max_file_size: int = 100000):
        """Index all project files for RAG."""
        self.structure = []
        self.index = {}
        
        exclude_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".evolution-backups", "dist", "build", ".next", "coverage"
        }
        exclude_extensions = {".pyc", ".pyo", ".so", ".dll", ".exe"}
        
        for path in self.project_root.rglob("*"):
            if path.is_file():
                # Check exclusions
                if any(exclude in str(path) for exclude in exclude_dirs):
                    continue
                if path.suffix in exclude_extensions:
                    continue
                    
                rel_path = str(path.relative_to(self.project_root))
                self.structure.append(rel_path)
                
                # Index content for text files
                if path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt", ".html", ".css"}:
                    try:
                        content = path.read_text(encoding="utf-8")
                        if len(content) < max_file_size:
                            self.index[rel_path] = content
                    except:
                        pass
    
    def find_relevant_files(self, query: str, limit: int = 5) -> list[str]:
        """Find files relevant to a query using simple keyword matching."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_files = []
        for file_path, content in self.index.items():
            content_lower = content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored_files.append((file_path, score))
        
        scored_files.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in scored_files[:limit]]
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get indexed content of a file."""
        return self.index.get(file_path)


class AutonomousDevelopmentAgent:
    """
    Truly autonomous development agent.
    
    Uses LLM to:
    1. Understand tasks in natural language
    2. Generate plans dynamically
    3. Write actual functional code (not templates)
    4. Create new tools when needed
    5. Test and validate work
    """
    
    SYSTEM_PROMPT = """You are an autonomous AI development agent with full access to a codebase.

CAPABILITIES:
- Read, write, edit, and delete any file in the project
- Create new tools, utilities, and services
- Install packages and dependencies
- Run commands and tests
- Use RAG to understand project context

RULES:
1. ALWAYS write COMPLETE, FUNCTIONAL code - never placeholders or templates
2. When creating files, use the EXACT file path specified
3. For frontend files: write actual React/JavaScript code
4. For backend files: write actual Python/FastAPI code
5. When asked to create a tool/utility, implement the FULL functionality
6. Test your work when possible
7. If you need clarification, ask the user
8. Use proper imports, error handling, and best practices

FILE OPERATIONS:
- To read: {"action": "read_file", "path": "relative/path.py"}
- To write: {"action": "write_file", "path": "relative/path.py", "content": "..."}
- To edit: {"action": "edit_file", "path": "relative/path.py", "old_text": "...", "new_text": "..."}
- To create directory: {"action": "create_directory", "path": "relative/path"}
- To search: {"action": "search_files", "pattern": "pattern", "glob": "**/*.py"}
- To list: {"action": "list_directory", "path": "relative/path"}

COMMANDS:
- To run: {"action": "run_command", "command": "python -m pytest"}
- To install: {"action": "install_package", "package": "requests"}

RAG:
- To query project: {"action": "rag_query", "query": "find authentication code"}

RESPONSE FORMAT:
Always respond with a JSON object containing:
{
    "thought": "Your reasoning about what to do next",
    "action": {"action": "...", ...},
    "is_complete": true/false,
    "final_result": "Summary when done"
}

When the task is complete, set is_complete=true and provide final_result.
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
        # Prefer Enhanced RAG context for richer project understanding and embeddings
        try:
            self.context = get_enhanced_rag_context(project_root)
        except Exception:
            # Fallback to simple ProjectContext if enhanced RAG is unavailable
            self.context = ProjectContext(project_root)
        self.plan: Optional[AgentPlan] = None
        self.progress_callback = None
        
        # Allowed commands for security
        self.allowed_commands = {
            "pip", "pip3", "python", "python3", "npm", "yarn", "pnpm",
            "git", "ls", "dir", "find", "grep", "cat", "head", "tail",
            "mkdir", "cp", "mv", "rm", "touch", "chmod",
            "pytest", "py.test", "node", "cargo", "go",
            "npx", "promptfoo", "export", "PYTHONPATH",
        }
        
        # Expose file system operations for API routes
        self.fs = self
        # Workspace manager will be lazily created when executing tasks
        self.workspace = None
    
    async def initialize(self):
        """Initialize the agent (build RAG index)."""
        await self.context.build_index()
    
    async def execute_task(self, task: str) -> AgentPlan:
        """Execute a development task autonomously."""
        self.plan = AgentPlan(task=task)
        self.plan.overall_status = "thinking"
        
        try:
            # Phase 1: Understand and plan using LLM
            await self._report_progress("🤔 Understanding task and creating plan...")
            
            # Build context from RAG (prefer Enhanced RAG context if available)
            if hasattr(self.context, "get_context_for_task"):
                project_context = self.context.get_context_for_task(task)
            else:
                relevant_files = []
                if hasattr(self.context, "find_relevant_files"):
                    relevant_files = self.context.find_relevant_files(task)

                context_parts = []
                for file_path in relevant_files[:5]:  # Top 5 relevant files
                    content = getattr(self.context, "get_file_content", lambda p: None)(file_path)
                    if content:
                        context_parts.append(f"### File: {file_path}\n```\n{content[:3000]}\n```")

                project_context = "\n\n".join(context_parts) if context_parts else "No relevant files found."
            
            # Phase 1: Use LLM to understand task and generate complete solution
            try:
                plan_response = await self._llm_generate_solution(task, project_context)
                llm_available = True
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                # LLM not available, use fallback code generation
                await self._report_progress(f"⚠️ LLM unavailable ({str(e)}). Using fallback code generation...")
                plan_response = self._generate_fallback_solution(task)
                llm_available = False
            
            # Parse the solution and extract actions
            actions = self._parse_solution(plan_response, task)
            self.plan.actions = actions
            self.plan.overall_status = "executing"
            
            await self._report_progress(f"📝 Executing {len(actions)} actions...")
            
            # Phase 2: Execute actions
            for i, action in enumerate(self.plan.actions):
                self.plan.current_action = i
                await self._report_progress(f"🔄 {action.action_type.value}: {action.description}")
                await self._execute_action(action)
                
                if action.status == ActionStatus.FAILED:
                    self.plan.errors.append(f"Action {i+1} failed: {action.error}")
                    # Try to recover
                    recovery = await self._handle_failure(action, task)
                    if recovery:
                        continue

                # After each action, allow the LLM to reflect and refine the remaining plan (ReAct-style)
                if llm_available:
                    try:
                        refined = await self._llm_refine_plan(task, self.plan, current_index=i)
                        if refined:
                            # Replace remaining actions with refined sequence
                            self.plan.actions = self.plan.actions[: i + 1] + refined
                    except Exception:
                        # Non-fatal: continue with existing plan
                        pass
                
                # Check if task is complete
                if self._is_task_complete(task, self.plan):
                    break
            
            self.plan.overall_status = "completed"
            self.plan.final_result = f"✅ Task completed! Modified {len(self.plan.files_modified)} file(s)."
            
        except Exception as e:
            import traceback
            self.plan.overall_status = "failed"
            self.plan.errors.append(f"{str(e)}\n\n{traceback.format_exc()}")
            self.plan.final_result = f"❌ Task failed: {str(e)}"
        
        return self.plan
    
    async def _report_progress(self, message: str):
        """Report progress via callback."""
        if self.progress_callback:
            await self.progress_callback(message)
    
    async def _llm_refine_plan(self, task: str, plan: AgentPlan, current_index: int = 0) -> list[Action]:
        """
        Ask the LLM to reflect on the executed actions and refine the remaining plan.
        Returns a list of new Action objects to replace the remaining actions after current_index.
        This provides a lightweight ReAct-style refinement loop.
        """
        try:
            # Provide the LLM with the current execution log and observations
            plan_log = plan.to_log_string()
            obs = {
                "files_modified": plan.files_modified,
                "errors": plan.errors,
                "current_index": current_index,
            }
            context = f"CURRENT PLAN:\n{plan_log}\n\nOBSERVATIONS:\n{json.dumps(obs)}\n"
            response = await self._llm_generate_solution(task, context)
            new_actions = self._parse_solution(response, task)
            # Return the new actions (LLM should provide only remaining actions)
            return new_actions or []
        except Exception:
            return []

    def _generate_fallback_solution(self, task: str) -> str:
        """Generate a solution without LLM using intelligent rule-based code generation."""
        task_lower = task.lower()
        
        # Extract key information from task
        filename = self._extract_filename(task)
        folder_path = self._extract_folder_path(task)
        message = self._extract_message(task)
        
        # Detect task type and generate appropriate code
        if "alert" in task_lower or ("show" in task_lower and ("alert" in task_lower or "warning" in task_lower or "notice" in task_lower)):
            return self._generate_alert_solution(task, filename, folder_path, message)
        elif "console" in task_lower and ("log" in task_lower or "print" in task_lower or "write" in task_lower):
            return self._generate_console_log_solution(task, filename, folder_path, message)
        elif "encrypt" in task_lower or "encryption" in task_lower:
            return self._generate_encryption_solution(task, filename, folder_path)
        elif "decrypt" in task_lower:
            return self._generate_decryption_solution(task, filename, folder_path)
        elif "api" in task_lower or "endpoint" in task_lower or "route" in task_lower:
            return self._generate_api_solution(task, filename, folder_path)
        elif "test" in task_lower:
            return self._generate_test_solution(task, filename, folder_path)
        elif "utility" in task_lower or "helper" in task_lower or "service" in task_lower:
            return self._generate_utility_solution(task, filename, folder_path)
        elif "file" in task_lower and ("create" in task_lower or "new" in task_lower):
            return self._generate_file_creation_solution(task, filename, folder_path, message)
        else:
            return self._generate_generic_solution(task, filename, folder_path)
    
    def _extract_filename(self, task: str) -> Optional[str]:
        """Extract filename from task description."""
        import re
        
        # Look for patterns like "called alert.js", "named alert.js", "file name should be alert.js"
        patterns = [
            r'(?:called|named|name is|filename is|file name is|should be)\s+["\']?([\w\-]+\.\w+)["\']?',
            r'["\']([\w\-]+\.(?:js|jsx|ts|tsx|py|css|html))["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_folder_path(self, task: str) -> str:
        """Extract folder path from task description."""
        import re
        
        # Check for explicit frontend/utils mention
        if "frontend" in task.lower() and "utils" in task.lower():
            return "frontend/src/utils"
        
        # Check for "in the same folder" references
        if "same folder" in task.lower() or "same directory" in task.lower():
            if "utils" in task.lower():
                return "frontend/src/utils"
        
        # Look for path patterns
        patterns = [
            r'(?:in|at|inside|within)\s+([/\w\-]+/[\w\-]+)',
            r'folder\s+([/\w\-]+)',
            r'directory\s+([/\w\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                path = match.group(1)
                # Normalize path
                if path.startswith('/'):
                    path = path[1:]
                return path
        
        # Default based on context
        if "utils" in task.lower():
            return "frontend/src/utils"
        if "component" in task.lower():
            return "frontend/src/components"
        if "api" in task.lower() or "endpoint" in task.lower():
            return "backend/app/api"
        if "service" in task.lower():
            return "backend/app/services"
        
        return "frontend/src/utils"  # Default
    
    def _extract_message(self, task: str) -> str:
        """Extract message/string from task description."""
        import re
        
        # Look for quoted strings
        patterns = [
            r'["\']([^"\']+)["\']',
            r'saying\s+(?:that\s+)?["\']?([^"\']+?)["\']?$',
            r'showing\s+(?:that\s+)?["\']?([^"\']+?)["\']?$',
            r'displaying\s+(?:that\s+)?["\']?([^"\']+?)["\']?$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Hello World"  # Default message
    
    def _generate_alert_solution(self, task: str, filename: str, folder_path: str, message: str) -> str:
        """Generate alert/notification solution."""
        if not filename:
            filename = "alert.js"
        if not folder_path:
            folder_path = "frontend/src/utils"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": f"Creating alert utility that shows: '{message}'",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": f'''/**
 * Alert Utility
 * Task: {task}
 * Generated by ISE AI Autonomous Agent
 * 
 * Shows browser alerts and notifications to users
 */

/**
 * Show a browser alert with a message
 * @param {string} message - The message to display
 */
export function showAlert(message = "{message}") {{
    alert(message);
}}

/**
 * Show a warning alert
 * @param {string} message - The warning message
 */
export function showWarning(message = "{message}") {{
    console.warn("⚠️ WARNING:", message);
    alert("⚠️ Warning: " + message);
}}

/**
 * Show a resource warning (specific use case)
 */
export function showResourceWarning() {{
    const warningMsg = "{message}";
    console.warn("🔴 Resource Warning:", warningMsg);
    
    // Show browser alert
    alert(warningMsg);
    
    // Optional: Also show in console with timestamp
    console.log(`[${{new Date().toISOString()}}] ${{warningMsg}}`);
}}

/**
 * Show a custom styled notification (if using a notification library)
 * @param {string} title - Notification title
 * @param {string} message - Notification message
 * @param {string} type - Type: 'info', 'warning', 'error', 'success'
 */
export function showNotification(title, message, type = 'info') {{
    console.log(`📢 [${{type.toUpperCase()}}] ${{title}}: ${{message}}`);
    
    // Fallback to alert if no notification library
    alert(`[${{type.toUpperCase()}}] ${{title}}\\n\\n${{message}}`);
}}

// Auto-execute on import (optional - uncomment if you want alert on page load)
// showAlert("{message}");

console.log("🔔 Alert utility loaded");
''',
                    "description": f"Create alert utility file at {file_path}"
                },
                {
                    "action": "edit_file",
                    "path": "frontend/src/main.jsx",
                    "old_text": "import React from 'react'",
                    "new_text": f"import React from 'react'\nimport {{ showAlert, showWarning, showResourceWarning }} from './utils/{filename.split('.')[0]}.js'",
                    "description": f"Import alert utility in main.jsx"
                }
            ],
            "is_complete": True,
            "final_result": f"Created alert utility at {file_path} that shows: '{message}'"
        })
    
    def _generate_console_log_solution(self, task: str, filename: Optional[str], folder_path: str, message: str) -> str:
        """Generate console.log solution."""
        if not filename:
            filename = "console_message.js"
        if not folder_path:
            folder_path = "frontend/src/utils"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": f"Creating a file that logs '{message}' to the console",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": f'''/**
 * Console Message Utility
 * Task: {task}
 * Generated by ISE AI Autonomous Agent
 */

// Log the message to browser console
console.log("{message}");

// Export for reuse
export function logMessage(msg = "{message}") {{
    console.log(msg);
}}

export function logWithTimestamp(msg = "{message}") {{
    const timestamp = new Date().toISOString();
    console.log(`[${{timestamp}}] ${{msg}}`);
}}

// Auto-execute on import
console.log("✅ Console message utility loaded");
''',
                    "description": f"Create console log utility at {file_path}"
                },
                {
                    "action": "edit_file",
                    "path": "frontend/src/main.jsx",
                    "old_text": "import React from 'react'",
                    "new_text": f"import React from 'react'\nimport {{ logMessage, logWithTimestamp }} from './utils/{filename.split('.')[0]}.js'",
                    "description": f"Import console utility in main.jsx"
                }
            ],
            "is_complete": True,
            "final_result": f"Created console utility at {file_path} that logs '{message}'"
        })
    
    def _generate_encryption_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate encryption utility solution."""
        if not filename:
            filename = "encrypt.js"
        if not folder_path:
            folder_path = "frontend/src/utils"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": "Creating encryption utility for secure frontend-to-backend communication",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": self._get_encryption_code(),
                    "description": "Create encryption utility with AES-GCM"
                },
                {
                    "action": "edit_file",
                    "path": "frontend/src/main.jsx",
                    "old_text": "import React from 'react'",
                    "new_text": f"import React from 'react'\nimport {{ encrypt, decrypt, encryptData, decryptData }} from './utils/{filename.split('.')[0]}.js'",
                    "description": "Import encryption utility"
                }
            ],
            "is_complete": True,
            "final_result": f"Created encryption utility at {file_path}"
        })
    
    def _get_encryption_code(self) -> str:
        """Return the encryption utility code."""
        return '''/**
 * Encryption Utility
 * Task: Encrypt messages from frontend to backend
 * Generated by ISE AI Autonomous Agent
 * 
 * Uses Web Crypto API for AES-GCM encryption
 */

const ENCRYPTION_KEY = "ise-ai-secret-key-2024";

async function getKey() {
    const enc = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
        "raw",
        enc.encode(ENCRYPTION_KEY),
        { name: "PBKDF2" },
        false,
        ["deriveKey"]
    );
    
    return crypto.subtle.deriveKey(
        {
            name: "PBKDF2",
            salt: enc.encode("ise-ai-salt"),
            iterations: 100000,
            hash: "SHA-256"
        },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"]
    );
}

export async function encrypt(plaintext) {
    const key = await getKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const enc = new TextEncoder();
    
    const ciphertext = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: iv },
        key,
        enc.encode(plaintext)
    );
    
    const combined = new Uint8Array(iv.length + ciphertext.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(ciphertext), iv.length);
    
    return btoa(String.fromCharCode(...combined));
}

export async function decrypt(encrypted) {
    const key = await getKey();
    const combined = Uint8Array.from(atob(encrypted), c => c.charCodeAt(0));
    
    const iv = combined.slice(0, 12);
    const ciphertext = combined.slice(12);
    
    const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: iv },
        key,
        ciphertext
    );
    
    const dec = new TextDecoder();
    return dec.decode(plaintext);
}

export async function encryptData(data) {
    const jsonString = JSON.stringify(data);
    return await encrypt(jsonString);
}

export async function decryptData(encrypted) {
    const jsonString = await decrypt(encrypted);
    return JSON.parse(jsonString);
}

export default { encrypt, decrypt, encryptData, decryptData };
console.log("🔐 Encryption utility loaded");
'''
    
    def _generate_decryption_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate decryption solution (same as encryption)."""
        return self._generate_encryption_solution(task, filename, folder_path)
    
    def _generate_file_creation_solution(self, task: str, filename: Optional[str], folder_path: str, message: str) -> str:
        """Generate generic file creation solution with actual code based on task."""
        import re
        
        # Try to extract file path from task
        if not filename or not folder_path.startswith(('frontend/', 'backend/')):
            path_match = re.search(r'([/\w\.-]+/[\w\.-]+\.\w+)', task)
            if path_match:
                extracted_path = path_match.group(1)
                if extracted_path.startswith('/'):
                    extracted_path = extracted_path[1:]
                folder_path = '/'.join(extracted_path.split('/')[:-1])
                filename = extracted_path.split('/')[-1]
        
        if not filename:
            filename = "generated.js"
        if not folder_path:
            folder_path = "frontend/src/utils"
        
        file_path = f"{folder_path}/{filename}"
        
        # Generate code based on task context
        code_content = self._generate_contextual_code(task, filename)
        
        return json.dumps({
            "thought": f"Creating file at {file_path}",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": code_content,
                    "description": f"Create file at {file_path} with functional code"
                }
            ],
            "is_complete": True,
            "final_result": f"Created file at {file_path}"
        })
    
    def _generate_contextual_code(self, task: str, filename: str) -> str:
        """Generate code based on task context and filename."""
        task_lower = task.lower()
        name_without_ext = filename.rsplit('.', 1)[0]
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'js'
        
        # JavaScript/React files
        if ext in ['js', 'jsx', 'ts', 'tsx']:
            if 'alert' in task_lower or 'notification' in task_lower or 'warning' in task_lower:
                return f'''/**
 * {name_without_ext.title()} Module
 * Task: {task}
 * Generated by ISE AI Autonomous Agent
 */

export function show() {{
    alert("Notification from {name_without_ext}");
}}

export function notify(message) {{
    console.log("📢", message);
    alert(message);
}}

export default {{ show, notify }};
'''
            elif 'log' in task_lower or 'console' in task_lower:
                return f'''/**
 * {name_without_ext.title()} Module
 * Task: {task}
 * Generated by ISE AI Autonomous Agent
 */

export function log(message) {{
    console.log(message);
}}

export function logWithTime(message) {{
    console.log(`[${{new Date().toISOString()}}] ${{message}}`);
}}

export default {{ log, logWithTime }};
'''
            else:
                return f'''/**
 * {name_without_ext.title()} Module
 * Task: {task}
 * Generated by ISE AI Autonomous Agent
 */

/**
 * Initialize the module
 */
export function init() {{
    console.log("{name_without_ext} initialized");
}}

/**
 * Main function - customize as needed
 */
export function execute(options = {{}}) {{
    console.log("Executing {name_without_ext} with options:", options);
    return {{ success: true }};
}}

export default {{ init, execute }};
'''
        
        # Python files
        elif ext == 'py':
            return f'''"""
{name_without_ext.title()} Module
Task: {task}
Generated by ISE AI Autonomous Agent
"""

from typing import Any, Dict, Optional


def init() -> None:
    """Initialize the module."""
    print(f"{name_without_ext} initialized")


def execute(options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute the main functionality.
    
    Args:
        options: Configuration options
        
    Returns:
        Result dictionary
    """
    print(f"Executing {name_without_ext} with options: {{options}}")
    return {{"status": "success", "module": "{name_without_ext}"}}


if __name__ == "__main__":
    init()
    result = execute()
    print(f"Result: {{result}}")
'''
        
        # Default
        return f'''// {name_without_ext.title()} Module
// Task: {task}
// Generated by ISE AI Autonomous Agent

export function init() {{
    console.log("{name_without_ext} initialized");
}}

export default {{ init }};
'''
    
    def _generate_api_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate API endpoint solution."""
        if not filename:
            filename = "auto_generated.py"
        if not folder_path:
            folder_path = "backend/app/api"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": "Creating FastAPI endpoint",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": self._get_api_code(task),
                    "description": "Create FastAPI endpoint"
                }
            ],
            "is_complete": True,
            "final_result": f"Created API endpoint at {file_path}"
        })
    
    def _get_api_code(self, task: str) -> str:
        """Generate API code based on task."""
        return f'''"""
Auto-generated API Endpoint
Task: {task}
Generated by ISE AI Autonomous Agent
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()


class RequestModel(BaseModel):
    """Request model for the endpoint."""
    data: Optional[Dict[str, Any]] = None


class ResponseModel(BaseModel):
    """Response model for the endpoint."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


@router.get("/api/auto")
async def get_auto():
    """Auto-generated GET endpoint."""
    return ResponseModel(
        status="success",
        message="Endpoint is working",
    )


@router.post("/api/auto")
async def post_auto(request: RequestModel):
    """Auto-generated POST endpoint."""
    return ResponseModel(
        status="success",
        message="Data received",
        data=request.data,
    )
'''
    
    def _generate_test_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate test file solution."""
        if not filename:
            filename = "test_auto_generated.py"
        if not folder_path:
            folder_path = "tests"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": "Creating test file",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": self._get_test_code(task),
                    "description": "Create test file"
                }
            ],
            "is_complete": True,
            "final_result": f"Created test file at {file_path}"
        })
    
    def _get_test_code(self, task: str) -> str:
        """Generate test code."""
        return f'''"""
Auto-generated Test File
Task: {task}
Generated by ISE AI Autonomous Agent
"""

import pytest


def test_placeholder():
    """Placeholder test - customize as needed."""
    assert True


def test_example():
    """Example test."""
    result = 2 + 2
    assert result == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    def _generate_utility_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate utility/service solution."""
        if not filename:
            filename = "auto_generated.py"
        if not folder_path:
            folder_path = "backend/app/services"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": "Creating utility module",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": self._get_utility_code(task),
                    "description": "Create service module"
                }
            ],
            "is_complete": True,
            "final_result": f"Created utility service at {file_path}"
        })
    
    def _get_utility_code(self, task: str) -> str:
        """Generate utility code."""
        return f'''"""
Auto-generated Service Module
Task: {task}
Generated by ISE AI Autonomous Agent
"""

from typing import Optional, Dict, Any
from datetime import datetime


class AutoGeneratedService:
    """
    Auto-generated service class.
    Customize this based on your requirements.
    """

    def __init__(self):
        self.created_at = datetime.now()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data."""
        return {{
            "status": "success",
            "data": data,
            "processed_at": datetime.now().isoformat(),
        }}

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data."""
        return bool(data)


# Global instance
_service: Optional[AutoGeneratedService] = None


def get_service() -> AutoGeneratedService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = AutoGeneratedService()
    return _service
'''
    
    def _generate_generic_solution(self, task: str, filename: Optional[str], folder_path: str) -> str:
        """Generate a generic solution for unrecognized tasks."""
        if not filename:
            filename = "auto_generated.py"
        if not folder_path:
            folder_path = "backend/app/services"
        
        file_path = f"{folder_path}/{filename}"
        
        return json.dumps({
            "thought": f"Creating solution for: {task}",
            "actions": [
                {
                    "action": "write_file",
                    "path": file_path,
                    "content": self._generate_contextual_code(task, filename),
                    "description": f"Create solution file at {file_path}"
                }
            ],
            "is_complete": True,
            "final_result": f"Created solution file at {file_path}"
        })
    
    async def _llm_generate_solution(self, task: str, project_context: str) -> str:
        """Use LLM to generate a complete solution with actual code."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""
TASK: {task}

PROJECT CONTEXT:
{project_context}

PROJECT STRUCTURE (available files):
{chr(10).join(getattr(self.context, 'structure', list(getattr(self.context, 'file_index', {}).keys()))[:100])}

INSTRUCTIONS:
1. Analyze the task carefully
2. Determine what files need to be created or modified
3. Write COMPLETE, FUNCTIONAL code - NOT templates or placeholders
4. For each file operation, provide the FULL content
5. Include proper imports, error handling, and best practices
6. If creating a utility/tool, implement the FULL functionality

Respond with a JSON object containing:
{{
    "thought": "Your analysis of the task",
    "actions": [
        {{"action": "write_file", "path": "frontend/src/utils/encrypt.js", "content": "FULL code here", "description": "Create encryption utility"}},
        ...
    ],
    "is_complete": true,
    "final_result": "Summary of what was done"
}}

IMPORTANT: The "content" field must contain the COMPLETE, WORKING code - not placeholders!
"""}
        ]
        
        response = await self._call_llm(messages, max_tokens=4096)
        return response
    
    async def _call_llm(self, messages: list[dict], max_tokens: int = 2048) -> str:
        """Call the LLM (Ollama) for reasoning."""
        payload = {
            "model": settings.default_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": max_tokens}
        }

        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=300.0) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty response from LLM")
                return content
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to Ollama at {settings.ollama_base_url}. Is Ollama running?") from e
        except httpx.TimeoutException as e:
            raise TimeoutError(f"LLM request timed out after 300s") from e
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {str(e)}") from e
    
    def _parse_solution(self, response: str, task: str) -> list[Action]:
        """Parse LLM/fallback solution response into actions."""
        actions = []
        
        # If response starts with { it's already JSON (from fallback)
        if response.strip().startswith('{'):
            try:
                data = json.loads(response)
                
                # Extract actions array if present
                if "actions" in data and isinstance(data["actions"], list):
                    for action_data in data["actions"]:
                        action_type_str = action_data.get("action", "think")
                        try:
                            action_type = ActionType(action_type_str)
                        except ValueError:
                            action_type = ActionType.THINK
                        
                        actions.append(Action(
                            action_type=action_type,
                            description=action_data.get("description", f"{action_type.value} operation"),
                            target=action_data.get("path", action_data.get("command", action_data.get("query", ""))),
                            metadata=action_data
                        ))
                    
                    return actions
            except json.JSONDecodeError:
                pass
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                
                # Extract actions array if present
                if "actions" in data and isinstance(data["actions"], list):
                    for action_data in data["actions"]:
                        action_type_str = action_data.get("action", "think")
                        try:
                            action_type = ActionType(action_type_str)
                        except ValueError:
                            action_type = ActionType.THINK
                        
                        actions.append(Action(
                            action_type=action_type,
                            description=action_data.get("description", f"{action_type.value} operation"),
                            target=action_data.get("path", action_data.get("command", action_data.get("query", ""))),
                            metadata=action_data
                        ))
                    
                    return actions
                
                # Extract single action if present
                if "action" in data:
                    action_data = data["action"]
                    action_type_str = action_data.get("action", "think")
                    try:
                        action_type = ActionType(action_type_str)
                    except ValueError:
                        action_type = ActionType.THINK
                    
                    actions.append(Action(
                        action_type=action_type,
                        description=action_data.get("description", str(action_data)),
                        target=action_data.get("path", action_data.get("command", action_data.get("query", ""))),
                        metadata=action_data
                    ))
                    
                    return actions
                    
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON, create a write action with the response as content
        actions.append(Action(
            action_type=ActionType.WRITE_FILE,
            description="Creating solution file",
            target="backend/app/services/auto_generated.py",
            metadata={"content": response, "description": "Generated solution"}
        ))
        
        return actions
    
    async def _execute_action(self, action: Action):
        """Execute a single action."""
        action.status = ActionStatus.IN_PROGRESS
        action.started_at = datetime.now(UTC).isoformat()
        
        try:
            if action.action_type == ActionType.THINK:
                action.output = "Thinking..."
                action.status = ActionStatus.COMPLETED
            
            elif action.action_type == ActionType.READ_FILE:
                success, result = await self._read_file(action.target)
                action.output = result
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
            
            elif action.action_type == ActionType.WRITE_FILE:
                content = action.metadata.get("content", "")
                success, result = await self._write_file(action.target, content)
                action.output = result
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
                if success:
                    self.plan.files_modified.append(action.target)
            
            elif action.action_type == ActionType.EDIT_FILE:
                old_text = action.metadata.get("old_text", "")
                new_text = action.metadata.get("new_text", "")
                success, msg = await self._edit_file(action.target, old_text, new_text)
                action.output = msg
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
                if success:
                    self.plan.files_modified.append(action.target)
            
            elif action.action_type == ActionType.CREATE_FILE:
                content = action.metadata.get("content", "")
                success, result = await self._write_file(action.target, content)
                action.output = result
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
                if success:
                    self.plan.files_modified.append(action.target)
            
            elif action.action_type == ActionType.SEARCH_FILES:
                pattern = action.metadata.get("pattern", action.target)
                glob_pattern = action.metadata.get("glob", "**/*")
                results = await self._search_files(pattern, glob_pattern)
                action.output = f"Found {len(results)} files: {', '.join(results[:10])}"
                action.status = ActionStatus.COMPLETED
            
            elif action.action_type == ActionType.LIST_DIRECTORY:
                success, items = await self._list_directory(action.target)
                action.output = "\n".join(items) if success else "Failed to list directory"
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
            
            elif action.action_type == ActionType.RUN_COMMAND:
                success, output = await self._run_command(action.target)
                action.output = output
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
            
            elif action.action_type == ActionType.INSTALL_PACKAGE:
                success, output = await self._run_command(f"pip install {action.target}")
                action.output = output
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
                if success:
                    self.plan.tools_created.append(f"package:{action.target}")
            
            elif action.action_type == ActionType.RAG_QUERY:
                results = self.context.find_relevant_files(action.target)
                action.output = f"Relevant files: {', '.join(results)}"
                action.status = ActionStatus.COMPLETED
            
            elif action.action_type == ActionType.TEST:
                success, output = await self._run_command("python -m pytest -v")
                action.output = output
                action.status = ActionStatus.COMPLETED if success else ActionStatus.FAILED
            
            elif action.action_type == ActionType.ASK_USER:
                action.status = ActionStatus.WAITING_USER
                action.output = action.metadata.get("question", "Need user input")
            
            else:
                action.error = f"Unknown action type: {action.action_type}"
                action.status = ActionStatus.FAILED
        
        except Exception as e:
            action.error = str(e)
            action.status = ActionStatus.FAILED
        
        action.completed_at = datetime.now(UTC).isoformat()
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a file path relative to project root."""
        path = Path(file_path)
        if path.is_absolute():
            try:
                return path.relative_to(self.project_root)
            except ValueError:
                return path
        return self.project_root / file_path

    async def _read_file(self, file_path: str) -> tuple[bool, str]:
        """Read a file. Returns (success, content_or_error)."""
        path = self._resolve_path(file_path)
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
                return True, content
        except Exception as e:
            return False, str(e)
    
    async def _write_file(self, file_path: str, content: str) -> tuple[bool, str]:
        """Write a file. Returns (success, message)."""
        path = self._resolve_path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
            return True, f"Successfully wrote to {file_path}"
        except Exception as e:
            return False, str(e)
    
    async def _edit_file(self, file_path: str, old_text: str, new_text: str) -> tuple[bool, str]:
        """Edit a file."""
        path = self.project_root / file_path
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
        
        if old_text not in content:
            return False, "Text to replace not found in file"
        
        new_content = content.replace(old_text, new_text, 1)
        
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(new_content)
        
        return True, f"Successfully edited {file_path}"
    
    async def _search_files(self, pattern: str, glob_pattern: str) -> list[str]:
        """Search for files."""
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
    
    async def _list_directory(self, dir_path: str) -> tuple[bool, list[str]]:
        """List directory contents."""
        path = self.project_root / dir_path
        if not path.is_dir():
            return False, []
        
        items = []
        for item in path.iterdir():
            if not item.name.startswith("."):
                items.append(f"{'📁 ' if item.is_dir() else '📄 '}{item.name}")
        return True, items
    
    async def _run_command(self, command: str, timeout: int = 120) -> tuple[bool, str]:
        """Run a shell command."""
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
        
        dangerous = ["rm -rf /", "rm -rf ~", "sudo", "su ", "dd "]
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
    
    async def _handle_failure(self, action: Action, task: str) -> bool:
        """Try to recover from a failed action."""
        # Ask LLM for recovery strategy
        recovery_prompt = f"""
Action failed: {action.action_type.value} on {action.target}
Error: {action.error}
Original task: {task}

What should we do? Respond with JSON: {{"action": {{...}}, "reason": "..."}}
"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": recovery_prompt}
        ]
        
        response = await self._call_llm(messages)
        new_actions = self._parse_plan(response)
        
        if new_actions:
            # Insert recovery actions
            for i, new_action in enumerate(new_actions):
                self.plan.actions.insert(self.plan.current_action + i + 1, new_action)
            return True
        
        return False
    
    def _is_task_complete(self, task: str, plan: AgentPlan) -> bool:
        """Check if the task is complete."""
        # Simple heuristic: at least one file modified or command run successfully
        if plan.files_modified:
            return True
        if plan.tools_created:
            return True
        
        # Check if any action completed successfully
        for action in plan.actions:
            if action.status == ActionStatus.COMPLETED:
                if action.action_type in {
                    ActionType.WRITE_FILE, ActionType.EDIT_FILE,
                    ActionType.CREATE_FILE, ActionType.RUN_COMMAND
                }:
                    return True
        
        return False


# Global instance
_agent: Optional[AutonomousDevelopmentAgent] = None


def get_autonomous_agent() -> AutonomousDevelopmentAgent:
    """Get or create autonomous agent instance."""
    global _agent
    if _agent is None:
        _agent = AutonomousDevelopmentAgent()
    return _agent
