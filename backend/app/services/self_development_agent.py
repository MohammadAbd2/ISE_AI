"""
Self-Development Agent

This agent enables the chatbot to improve itself by:
- Learning from user interactions
- Adding new capabilities dynamically
- Improving response quality based on feedback
- Creating new tools and skills on demand
"""

import json
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
from pathlib import Path

from app.services.chat import get_chat_service
from app.services.artifacts import get_artifact_service


@dataclass
class SelfImprovementTask:
    """Represents a self-improvement task."""
    task_id: str
    improvement_type: str  # "new_skill", "enhance_skill", "fix_issue", "add_tool"
    description: str
    user_request: str
    status: str = "pending"  # pending, analyzing, implementing, testing, completed, failed
    implementation_plan: str = ""
    code_changes: list[str] = field(default_factory=list)
    test_results: str = ""
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None


class SelfDevelopmentAgent:
    """
    Agent that enables the chatbot to improve itself.
    
    Capabilities:
    - Analyze user requests for new features/skills
    - Generate implementation plans
    - Create new tools and capabilities
    - Update existing functionality
    - Learn from user feedback
    """
    
    name = "self-development-agent"
    
    def __init__(self):
        self.chat_service = get_chat_service()
        self.artifact_service = get_artifact_service()
        self.improvement_history: list[SelfImprovementTask] = []
        self.capabilities_file = Path("backend/app/services/capabilities.json")
        self.load_capabilities()
    
    def load_capabilities(self):
        """Load current capabilities from file."""
        if self.capabilities_file.exists():
            try:
                with open(self.capabilities_file, 'r') as f:
                    self.capabilities = json.load(f)
            except Exception:
                self.capabilities = {
                    "skills": [],
                    "tools": [],
                    "knowledge_areas": [],
                    "improvements": []
                }
        else:
            self.capabilities = {
                "skills": [],
                "tools": [],
                "knowledge_areas": [],
                "improvements": []
            }
    
    def save_capabilities(self):
        """Save capabilities to file."""
        try:
            with open(self.capabilities_file, 'w') as f:
                json.dump(self.capabilities, f, indent=2)
        except Exception as e:
            print(f"Failed to save capabilities: {e}")
    
    def can_self_improve(self, user_message: str) -> bool:
        """Check if user is requesting self-improvement."""
        lower = user_message.lower()
        
        improvement_triggers = [
            "add a new", "create a new", "implement a new",
            "add support for", "add capability", "add skill",
            "learn to", "learn how to",
            "improve your", "enhance your", "upgrade your",
            "add a tool", "create a tool",
            "can you add", "can you learn",
            "new feature", "new functionality",
            "extend your", "expand your",
        ]
        
        return any(trigger in lower for trigger in improvement_triggers)
    
    async def analyze_improvement_request(self, user_message: str) -> dict:
        """Analyze what the user wants the AI to learn/add."""
        analysis_prompt = f"""Analyze this user request for self-improvement:

User Request: "{user_message}"

Determine:
1. What type of improvement is requested?
   - new_skill: Add a completely new skill/capability
   - enhance_skill: Improve an existing skill
   - add_tool: Create a new tool or utility
   - fix_issue: Fix a problem or bug

2. What specifically needs to be implemented?

3. What files would need to be modified or created?

4. What would the implementation involve?

Provide a structured analysis in JSON format with:
- improvement_type
- description
- required_files
- implementation_steps
- complexity (1-10)
- estimated_difficulty (easy/medium/hard)"""

        try:
            response = await self.chat_service.generate(
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "improvement_type": "new_skill",
                    "description": user_message,
                    "required_files": [],
                    "implementation_steps": [user_message],
                    "complexity": 5,
                    "estimated_difficulty": "medium"
                }
        except Exception as e:
            return {
                "improvement_type": "new_skill",
                "description": user_message,
                "error": str(e)
            }
    
    async def create_implementation_plan(self, analysis: dict, user_message: str) -> str:
        """Create a detailed implementation plan."""
        plan_prompt = f"""Create a detailed implementation plan for this self-improvement:

Analysis: {json.dumps(analysis, indent=2)}

User Request: {user_message}

Create a step-by-step implementation plan that includes:
1. What files need to be created/modified
2. What code needs to be written
3. How to integrate the new capability
4. How to test the implementation
5. How to verify it works correctly

Be specific and provide actual code examples where possible."""

        try:
            plan = await self.chat_service.generate(
                messages=[{"role": "user", "content": plan_prompt}]
            )
            return plan
        except Exception as e:
            return f"Failed to create implementation plan: {e}"
    
    async def implement_improvement(self, task: SelfImprovementTask) -> SelfImprovementTask:
        """Execute the self-improvement task."""
        task.status = "analyzing"
        
        try:
            # Step 1: Analyze the request
            analysis = await self.analyze_improvement_request(task.user_request)
            task.implementation_plan = await self.create_implementation_plan(analysis, task.user_request)
            
            # Step 2: Generate the code/files needed
            task.status = "implementing"
            
            implementation_prompt = f"""Implement this self-improvement:

Task: {task.description}
User Request: {task.user_request}

Analysis: {json.dumps(analysis, indent=2)}

Implementation Plan:
{task.implementation_plan}

Generate the actual code that needs to be added/modified.
Provide complete, working code examples.
Include:
- New files to create (with full path and content)
- Existing files to modify (with exact changes)
- Configuration updates needed
- Integration points"""

            implementation = await self.chat_service.generate(
                messages=[{"role": "user", "content": implementation_prompt}]
            )
            
            task.code_changes = [implementation]
            
            # Step 3: Create test/verification instructions
            task.status = "testing"
            
            test_prompt = f"""Create test and verification instructions for this self-improvement:

Task: {task.description}
Implementation:
{implementation}

Provide:
1. How to test the new capability
2. Example usage
3. How to verify it works correctly
4. Any manual steps the user needs to perform"""

            task.test_results = await self.chat_service.generate(
                messages=[{"role": "user", "content": test_prompt}]
            )
            
            # Step 4: Update capabilities
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            
            # Add to capabilities
            if analysis.get("improvement_type") == "new_skill":
                self.capabilities["skills"].append({
                    "name": task.description,
                    "added_at": task.completed_at,
                    "user_request": task.user_request
                })
            elif analysis.get("improvement_type") == "add_tool":
                self.capabilities["tools"].append({
                    "name": task.description,
                    "added_at": task.completed_at,
                    "user_request": task.user_request
                })
            
            self.capabilities["improvements"].append({
                "task_id": task.task_id,
                "type": analysis.get("improvement_type"),
                "description": task.description,
                "completed_at": task.completed_at
            })
            
            self.save_capabilities()
            
            # Add to history
            self.improvement_history.append(task)
            
            return task
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now(UTC).isoformat()
            self.improvement_history.append(task)
            return task
    
    async def learn_from_feedback(self, user_message: str, ai_response: str, feedback: str) -> dict:
        """Learn from user feedback to improve future responses."""
        feedback_prompt = f"""Analyze this user feedback and determine how to improve:

User's Original Message: {user_message}

AI's Response: {ai_response}

User's Feedback: {feedback}

Determine:
1. What was wrong or inadequate about the response?
2. What should have been done differently?
3. What rule, pattern, or preference should be learned?
4. How should future similar requests be handled?

Provide specific, actionable improvements."""

        try:
            learning = await self.chat_service.generate(
                messages=[{"role": "user", "content": feedback_prompt}]
            )
            
            # Store the learning
            learning_record = {
                "type": "feedback_learning",
                "original_request": user_message,
                "original_response": ai_response,
                "feedback": feedback,
                "learning": learning,
                "learned_at": datetime.now(UTC).isoformat()
            }
            
            self.capabilities["improvements"].append(learning_record)
            self.save_capabilities()
            
            return learning_record
        except Exception as e:
            return {"error": str(e)}
    
    def get_improvement_status(self) -> dict:
        """Get current self-improvement status and capabilities."""
        return {
            "total_improvements": len(self.improvement_history),
            "completed_improvements": len([t for t in self.improvement_history if t.status == "completed"]),
            "failed_improvements": len([t for t in self.improvement_history if t.status == "failed"]),
            "capabilities": self.capabilities,
            "recent_improvements": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "status": t.status,
                    "completed_at": t.completed_at
                }
                for t in self.improvement_history[-5:]
            ]
        }


# Singleton instance
_self_development_agent = None


def get_self_development_agent() -> SelfDevelopmentAgent:
    """Get or create the self-development agent singleton."""
    global _self_development_agent
    if _self_development_agent is None:
        _self_development_agent = SelfDevelopmentAgent()
    return _self_development_agent
