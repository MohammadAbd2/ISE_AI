"""
Dynamic tool registry for extensible AI capabilities.
Allows the AI to register new tools and capabilities at runtime.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from backend.app.core.config import settings


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
        """Initialize default tools if empty."""
        if not self.tools:
            # File I/O tools
            self.register(
                Tool(
                    name="read_file",
                    description="Read the contents of a file",
                    function_ref="tool_executor.read_file",
                    parameters={
                        "path": {"type": "string", "description": "File path"}
                    },
                    return_type="str",
                    category="file_io",
                )
            )
            self.register(
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
                )
            )

            # Execution tools
            self.register(
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
                )
            )

            # Capability management tools
            self.register(
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
                )
            )

            self.register(
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
                )
            )

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
