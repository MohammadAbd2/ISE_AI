"""
Prompt Optimizer Module for Manus-Refined Architecture

This module implements autonomous prompt optimization and refinement.
The Prompt Optimizer analyzes prompt effectiveness, identifies issues,
and generates improved versions to enhance agent performance.
"""

import json
from datetime import datetime
from typing import Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    """Represents a prompt template for an agent."""
    template_id: str
    agent_role: str
    base_prompt: str
    context_variables: List[str]
    version: int = 1
    effectiveness_score: float = 0.5
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PromptAnalysis:
    """Represents an analysis of prompt effectiveness."""
    template_id: str
    analysis_timestamp: datetime
    success_rate: float
    average_response_quality: float
    common_errors: List[str]
    improvement_suggestions: List[str]
    recommended_changes: dict[str, Any]


class PromptOptimizer:
    """
    Autonomous prompt optimization engine.
    
    This engine:
    - Tracks prompt effectiveness metrics
    - Analyzes failure patterns
    - Generates improved prompt versions
    - Manages prompt versioning and rollback
    - Learns optimal prompt structures for different task types
    """

    def __init__(self):
        """Initialize the prompt optimizer."""
        self.prompt_templates: dict[str, PromptTemplate] = {}
        self.prompt_history: dict[str, List[PromptTemplate]] = {}
        self.analysis_history: dict[str, List[PromptAnalysis]] = {}
        self.optimization_metrics: dict[str, Any] = {}

    def register_prompt_template(self, template_id: str, agent_role: str,
                                base_prompt: str, context_variables: List[str]) -> PromptTemplate:
        """
        Register a new prompt template.
        
        Args:
            template_id: Unique identifier for the template
            agent_role: Role of the agent using this prompt
            base_prompt: The base prompt text
            context_variables: List of context variables the prompt uses
            
        Returns:
            The created PromptTemplate
        """
        template = PromptTemplate(
            template_id=template_id,
            agent_role=agent_role,
            base_prompt=base_prompt,
            context_variables=context_variables
        )
        self.prompt_templates[template_id] = template
        self.prompt_history[template_id] = [template]
        return template

    def record_prompt_execution(self, template_id: str, success: bool,
                               response_quality: float = 0.5,
                               error_message: Optional[str] = None):
        """
        Record the execution result of a prompt.
        
        Args:
            template_id: ID of the prompt template used
            success: Whether the execution was successful
            response_quality: Quality score of the response (0-1)
            error_message: Optional error message if execution failed
        """
        if template_id not in self.prompt_templates:
            return

        template = self.prompt_templates[template_id]
        template.usage_count += 1

        if success:
            template.success_count += 1
            template.effectiveness_score = (template.success_count / template.usage_count) * response_quality
        else:
            template.failure_count += 1
            template.effectiveness_score = template.success_count / template.usage_count

    def analyze_prompt_effectiveness(self, template_id: str) -> PromptAnalysis:
        """
        Analyze the effectiveness of a prompt template.
        
        Args:
            template_id: ID of the prompt template to analyze
            
        Returns:
            PromptAnalysis object with findings and recommendations
        """
        if template_id not in self.prompt_templates:
            return None

        template = self.prompt_templates[template_id]
        success_rate = (template.success_count / template.usage_count) if template.usage_count > 0 else 0

        # Identify common error patterns
        common_errors = self._identify_common_errors(template_id)

        # Generate improvement suggestions
        improvement_suggestions = self._generate_improvement_suggestions(template, success_rate, common_errors)

        # Recommend specific changes
        recommended_changes = self._recommend_prompt_changes(template, common_errors)

        analysis = PromptAnalysis(
            template_id=template_id,
            analysis_timestamp=datetime.now(),
            success_rate=success_rate,
            average_response_quality=template.effectiveness_score,
            common_errors=common_errors,
            improvement_suggestions=improvement_suggestions,
            recommended_changes=recommended_changes
        )

        if template_id not in self.analysis_history:
            self.analysis_history[template_id] = []
        self.analysis_history[template_id].append(analysis)

        return analysis

    def _identify_common_errors(self, template_id: str) -> List[str]:
        """Identify common error patterns from execution history."""
        # This is a simplified implementation
        # In a real system, this would analyze detailed error logs
        common_errors = [
            "Ambiguous task description",
            "Missing context variables",
            "Unclear expected output format"
        ]
        return common_errors

    def _generate_improvement_suggestions(self, template: PromptTemplate,
                                         success_rate: float,
                                         common_errors: List[str]) -> List[str]:
        """Generate suggestions for improving the prompt."""
        suggestions = []

        if success_rate < 0.7:
            suggestions.append("🔴 **Low Success Rate**: Consider adding more specific instructions or examples.")

        if success_rate < 0.5:
            suggestions.append("🔴 **Critical**: Prompt needs major revision. Consider adding step-by-step guidance.")

        if "Ambiguous task description" in common_errors:
            suggestions.append("📝 **Clarity**: Add more specific examples of expected behavior.")

        if "Missing context variables" in common_errors:
            suggestions.append("🔗 **Context**: Ensure all required context variables are provided.")

        if success_rate > 0.8:
            suggestions.append("✅ **Excellent Performance**: This prompt is working well. Minor tweaks may further improve it.")

        return suggestions

    def _recommend_prompt_changes(self, template: PromptTemplate,
                                 common_errors: List[str]) -> dict[str, Any]:
        """Recommend specific changes to the prompt."""
        recommendations = {
            "add_examples": "Ambiguous task description" in common_errors,
            "add_context_injection": "Missing context variables" in common_errors,
            "clarify_output_format": True,
            "add_error_handling_instructions": template.failure_count > 5,
            "increase_specificity": template.effectiveness_score < 0.6
        }
        return recommendations

    def generate_improved_prompt(self, template_id: str, analysis: PromptAnalysis) -> str:
        """
        Generate an improved version of a prompt based on analysis.
        
        Args:
            template_id: ID of the prompt template
            analysis: PromptAnalysis with recommendations
            
        Returns:
            Improved prompt text
        """
        if template_id not in self.prompt_templates:
            return None

        template = self.prompt_templates[template_id]
        improved_prompt = template.base_prompt

        # Apply recommendations
        if analysis.recommended_changes.get("add_examples"):
            improved_prompt += "\n\n📌 **Examples:**\n- Example 1: [specific example]\n- Example 2: [specific example]"

        if analysis.recommended_changes.get("clarify_output_format"):
            improved_prompt += "\n\n📋 **Expected Output Format:**\n- Use clear, structured formatting\n- Include relevant details\n- Provide reasoning when applicable"

        if analysis.recommended_changes.get("add_error_handling_instructions"):
            improved_prompt += "\n\n⚠️ **Error Handling:**\nIf you encounter an error, provide:\n1. Error description\n2. Root cause analysis\n3. Suggested fix"

        if analysis.recommended_changes.get("increase_specificity"):
            improved_prompt += "\n\n🎯 **Specificity Requirements:**\n- Be precise in your instructions\n- Avoid vague terms\n- Use concrete examples"

        return improved_prompt

    def apply_prompt_improvement(self, template_id: str, improved_prompt: str) -> PromptTemplate:
        """
        Apply an improved prompt version.
        
        Args:
            template_id: ID of the prompt template
            improved_prompt: The improved prompt text
            
        Returns:
            The updated PromptTemplate
        """
        if template_id not in self.prompt_templates:
            return None

        old_template = self.prompt_templates[template_id]

        # Create new version
        new_template = PromptTemplate(
            template_id=template_id,
            agent_role=old_template.agent_role,
            base_prompt=improved_prompt,
            context_variables=old_template.context_variables,
            version=old_template.version + 1
        )

        # Update templates
        self.prompt_templates[template_id] = new_template
        self.prompt_history[template_id].append(new_template)

        return new_template

    def rollback_prompt(self, template_id: str, version: int) -> Optional[PromptTemplate]:
        """
        Rollback a prompt to a previous version.
        
        Args:
            template_id: ID of the prompt template
            version: Version number to rollback to
            
        Returns:
            The rolled-back PromptTemplate
        """
        if template_id not in self.prompt_history:
            return None

        history = self.prompt_history[template_id]
        for template in history:
            if template.version == version:
                self.prompt_templates[template_id] = template
                return template

        return None

    def get_optimization_metrics(self) -> dict[str, Any]:
        """Get overall optimization metrics."""
        total_templates = len(self.prompt_templates)
        avg_effectiveness = sum(t.effectiveness_score for t in self.prompt_templates.values()) / total_templates if total_templates > 0 else 0
        total_executions = sum(t.usage_count for t in self.prompt_templates.values())
        total_successes = sum(t.success_count for t in self.prompt_templates.values())

        return {
            "total_templates": total_templates,
            "average_effectiveness_score": avg_effectiveness,
            "total_executions": total_executions,
            "total_successes": total_successes,
            "overall_success_rate": (total_successes / total_executions) if total_executions > 0 else 0,
            "templates_needing_improvement": len([t for t in self.prompt_templates.values() if t.effectiveness_score < 0.6])
        }

    def get_prompt_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a prompt template by ID."""
        return self.prompt_templates.get(template_id)

    def list_all_templates(self) -> List[PromptTemplate]:
        """List all registered prompt templates."""
        return list(self.prompt_templates.values())

    def get_template_history(self, template_id: str) -> Optional[List[PromptTemplate]]:
        """Get the version history of a prompt template."""
        return self.prompt_history.get(template_id)
