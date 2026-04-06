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
from app.services.visualization_runtime import build_visualization_response


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
        """Execute built-in runtime tools, including async service-backed tools."""
        tool = self.tools.get(tool_name)
        if not tool or not tool.enabled:
            raise ValueError(f"Tool {tool_name} is not available")

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
        if tool_name == "execute_command":
            return tool_executor.execute_command(
                kwargs["command"],
                kwargs.get("cwd"),
                kwargs.get("timeout"),
            )
        if tool_name == "analyze_imports":
            return tool_executor.analyze_imports(kwargs["file_path"])
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


def get_dynamic_tool_registry() -> DynamicToolRegistry:
    """Dependency for FastAPI endpoints."""
    return DynamicToolRegistry()
