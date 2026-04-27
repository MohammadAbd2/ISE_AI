"""
Response Formatter Module for Manus-Refined Architecture

This module formats agent responses with professional styling, icons, bold formatting,
and ChatGPT-style follow-up suggestions.
"""

from typing import Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json


class ResponseType(Enum):
    """Types of agent responses."""
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    PLANNING = "planning"
    REFACTORING = "refactoring"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


@dataclass
class Suggestion:
    """Represents a follow-up suggestion."""
    text: str
    icon: str = "💡"
    action_type: str = "query"  # "query", "action", "refinement"


class IconLibrary:
    """Library of icons for different contexts."""
    
    # Agent roles
    AGENT_ICONS = {
        "orchestrator": "🎯",
        "planner": "📋",
        "coder": "💻",
        "web_interaction": "🌐",
        "self_reflection": "🔍",
        "self_improvement": "⚡",
        "debugger": "🐛",
        "research": "📚"
    }

    # Response types
    RESPONSE_ICONS = {
        "code_generation": "✨",
        "analysis": "📊",
        "debugging": "🔧",
        "research": "🔎",
        "planning": "📐",
        "refactoring": "🔄",
        "error": "❌",
        "success": "✅",
        "info": "ℹ️"
    }

    # Status indicators
    STATUS_ICONS = {
        "pending": "⏳",
        "in_progress": "⚙️",
        "completed": "✅",
        "failed": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
    }

    # Action icons
    ACTION_ICONS = {
        "execute": "▶️",
        "test": "🧪",
        "deploy": "🚀",
        "rollback": "↩️",
        "monitor": "📡",
        "optimize": "⚡",
        "document": "📖",
        "review": "👁️"
    }

    @staticmethod
    def get_icon(category: str, key: str, default: str = "•") -> str:
        """Get an icon from the library."""
        icons_map = {
            "agent": IconLibrary.AGENT_ICONS,
            "response": IconLibrary.RESPONSE_ICONS,
            "status": IconLibrary.STATUS_ICONS,
            "action": IconLibrary.ACTION_ICONS
        }
        return icons_map.get(category, {}).get(key, default)


class ResponseFormatter:
    """
    Formats agent responses with professional styling and enhancements.
    """

    def __init__(self):
        """Initialize the response formatter."""
        self.icon_library = IconLibrary()

    def format_agent_response(self, agent_role: str, response_type: ResponseType,
                             content: str, metadata: Optional[dict] = None,
                             suggestions: Optional[List[Suggestion]] = None) -> str:
        """
        Format an agent response with professional styling.
        
        Args:
            agent_role: Role of the agent providing the response
            response_type: Type of response
            content: The main response content
            metadata: Optional metadata about the response
            suggestions: Optional list of follow-up suggestions
            
        Returns:
            Formatted response string
        """
        formatted_response = ""

        # Header with agent role and response type
        agent_icon = self.icon_library.get_icon("agent", agent_role, "🤖")
        response_icon = self.icon_library.get_icon("response", response_type.value, "•")

        formatted_response += f"{agent_icon} **{agent_role.replace('_', ' ').title()}** {response_icon} {response_type.value.replace('_', ' ').title()}\n"
        formatted_response += "---\n\n"

        # Main content
        formatted_response += content + "\n\n"

        # Metadata if provided
        if metadata:
            formatted_response += self._format_metadata(metadata)

        # Suggestions
        if suggestions:
            formatted_response += self._format_suggestions(suggestions)

        return formatted_response

    def format_code_response(self, code: str, language: str = "python",
                            explanation: Optional[str] = None) -> str:
        """
        Format a code response with syntax highlighting and explanation.
        
        Args:
            code: The code to format
            language: Programming language
            explanation: Optional explanation of the code
            
        Returns:
            Formatted code response
        """
        formatted = f"✨ **Generated Code** ({language})\n\n"
        formatted += f"```{language}\n{code}\n```\n\n"

        if explanation:
            formatted += f"📝 **Explanation:**\n{explanation}\n\n"

        return formatted

    def format_error_response(self, error_message: str, error_type: str = "error",
                             suggested_fix: Optional[str] = None,
                             diagnostic_info: Optional[dict] = None) -> str:
        """
        Format an error response with diagnostic information.
        
        Args:
            error_message: The error message
            error_type: Type of error
            suggested_fix: Optional suggested fix
            diagnostic_info: Optional diagnostic information
            
        Returns:
            Formatted error response
        """
        formatted = f"❌ **Error: {error_type.replace('_', ' ').title()}**\n\n"
        formatted += f"**Error Message:**\n```\n{error_message}\n```\n\n"

        if suggested_fix:
            formatted += f"🔧 **Suggested Fix:**\n{suggested_fix}\n\n"

        if diagnostic_info:
            formatted += self._format_diagnostic_info(diagnostic_info)

        return formatted

    def format_analysis_response(self, analysis_title: str, findings: List[str],
                                metrics: Optional[dict] = None,
                                recommendations: Optional[List[str]] = None) -> str:
        """
        Format an analysis response with findings and recommendations.
        
        Args:
            analysis_title: Title of the analysis
            findings: List of findings
            metrics: Optional metrics dictionary
            recommendations: Optional list of recommendations
            
        Returns:
            Formatted analysis response
        """
        formatted = f"📊 **{analysis_title}**\n\n"

        formatted += "**Key Findings:**\n"
        for i, finding in enumerate(findings, 1):
            formatted += f"{i}. {finding}\n"
        formatted += "\n"

        if metrics:
            formatted += self._format_metrics(metrics)

        if recommendations:
            formatted += "**Recommendations:**\n"
            for i, rec in enumerate(recommendations, 1):
                formatted += f"{i}. {rec}\n"
            formatted += "\n"

        return formatted

    def format_planning_response(self, plan_title: str, steps: List[dict],
                                estimated_duration: Optional[str] = None,
                                resource_requirements: Optional[List[str]] = None) -> str:
        """
        Format a planning response with steps and resource requirements.
        
        Args:
            plan_title: Title of the plan
            steps: List of steps (each step is a dict with 'description', 'duration', 'tools')
            estimated_duration: Optional total estimated duration
            resource_requirements: Optional list of resource requirements
            
        Returns:
            Formatted planning response
        """
        formatted = f"📋 **{plan_title}**\n\n"

        formatted += "**Execution Plan:**\n"
        for i, step in enumerate(steps, 1):
            description = step.get("description", "")
            duration = step.get("duration", "")
            tools = step.get("tools", [])

            formatted += f"{i}. **{description}**\n"
            if duration:
                formatted += f"   ⏱️ Duration: {duration}\n"
            if tools:
                formatted += f"   🛠️ Tools: {', '.join(tools)}\n"

        formatted += "\n"

        if estimated_duration:
            formatted += f"⏱️ **Total Estimated Duration:** {estimated_duration}\n\n"

        if resource_requirements:
            formatted += "**Resource Requirements:**\n"
            for req in resource_requirements:
                formatted += f"• {req}\n"
            formatted += "\n"

        return formatted

    def _format_metadata(self, metadata: dict) -> str:
        """Format metadata section."""
        formatted = "**Metadata:**\n"
        for key, value in metadata.items():
            formatted += f"• **{key.replace('_', ' ').title()}:** {value}\n"
        formatted += "\n"
        return formatted

    def _format_metrics(self, metrics: dict) -> str:
        """Format metrics section."""
        formatted = "**Metrics:**\n"
        for key, value in metrics.items():
            formatted += f"• **{key.replace('_', ' ').title()}:** {value}\n"
        formatted += "\n"
        return formatted

    def _format_diagnostic_info(self, diagnostic_info: dict) -> str:
        """Format diagnostic information."""
        formatted = "**Diagnostic Information:**\n"
        for key, value in diagnostic_info.items():
            if isinstance(value, dict):
                formatted += f"• **{key.replace('_', ' ').title()}:**\n"
                for sub_key, sub_value in value.items():
                    formatted += f"  - {sub_key}: {sub_value}\n"
            else:
                formatted += f"• **{key.replace('_', ' ').title()}:** {value}\n"
        formatted += "\n"
        return formatted

    def _format_suggestions(self, suggestions: List[Suggestion]) -> str:
        """Format follow-up suggestions in ChatGPT style."""
        formatted = "---\n\n"
        formatted += "**💡 Suggestions for Next Steps:**\n\n"

        for i, suggestion in enumerate(suggestions, 1):
            formatted += f"{i}. {suggestion.icon} **{suggestion.text}**\n"

        formatted += "\n"
        return formatted

    def create_suggestions(self, response_type: ResponseType,
                          context: Optional[dict] = None) -> List[Suggestion]:
        """
        Create context-aware follow-up suggestions.
        
        Args:
            response_type: Type of response
            context: Optional context information
            
        Returns:
            List of Suggestion objects
        """
        suggestions = []

        if response_type == ResponseType.CODE_GENERATION:
            suggestions.extend([
                Suggestion("Test the generated code with unit tests", "🧪", "action"),
                Suggestion("Review the code for potential improvements", "👁️", "action"),
                Suggestion("Deploy the code to a staging environment", "🚀", "action"),
            ])

        elif response_type == ResponseType.DEBUGGING:
            suggestions.extend([
                Suggestion("Apply the suggested fix and re-run tests", "🔧", "action"),
                Suggestion("Monitor the system for similar errors", "📡", "action"),
                Suggestion("Document this error and its solution", "📖", "action"),
            ])

        elif response_type == ResponseType.ANALYSIS:
            suggestions.extend([
                Suggestion("Dive deeper into the top finding", "🔍", "query"),
                Suggestion("Compare with previous analysis results", "📊", "query"),
                Suggestion("Implement the recommended improvements", "⚡", "action"),
            ])

        elif response_type == ResponseType.PLANNING:
            suggestions.extend([
                Suggestion("Review and refine the execution plan", "📋", "refinement"),
                Suggestion("Identify potential risks and mitigation strategies", "⚠️", "query"),
                Suggestion("Begin executing the first step of the plan", "▶️", "action"),
            ])

        elif response_type == ResponseType.RESEARCH:
            suggestions.extend([
                Suggestion("Summarize the key findings from the research", "📚", "query"),
                Suggestion("Explore related topics for deeper understanding", "🔎", "query"),
                Suggestion("Create a knowledge base entry for future reference", "💾", "action"),
            ])

        return suggestions

    def format_streaming_update(self, status: str, progress: int,
                               current_task: str, icon: str = "⚙️") -> str:
        """
        Format a streaming progress update.
        
        Args:
            status: Current status
            progress: Progress percentage (0-100)
            current_task: Description of current task
            icon: Icon to use
            
        Returns:
            Formatted progress update
        """
        progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
        return f"{icon} **{status}** [{progress_bar}] {progress}% - {current_task}"
