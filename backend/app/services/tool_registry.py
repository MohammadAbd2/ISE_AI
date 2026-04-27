"""
Unified Tool Registry for ISE_AI

Provides a centralized registry for all available tools, enabling dynamic discovery,
validation, and execution of tools by agents.
"""

from __future__ import annotations

import re

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class ToolCategory(str, Enum):
    """Categories of tools available to agents."""

    CODE_EXECUTION = "code_execution"
    FILE_SYSTEM = "file_system"
    WEB_INTERACTION = "web_interaction"
    VERSION_CONTROL = "version_control"
    EXTERNAL_API = "external_api"
    MEDIA_GENERATION = "media_generation"
    RESEARCH = "research"
    DEBUGGING = "debugging"
    TESTING = "testing"
    UTILITY = "utility"


@dataclass(slots=True)
class ToolParameter:
    """Represents a parameter for a tool."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: list[str] | None = None


@dataclass(slots=True)
class ToolDefinition:
    """Represents the definition of a tool."""

    name: str
    category: ToolCategory
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "str"
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    requires_approval: bool = False
    timeout_seconds: int = 30


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given parameters."""
        pass

    def validate_parameters(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate parameters against the tool definition."""
        definition = self.definition
        required_params = {p.name for p in definition.parameters if p.required}
        provided_params = set(kwargs.keys())

        missing = required_params - provided_params
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"

        for param in definition.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                if not self._validate_type(value, param.type):
                    return False, f"Parameter '{param.name}' has invalid type. Expected {param.type}, got {type(value).__name__}"

                if param.enum_values and value not in param.enum_values:
                    return False, f"Parameter '{param.name}' must be one of {param.enum_values}"

        return True, ""

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate if a value matches the expected type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected_class = type_mapping.get(expected_type)
        if expected_class is None:
            return True
        return isinstance(value, expected_class)


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._categories: dict[ToolCategory, list[str]] = {cat: [] for cat in ToolCategory}

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        definition = tool.definition
        self._tools[definition.name] = tool
        self._categories[definition.category].append(definition.name)

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool from the registry."""
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            category = tool.definition.category
            self._categories[category].remove(tool_name)
            del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def get_tools_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_tools(self) -> list[ToolDefinition]:
        """List all available tools."""
        return [tool.definition for tool in self._tools.values()]

    def list_tools_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """List all tools in a category."""
        return [tool.definition for tool in self.get_tools_by_category(category)]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> tuple[bool, str]:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if tool is None:
            return False, f"Tool '{tool_name}' not found."

        is_valid, error_msg = tool.validate_parameters(**kwargs)
        if not is_valid:
            return False, error_msg

        try:
            result = await tool.execute(**kwargs)
            return True, result
        except Exception as exc:
            return False, f"Tool execution failed: {str(exc)}"

    def get_tool_suggestions(self, task_description: str) -> list[ToolDefinition]:
        """Suggest tools using names, descriptions, tags, and light semantic aliases."""
        normalized = task_description.lower()
        keywords = re.findall(r"[a-z0-9_+-]+", normalized)
        alias_groups = {
            "image": {"image", "picture", "photo", "draw", "illustration", "art", "poster", "logo"},
            "web": {"search", "browse", "research", "internet", "lookup", "find", "latest"},
            "code": {"code", "python", "react", "component", "fix", "debug", "script", "execute"},
            "file": {"file", "folder", "directory", "write", "read", "save", "edit"},
        }
        expanded = set(keywords)
        for group in alias_groups.values():
            if expanded.intersection(group):
                expanded.update(group)

        suggestions = []
        for tool in self._tools.values():
            definition = tool.definition
            haystacks = [definition.name.lower(), definition.description.lower(), " ".join(tag.lower() for tag in definition.tags)]
            score = 0
            for keyword in expanded:
                if any(keyword == part for part in re.findall(r"[a-z0-9_+-]+", definition.name.lower())):
                    score += 4
                if any(keyword in hay for hay in haystacks):
                    score += 2
            if definition.category.value.lower().replace("_", " ") in normalized:
                score += 3
            if score > 0:
                suggestions.append((definition, score))

        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [def_ for def_, _ in suggestions[:5]]


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


# Example tool implementations

class PythonExecutorTool(BaseTool):
    """Tool for executing Python code."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="python_executor",
            category=ToolCategory.CODE_EXECUTION,
            description="Execute Python code in a sandboxed environment.",
            parameters=[
                ToolParameter(
                    name="code",
                    type="str",
                    description="Python code to execute",
                    required=True,
                ),
                ToolParameter(
                    name="timeout",
                    type="int",
                    description="Execution timeout in seconds",
                    required=False,
                    default=10,
                ),
            ],
            returns="str",
            examples=["python_executor(code='print(1 + 1)')"],
            tags=["python", "code", "execution"],
        )

    async def execute(self, **kwargs: Any) -> str:
        code = kwargs.get("code", "")
        timeout = kwargs.get("timeout", 10)
        try:
            import asyncio

            result = await asyncio.wait_for(self._run_code(code), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return f"Code execution timed out after {timeout} seconds."
        except Exception as exc:
            return f"Error executing code: {str(exc)}"

    async def _run_code(self, code: str) -> str:
        import subprocess

        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr


class WebScraperTool(BaseTool):
    """Tool for scraping web pages."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_scraper",
            category=ToolCategory.WEB_INTERACTION,
            description="Scrape content from a web page.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="str",
                    description="URL to scrape",
                    required=True,
                ),
            ],
            returns="str",
            examples=["web_scraper(url=\'https://example.com\')"],
            tags=["web", "scraping", "research"],
        )

    async def execute(self, **kwargs: Any) -> str:
        url = kwargs.get("url", "")
        from app.services.web_scraper import WebScraperService

        scraper = WebScraperService()
        content = await scraper.fetch_page(url)
        if content:
            return f"Title: {content.title}\n\nContent:\n{content.content}"
        return "Failed to scrape the page."


class WebResearchTool(BaseTool):
    """Tool for conducting web research on a given topic."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_research_agent",
            category=ToolCategory.RESEARCH,
            description="Conduct comprehensive web research on a specified topic, aggregating information from multiple sources.",
            parameters=[
                ToolParameter(
                    name="topic",
                    type="str",
                    description="The topic to research",
                    required=True,
                ),
                ToolParameter(
                    name="num_sources",
                    type="int",
                    description="Number of sources to consult (default: 5)",
                    required=False,
                    default=5,
                ),
            ],
            returns="str",
            examples=["web_research_agent(topic=\'AI agent architectures\', num_sources=3)"],
            tags=["web", "research", "information_gathering"],
        )

    async def execute(self, **kwargs: Any) -> str:
        topic = kwargs.get("topic", "")
        num_sources = kwargs.get("num_sources", 5)
        from app.services.web_scraper import WebResearchAgent

        research_agent = WebResearchAgent()
        result = await research_agent.research_topic(topic, num_sources)
        if result.sources:
            return f"Research Summary for \'{result.query}\':\n{result.synthesized_summary}\n\nConfidence: {result.confidence_score:.2f}"
        return f"No relevant information found for \'{topic}\' after research."
