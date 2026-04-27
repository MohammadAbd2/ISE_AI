"""
Dynamic tool registry for extensible AI capabilities.
Allows the AI to register new tools and capabilities at runtime.
"""

import json
import inspect
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional

from app.core.config import settings
from app.services.artifacts import get_artifact_service
from app.services.history import get_history_service
from app.services.search import get_search_service
from app.services.session_analytics import build_session_analytics_payload
from app.services.tool_executor import get_tool_executor
from app.services.git_integration import get_git_integration
from app.services.visualization_runtime import build_visualization_response
from app.services.sandbox_runner import execute_module_in_sandbox


@dataclass
class Tool:
    """Represents a callable tool the AI can use."""

    name: str
    description: str
    function_ref: str  # e.g., "module.function_name"
    parameters: dict  # JSON schema for parameters
    return_type: str  # Expected return type
    category: str  # e.g., "file_io", "execution", "search"
    version: str = "1.0.0"
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "function_ref": self.function_ref,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "category": self.category,
            "version": self.version,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(data: dict) -> "Tool":
        """Create from dictionary."""
        return Tool(
            name=data["name"],
            description=data["description"],
            function_ref=data["function_ref"],
            parameters=data.get("parameters", {}),
            return_type=data.get("return_type", "Any"),
            category=data.get("category", "custom"),
            version=data.get("version", "1.0.0"),
            enabled=data.get("enabled", True),
        )


class DynamicToolRegistry:
    """
    Registry for AI tools that can be extended at runtime.
    Persisted as JSON for easy inspection and modification.
    """

    def __init__(self):
        self.registry_file = (
            Path(settings.backend_root).parent / ".evolution-tools.json"
        )
        self.tools: dict[str, Tool] = {}
        self.tool_functions: dict[str, Callable] = {}
        self._load_registry()
        self._initialize_defaults()

    def _load_registry(self) -> None:
        """Load tool registry from file."""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text())
                for name, tool_data in data.items():
                    self.tools[name] = Tool.from_dict(tool_data)
            except Exception:
                self.tools = {}
        else:
            self.tools = {}

    def _save_registry(self) -> None:
        """Save tool registry to file."""
        data = {name: tool.to_dict() for name, tool in self.tools.items()}
        self.registry_file.write_text(json.dumps(data, indent=2))

    def _initialize_defaults(self) -> None:
        """Ensure built-in tools are always present."""
        changed = False
        for tool in self._default_tools():
            if tool.name in self.tools:
                continue
            self.tools[tool.name] = tool
            changed = True

        if changed:
            self._save_registry()

    def _default_tools(self) -> list[Tool]:
        """Return built-in tools supported by the current application."""
        return [
            Tool(
                name="read_file",
                description="Read the contents of a file",
                function_ref="tool_executor.read_file",
                parameters={
                    "path": {"type": "string", "description": "File path"}
                },
                return_type="str",
                category="file_io",
            ),
            Tool(
                name="write_file",
                description="Write content to a file",
                function_ref="tool_executor.write_file",
                parameters={
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append if True"},
                },
                return_type="dict",
                category="file_io",
            ),
            Tool(
                name="list_directory",
                description="List files and directories in a safe workspace path",
                function_ref="tool_executor.list_directory",
                parameters={
                    "path": {"type": "string", "description": "Directory path"},
                },
                return_type="array",
                category="file_io",
            ),
            Tool(
                name="execute_command",
                description="Execute a shell command safely",
                function_ref="tool_executor.execute_command",
                parameters={
                    "command": {
                        "type": "string",
                        "description": "Command to execute",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                    },
                },
                return_type="dict",
                category="execution",
            ),
            Tool(
                name="register_capability",
                description="Register a new AI capability",
                function_ref="capability_registry.register",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "Capability name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Capability description",
                    },
                },
                return_type="dict",
                category="capability_management",
            ),
            Tool(
                name="update_capability_status",
                description="Update the status of a capability",
                function_ref="capability_registry.update_status",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "Capability name",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status (available, pending, in_development, failed, deprecated)",
                    },
                },
                return_type="dict",
                category="capability_management",
            ),
            Tool(
                name="analyze_imports",
                description="Extract import dependencies from a Python source file",
                function_ref="tool_executor.analyze_imports",
                parameters={
                    "file_path": {"type": "string", "description": "Python file path"},
                },
                return_type="array",
                category="analysis",
            ),
            Tool(
                name="web_research",
                description="Run a multi-query web research pass and persist the result as research memory",
                function_ref="search_service.web_research",
                parameters={
                    "query": {"type": "string", "description": "Research question"},
                    "session_id": {"type": "string", "description": "Active session id"},
                },
                return_type="dict",
                category="research",
            ),
            Tool(
                name="build_visualization",
                description="Parse user data into a dynamic chart or 3D map specification",
                function_ref="visualization.build_visualization_artifacts",
                parameters={
                    "prompt": {"type": "string", "description": "Visualization request"},
                    "data": {"type": "string", "description": "Optional raw dataset"},
                },
                return_type="dict",
                category="visualization",
            ),
            Tool(
                name="session_analytics",
                description="Resolve the latest session artifacts, render blocks, and visualization context",
                function_ref="session_analytics.build_session_analytics_payload",
                parameters={
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="analytics",
            ),
            Tool(
                name="session_history",
                description="Inspect the current chat session history and summarize recent messages",
                function_ref="history_service.get_session",
                parameters={
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="analytics",
            ),
            Tool(
                name="project_archive_analysis",
                description="Analyze uploaded project archives for frameworks, configs, and prioritized source context",
                function_ref="document_service.extract_archive_context",
                parameters={
                    "artifact_id": {"type": "string", "description": "Archive artifact id"},
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="analysis",
            ),
            Tool(
                name="generate_plan",
                description="Create a project-aware execution plan for a coding or workflow task",
                function_ref="planning_agent.create_plan",
                parameters={
                    "task": {"type": "string", "description": "Task to plan"},
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="planning",
            ),
            Tool(
                name="execute_plan",
                description="Execute a structured plan and return typed plan-result artifacts",
                function_ref="planning_agent.execute_task_with_plan",
                parameters={
                    "task": {"type": "string", "description": "Task to execute"},
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="planning",
            ),
            Tool(
                name="run_verification",
                description="Run project-aware verification commands after coding changes",
                function_ref="intelligent_coding_agent.verify_changes",
                parameters={
                    "paths": {"type": "array", "description": "Touched file paths"},
                },
                return_type="dict",
                category="verification",
            ),
            Tool(
                name="list_artifacts",
                description="List saved artifacts for the active session",
                function_ref="artifact_service.list_artifacts",
                parameters={
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="artifacts",
            ),
            Tool(
                name="reopen_artifact",
                description="Reopen a saved artifact into the chat as a structured result",
                function_ref="artifact_service.reopen_artifact",
                parameters={
                    "artifact_id": {"type": "string", "description": "Artifact id"},
                    "session_id": {"type": "string", "description": "Session id"},
                },
                return_type="dict",
                category="artifacts",
            ),
            # Git Operations
            Tool(
                name="git_status",
                description="Get git repository status (branch, staged/unstaged changes, untracked files)",
                function_ref="git_integration.get_status",
                parameters={},
                return_type="dict",
                category="git",
            ),
            Tool(
                name="git_commit",
                description="Stage files and create a git commit",
                function_ref="git_integration.commit",
                parameters={
                    "message": {"type": "string", "description": "Commit message"},
                    "files": {"type": "array", "description": "Files to stage (optional)"},
                },
                return_type="bool",
                category="git",
            ),
            Tool(
                name="git_branch_create",
                description="Create a new git branch",
                function_ref="git_integration.create_branch",
                parameters={
                    "branch_name": {"type": "string", "description": "New branch name"},
                    "from_branch": {"type": "string", "description": "Branch to create from (optional)"},
                },
                return_type="bool",
                category="git",
            ),
            Tool(
                name="git_branch_checkout",
                description="Switch to a git branch",
                function_ref="git_integration.checkout_branch",
                parameters={
                    "branch_name": {"type": "string", "description": "Branch to checkout"},
                },
                return_type="bool",
                category="git",
            ),
            Tool(
                name="git_branches",
                description="List all git branches",
                function_ref="git_integration.list_branches",
                parameters={},
                return_type="array",
                category="git",
            ),
            Tool(
                name="git_push",
                description="Push to remote git repository",
                function_ref="git_integration.push",
                parameters={
                    "remote": {"type": "string", "description": "Remote name (default: origin)"},
                    "branch": {"type": "string", "description": "Branch name (optional)"},
                },
                return_type="bool",
                category="git",
            ),
            Tool(
                name="git_pull",
                description="Pull from remote git repository",
                function_ref="git_integration.pull",
                parameters={
                    "remote": {"type": "string", "description": "Remote name (default: origin)"},
                    "branch": {"type": "string", "description": "Branch name (optional)"},
                },
                return_type="bool",
                category="git",
            ),
            Tool(
                name="git_log",
                description="Get git commit history",
                function_ref="git_integration.get_log",
                parameters={
                    "count": {"type": "integer", "description": "Number of commits (default: 20)"},
                },
                return_type="array",
                category="git",
            ),
            Tool(
                name="git_diff",
                description="Get git diff of unstaged changes",
                function_ref="git_integration.get_diff",
                parameters={
                    "file_path": {"type": "string", "description": "File path (optional)"},
                },
                return_type="str",
                category="git",
            ),
            Tool(
                name="git_commit_suggestion",
                description="Generate a commit message based on current changes",
                function_ref="git_integration.generate_commit_message",
                parameters={},
                return_type="dict",
                category="git",
            ),
            # Advanced File Operations
            Tool(
                name="search_in_files",
                description="Search for text or regex pattern across multiple files in the project",
                function_ref="filesystem_plugin.search_in_files",
                parameters={
                    "pattern": {"type": "string", "description": "Text or regex pattern"},
                    "folder": {"type": "string", "description": "Folder to search in (optional)"},
                    "use_regex": {"type": "boolean", "description": "Use regex pattern"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search"},
                    "limit": {"type": "integer", "description": "Maximum results (default: 50)"},
                },
                return_type="dict",
                category="file_io",
            ),
            Tool(
                name="replace_in_files",
                description="Search and replace text across multiple files",
                function_ref="filesystem_plugin.replace_in_files",
                parameters={
                    "search_pattern": {"type": "string", "description": "Text or regex to search"},
                    "replacement": {"type": "string", "description": "Replacement text"},
                    "folder": {"type": "string", "description": "Folder to search in (optional)"},
                    "use_regex": {"type": "boolean", "description": "Use regex pattern"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search"},
                    "file_pattern": {"type": "string", "description": "File pattern filter (e.g., *.py)"},
                },
                return_type="dict",
                category="file_io",
            ),
            Tool(
                name="get_file_tree",
                description="Get file tree structure for the project or a specific folder",
                function_ref="filesystem_plugin.get_file_tree",
                parameters={
                    "folder": {"type": "string", "description": "Folder to get tree for (optional)"},
                    "max_depth": {"type": "integer", "description": "Maximum depth (default: 5)"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files"},
                },
                return_type="dict",
                category="file_io",
            ),
            # Semantic Code Search
            Tool(
                name="semantic_code_search",
                description="Search code intelligently using semantic understanding (functions, classes, imports, keywords)",
                function_ref="semantic_search.search",
                parameters={
                    "query": {"type": "string", "description": "Search query (function name, keyword, concept)"},
                    "limit": {"type": "integer", "description": "Maximum results (default: 20)"},
                },
                return_type="dict",
                category="search",
            ),
            # New Advanced Tools
            Tool(
                name="glob_search",
                description="Search for files using glob patterns (e.g., **/*.py)",
                function_ref="tool_executor.glob_search",
                parameters={
                    "pattern": {"type": "string", "description": "Glob pattern"},
                    "path": {"type": "string", "description": "Root path to search from (default: .)"},
                },
                return_type="array",
                category="file_io",
            ),
            Tool(
                name="rip_grep",
                description="Advanced search for a pattern in file contents (regex supported)",
                function_ref="tool_executor.rip_grep",
                parameters={
                    "pattern": {"type": "string", "description": "The regular expression pattern to search for"},
                    "path": {"type": "string", "description": "File or directory to search in"},
                    "case_insensitive": {"type": "boolean", "description": "Case insensitive search"},
                    "context": {"type": "integer", "description": "Number of lines of context to show"},
                },
                return_type="dict",
                category="file_io",
            ),
            Tool(
                name="fetch_url",
                description="Fetch content from a URL safely",
                function_ref="tool_executor.fetch_url",
                parameters={
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                return_type="dict",
                category="research",
            ),
            # MCP Tools
            Tool(
                name="mcp_list_servers",
                description="List all configured MCP servers",
                function_ref="mcp_client.list_servers",
                parameters={},
                return_type="dict",
                category="mcp",
            ),
            Tool(
                name="mcp_connect",
                description="Connect to an MCP server",
                function_ref="mcp_client.connect_server",
                parameters={
                    "server_name": {"type": "string", "description": "Name of the server to connect"},
                },
                return_type="dict",
                category="mcp",
            ),
            Tool(
                name="mcp_execute",
                description="Execute a tool on an MCP server",
                function_ref="mcp_client.execute_tool",
                parameters={
                    "server_name": {"type": "string", "description": "Server name"},
                    "tool_name": {"type": "string", "description": "Tool name"},
                    "arguments": {"type": "object", "description": "Tool arguments"},
                },
                return_type="dict",
                category="mcp",
            ),
            # LSP Tools
            Tool(
                name="lsp_index",
                description="Index the project for code intelligence",
                function_ref="lsp_integration.index_project",
                parameters={},
                return_type="integer",
                category="analysis",
            ),
            Tool(
                name="lsp_definition",
                description="Find where a symbol is defined",
                function_ref="lsp_integration.go_to_definition",
                parameters={
                    "file_path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number (1-based)"},
                    "column": {"type": "integer", "description": "Column number"},
                },
                return_type="dict",
                category="analysis",
            ),
            Tool(
                name="lsp_hover",
                description="Get hover documentation for a symbol",
                function_ref="lsp_integration.get_hover_info",
                parameters={
                    "file_path": {"type": "string", "description": "File path"},
                    "line": {"type": "integer", "description": "Line number (1-based)"},
                    "column": {"type": "integer", "description": "Column number"},
                },
                return_type="dict",
                category="analysis",
            ),
            Tool(
                name="lsp_symbols",
                description="Search for symbols by name",
                function_ref="lsp_integration.search_symbols",
                parameters={
                    "query": {"type": "string", "description": "Search query"},
                    "kind": {"type": "string", "description": "Optional symbol kind"},
                },
                return_type="dict",
                category="analysis",
            ),
            Tool(
                name="notebook_edit",
                description="Edit a cell in a Jupyter notebook",
                function_ref="tool_executor.notebook_edit",
                parameters={
                    "path": {"type": "string", "description": "Notebook file path (.ipynb)"},
                    "cell_index": {"type": "integer", "description": "Index of the cell to edit"},
                    "new_content": {"type": "string", "description": "New content for the cell"},
                },
                return_type="dict",
                category="file_io",
            ),
            Tool(
                name="schedule_task",
                description="Schedule a command to run with a cron expression",
                function_ref="tool_executor.schedule_task",
                parameters={
                    "name": {"type": "string", "description": "Task name"},
                    "cron": {"type": "string", "description": "Cron expression (e.g., '0 0 * * *')"},
                    "command": {"type": "string", "description": "Command to run"},
                },
                return_type="dict",
                category="planning",
            ),
            Tool(
                name="ask_permission",
                description="Ask the user for explicit permission to perform a sensitive action",
                function_ref="permission_manager.request_approval",
                parameters={
                    "action": {"type": "string", "description": "The action requiring approval"},
                    "details": {"type": "string", "description": "Detailed explanation of why this is needed"},
                },
                return_type="dict",
                category="interaction",
            ),
            Tool(
                name="ask_user",
                description="Ask the user a question and wait for a response",
                function_ref="tool_executor.ask_user",
                parameters={
                    "question": {"type": "string", "description": "The question to ask the user"},
                },
                return_type="dict",
                category="interaction",
            ),
            Tool(
                name="spawn_subagent",
                description="Spawn a specialized sub-agent to handle a specific sub-task",
                function_ref="tool_executor.spawn_subagent",
                parameters={
                    "task": {"type": "string", "description": "The sub-task description"},
                    "role": {"type": "string", "description": "The role of the sub-agent (e.g., coder, researcher)"},
                },
                return_type="dict",
                category="planning",
            ),
            Tool(
                name="system_doctor",
                description="Check the health of the agent's environment and dependencies",
                function_ref="tool_executor.system_doctor",
                parameters={},
                return_type="dict",
                category="analysis",
            ),
            Tool(
                name="enter_worktree",
                description="Enter a new git worktree/branch for isolated development",
                function_ref="tool_executor.enter_worktree",
                parameters={
                    "branch_name": {"type": "string", "description": "Branch name"},
                },
                return_type="dict",
                category="git",
            ),
            Tool(
                name="exit_worktree",
                description="Exit the current worktree and return to the main branch",
                function_ref="tool_executor.exit_worktree",
                parameters={
                    "merge": {"type": "boolean", "description": "Merge changes into main"},
                },
                return_type="dict",
                category="git",
            ),
            Tool(
                name="repl_execute",
                description="Execute Python code in a persistent REPL session",
                function_ref="tool_executor.repl_execute",
                parameters={
                    "code": {"type": "string", "description": "Python code to execute"},
                },
                return_type="dict",
                category="execution",
            ),
        ]

    def register(self, tool: Tool) -> dict:
        """
        Register a new tool.
        
        Args:
            tool: Tool object to register
        
        Returns:
            Registration result
        """
        self.tools[tool.name] = tool
        self._save_registry()
        return {
            "status": "success",
            "tool": tool.name,
            "category": tool.category,
        }

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(
        self, category: Optional[str] = None, enabled_only: bool = True
    ) -> list[dict]:
        """
        List all tools.
        
        Args:
            category: Filter by category (None = all)
            enabled_only: Only return enabled tools
        
        Returns:
            List of tool definitions
        """
        tools = list(self.tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return [t.to_dict() for t in tools]

    def update_tool(self, name: str, updates: dict) -> dict:
        """Update a tool's metadata."""
        if name not in self.tools:
            return {
                "status": "failed",
                "error": f"Tool {name} not found",
            }

        tool = self.tools[name]
        for key, value in updates.items():
            if hasattr(tool, key):
                setattr(tool, key, value)

        self._save_registry()
        return {
            "status": "success",
            "tool": name,
            "updated_fields": list(updates.keys()),
        }

    def enable_tool(self, name: str) -> dict:
        """Enable a tool."""
        return self.update_tool(name, {"enabled": True})

    def disable_tool(self, name: str) -> dict:
        """Disable a tool."""
        return self.update_tool(name, {"enabled": False})

    def remove_tool(self, name: str) -> dict:
        """Remove a tool from the registry."""
        if name not in self.tools:
            return {
                "status": "failed",
                "error": f"Tool {name} not found",
            }

        del self.tools[name]
        self._save_registry()
        return {
            "status": "success",
            "removed": name,
        }

    def get_tools_by_category(self, category: str) -> list[dict]:
        """Get all tools in a category."""
        return self.list_tools(category=category, enabled_only=True)

    def register_function(
        self,
        tool_name: str,
        function: Callable,
    ) -> dict:
        """
        Register a Python function as a tool.
        
        Args:
            tool_name: Name of the tool
            function: Callable function
        
        Returns:
            Registration result
        """
        if tool_name not in self.tools:
            return {
                "status": "failed",
                "error": f"Tool {tool_name} not registered in registry",
            }

        self.tool_functions[tool_name] = function
        return {
            "status": "success",
            "tool": tool_name,
            "function_registered": True,
        }

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool function.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Arguments to pass to the tool
        
        Returns:
            Result from the tool function
        """
        if tool_name not in self.tool_functions:
            raise ValueError(f"Tool {tool_name} not registered with a function")

        tool = self.tools.get(tool_name)
        if not tool or not tool.enabled:
            raise ValueError(f"Tool {tool_name} is not available")

        return self.tool_functions[tool_name](**kwargs)

    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """Execute built-in runtime tools, including async service-backed tools.
        Supports sandboxed execution when payload contains 'sandbox': True.
        """
        tool = self.tools.get(tool_name)
        if not tool or not tool.enabled:
            raise ValueError(f"Tool {tool_name} is not available")

        # If caller requested sandboxed execution, attempt to run the tool module in a subprocess
        if kwargs.pop("sandbox", False):
            # Determine module and entrypoint from tool.function_ref
            try:
                module_path, entrypoint = tool.function_ref.rsplit('.', 1)
            except Exception:
                raise ValueError("Tool does not have a resolvable function_ref for sandbox execution")
            use_docker = kwargs.pop("use_docker", False)
            result = execute_module_in_sandbox(module_path, entrypoint, kwargs, use_docker=use_docker)
            return result

        tool_executor = get_tool_executor()
        if tool_name == "read_file":
            return tool_executor.read_file(kwargs["path"])
        if tool_name == "write_file":
            return tool_executor.write_file(
                kwargs["path"],
                kwargs["content"],
                kwargs.get("append", False),
            )
        if tool_name == "list_directory":
            return tool_executor.list_directory(kwargs.get("path", "."))
        if tool_name == "glob_search":
            return tool_executor.glob_search(kwargs["pattern"], kwargs.get("path", "."))
        if tool_name == "rip_grep":
            return tool_executor.rip_grep(
                kwargs["pattern"], 
                kwargs.get("path", "."),
                kwargs.get("glob"),
                kwargs.get("case_insensitive", False),
                kwargs.get("context", 0)
            )
        if tool_name == "execute_command":
            return tool_executor.execute_command(
                kwargs["command"],
                kwargs.get("cwd"),
                kwargs.get("timeout"),
            )
        if tool_name == "analyze_imports":
            return tool_executor.analyze_imports(kwargs["file_path"])
        if tool_name == "notebook_edit":
            return tool_executor.notebook_edit(kwargs["path"], kwargs["cell_index"], kwargs["new_content"])
        if tool_name == "schedule_task":
            return tool_executor.schedule_task(kwargs["name"], kwargs["cron"], kwargs["command"])
        if tool_name == "web_research":
            search = get_search_service()
            log = await search.search(kwargs["session_id"], kwargs["query"])
            return {
                "query": log.query,
                "status": log.status,
                "summary": log.summary,
                "sources": [source.model_dump() for source in log.sources],
                "render_blocks": search.build_render_blocks(log),
            }
        if tool_name == "fetch_url":
            return await tool_executor.fetch_url(kwargs["url"])
        if tool_name == "system_doctor":
            return await tool_executor.system_doctor()
        if tool_name == "enter_worktree":
            return tool_executor.enter_worktree(kwargs["branch_name"])
        if tool_name == "exit_worktree":
            return tool_executor.exit_worktree(kwargs.get("merge", False))
        if tool_name == "repl_execute":
            return tool_executor.repl_execute(kwargs["code"])
        
        # MCP operations
        from app.services.mcp_client import get_mcp_client
        mcp = get_mcp_client()
        if tool_name == "mcp_list_servers":
            return mcp.list_servers()
        if tool_name == "mcp_connect":
            return await mcp.connect_server(kwargs["server_name"])
        if tool_name == "mcp_execute":
            result = await mcp.execute_tool(kwargs["server_name"], kwargs["tool_name"], kwargs["arguments"])
            return {
                "success": result.success,
                "tool_name": result.tool_name,
                "result": result.result,
                "error": result.error,
            }

        # LSP operations
        from app.services.lsp_integration import get_lsp_integration
        lsp = get_lsp_integration()
        if tool_name == "lsp_index":
            return lsp.index_project()
        if tool_name == "lsp_definition":
            return lsp.go_to_definition(kwargs["file_path"], kwargs["line"], kwargs["column"])
        if tool_name == "lsp_hover":
            return lsp.get_hover_info(kwargs["file_path"], kwargs["line"], kwargs["column"])
        if tool_name == "lsp_symbols":
            return lsp.search_symbols(kwargs["query"], kwargs.get("kind"))

        # Permission operations
        from app.services.permission_manager import get_permission_manager
        pm = get_permission_manager()
        if tool_name == "ask_permission":
            return pm.request_approval(kwargs["action"], kwargs["details"])
        if tool_name == "ask_user":
            return tool_executor.ask_user(kwargs["question"])
        if tool_name == "spawn_subagent":
            return await tool_executor.spawn_subagent(kwargs["task"], kwargs.get("role", "coder"))

        if tool_name == "build_visualization":
            response = build_visualization_response(
                kwargs.get("data") or kwargs["prompt"]
            )
            if response is None:
                return {
                    "status": "failed",
                    "error": "No visualization could be derived from the provided input.",
                }
            return {"status": "success", **response}
        if tool_name == "list_artifacts":
            artifacts = get_artifact_service()
            return await artifacts.list_artifacts(kwargs["session_id"], limit=24)
        if tool_name == "reopen_artifact":
            artifacts = get_artifact_service()
            artifact = await artifacts.get_artifact(kwargs["artifact_id"])
            if artifact is None:
                return {"status": "failed", "error": "Artifact not found"}
            return {
                "status": "success",
                "artifact": artifact,
                "render_blocks": self._artifact_render_blocks(artifact),
            }
        if tool_name == "session_analytics":
            history = get_history_service()
            artifacts = get_artifact_service()
            session = await history.get_session(kwargs["session_id"])
            rows = await artifacts.list_artifacts(kwargs["session_id"], limit=12)
            return build_session_analytics_payload(session, rows)
        if tool_name == "session_history":
            history = get_history_service()
            session = await history.get_session(kwargs["session_id"])
            if session is None:
                return {"status": "failed", "error": "Session not found"}
            messages = session.get("messages", [])
            return {
                "status": "success",
                "session_id": session["id"],
                "title": session.get("title", ""),
                "message_count": len(messages),
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content[:240],
                    }
                    for message in messages[-8:]
                ],
            }

        # Git operations
        git = get_git_integration()
        if git and git.is_git_repo():
            if tool_name == "git_status":
                status = await git.get_status()
                return {
                    "status": "success",
                    "branch": status.branch,
                    "is_clean": status.is_clean,
                    "staged": status.staged_changes,
                    "unstaged": status.unstaged_changes,
                    "untracked": status.untracked_files,
                }
            if tool_name == "git_commit":
                if kwargs.get("files"):
                    await git.stage_files(kwargs["files"])
                success = await git.commit(kwargs["message"])
                return {"status": "success" if success else "failed", "committed": success}
            if tool_name == "git_branch_create":
                success = await git.create_branch(kwargs["branch_name"], kwargs.get("from_branch", ""))
                return {"status": "success" if success else "failed", "branch": kwargs["branch_name"]}
            if tool_name == "git_branch_checkout":
                success = await git.checkout_branch(kwargs["branch_name"])
                return {"status": "success" if success else "failed", "branch": kwargs["branch_name"]}
            if tool_name == "git_branches":
                branches = await git.list_branches()
                return {"status": "success", "branches": branches}
            if tool_name == "git_push":
                success = await git.push(kwargs.get("remote", "origin"), kwargs.get("branch", ""))
                return {"status": "success" if success else "failed"}
            if tool_name == "git_pull":
                success = await git.pull(kwargs.get("remote", "origin"), kwargs.get("branch", ""))
                return {"status": "success" if success else "failed"}
            if tool_name == "git_log":
                commits = await git.get_log(kwargs.get("count", 20))
                return {"status": "success", "commits": commits, "count": len(commits)}
            if tool_name == "git_diff":
                diff = await git.get_diff(kwargs.get("file_path", ""))
                return {"status": "success", "diff": diff[:5000] if diff else ""}
            if tool_name == "git_commit_suggestion":
                suggestion = await git.generate_commit_message()
                return {"status": "success", "message": suggestion.message, "type": suggestion.type}

        # Filesystem plugin operations
        from app.plugins.filesystem.plugin import FileSystemPlugin
        import os
        fs_plugin = FileSystemPlugin(os.getcwd())
        
        if tool_name == "search_in_files":
            result = fs_plugin.search_in_files(
                kwargs.get("pattern", ""),
                kwargs.get("folder"),
                kwargs.get("use_regex", False),
                kwargs.get("case_sensitive", False),
                kwargs.get("limit", 50),
            )
            return result
        if tool_name == "replace_in_files":
            result = fs_plugin.replace_in_files(
                kwargs.get("search_pattern", ""),
                kwargs.get("replacement", ""),
                kwargs.get("folder"),
                kwargs.get("use_regex", False),
                kwargs.get("case_sensitive", False),
                kwargs.get("file_pattern"),
            )
            return result
        if tool_name == "get_file_tree":
            result = fs_plugin.get_file_tree(
                kwargs.get("folder"),
                kwargs.get("max_depth", 5),
                kwargs.get("include_hidden", False),
            )
            return result

        # Semantic code search
        from app.services.semantic_search import get_semantic_search
        semantic_search = get_semantic_search()
        
        if tool_name == "semantic_code_search":
            result = semantic_search.search(
                kwargs.get("query", ""),
                kwargs.get("limit", 20),
            )
            return result

        if tool_name in self.tool_functions:
            result = self.tool_functions[tool_name](**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        raise ValueError(f"Tool {tool_name} does not have a runtime implementation")

    def _artifact_render_blocks(self, artifact: dict) -> list[dict]:
        """Convert a saved artifact into structured render blocks for reopening."""
        if artifact.get("kind") == "research":
            metadata = artifact.get("metadata", {})
            sources = metadata.get("sources", [])
            summary = artifact.get("content", "").splitlines()[0] if artifact.get("content") else artifact["title"]
            return [
                {
                    "type": "research_result",
                    "payload": {
                        "query": metadata.get("query", artifact["title"]),
                        "provider": metadata.get("provider", "unknown"),
                        "query_plan": metadata.get("query_variants", []),
                        "conflict": metadata.get("conflict", ""),
                        "confidence": metadata.get("confidence", "medium"),
                        "freshness": metadata.get("freshness", ""),
                        "sources": sources,
                    },
                },
                {
                    "type": "report",
                    "payload": {
                        "title": artifact["title"],
                        "summary": summary,
                        "highlights": [
                            f"{len(sources)} sources loaded from research memory",
                            f"Confidence: {metadata.get('confidence', 'medium')}",
                        ],
                    },
                },
            ]
        return [
            {
                "type": "file_result",
                "payload": {
                    "title": artifact["title"],
                    "files": [
                        {
                            "path": artifact["title"],
                            "summary": artifact.get("metadata", {}).get("preview", artifact.get("content", "")[:240]),
                        }
                    ],
                },
            }
        ]

    def to_openai_schema(self) -> list[dict]:
        """
        Convert tools to OpenAI function calling schema.
        
        Useful for integrating with LLM function calling APIs.
        """
        schema = []
        for tool in self.tools.values():
            if not tool.enabled:
                continue

            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.parameters,
                            "required": list(tool.parameters.keys()),
                        },
                    },
                }
            )

        return schema

    def _resolve_function(self, function_ref: str):
        """
        Resolve a dotted function reference like 'module.sub.module.func' to a callable.
        Attempts regular import first, then falls back to loading from a file path under the project.
        """
        import importlib
        import importlib.util
        import sys

        try:
            module_name, func_name = function_ref.rsplit(".", 1)
        except ValueError:
            return None

        # Try normal import
        try:
            module = importlib.import_module(module_name)
        except Exception:
            # Fallback: attempt to load module from project extensions or file path
            project_root = Path(settings.backend_root).parent.parent
            module_path = project_root / Path(module_name.replace(".", "/")).with_suffix(".py")
            if module_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                except Exception:
                    return None
            else:
                return None

        func = getattr(module, func_name, None)
        if callable(func):
            return func
        return None

    def _load_functions(self) -> None:
        """
        Attempt to load callable implementations for any tools that declare a function_ref.
        This allows tools saved in the registry to be immediately usable after startup.
        """
        for name, tool in list(self.tools.items()):
            if not tool.function_ref:
                continue
            try:
                func = self._resolve_function(tool.function_ref)
                if func:
                    self.tool_functions[name] = func
            except Exception:
                # Silently ignore; function may be loaded later via register_code
                pass

    def register_code(self, tool_name: str, code: str, entrypoint: str = "run") -> dict:
        """
        Persist source code for a tool into the project 'extensions' folder and attempt to register its entrypoint.
        The saved module will be named 'extensions.<tool_name>'.
        """
        project_root = Path(settings.backend_root).parent.parent
        ext_dir = project_root / "extensions"
        ext_dir.mkdir(parents=True, exist_ok=True)
        file_path = ext_dir / f"{tool_name}.py"

        try:
            file_path.write_text(code, encoding="utf-8")
        except Exception as e:
            return {"status": "failed", "error": f"Failed to write code file: {e}"}

        module_name = f"extensions.{tool_name}"
        tool = self.tools.get(tool_name)
        if tool:
            # Update function_ref to point to the expected entrypoint
            tool.function_ref = f"{module_name}.{entrypoint}"
            self._save_registry()

        # Try to resolve and register the function
        func = self._resolve_function(tool.function_ref)
        if not func:
            return {"status": "failed", "error": "Could not resolve function after writing code"}

        self.tool_functions[tool_name] = func
        return {"status": "success", "tool": tool_name, "registered": True}


def get_dynamic_tool_registry() -> DynamicToolRegistry:
    """Dependency for FastAPI endpoints."""
    registry = DynamicToolRegistry()
    # Attempt to load any functions declared in the registry on startup
    try:
        registry._load_functions()
    except Exception:
        pass
    return registry
