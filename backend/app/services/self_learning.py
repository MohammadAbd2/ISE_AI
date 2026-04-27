"""
Self-Learning System for ISE AI

This module implements continuous learning from user interactions:
1. User preference detection
2. Code style adaptation
3. Context-aware responses
4. Multi-session memory
5. Automated skill development
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

class LearningType(str, Enum):
    """Types of learning the system can perform."""
    PREFERENCE = "preference"  # User preferences (naming, structure, etc.)
    CODE_STYLE = "code_style"  # Code style patterns
    WORKFLOW = "workflow"  # Workflow preferences
    LANGUAGE = "language"  # Language/framework preferences
    PATTERN = "pattern"  # Recognized patterns
    CORRECTION = "correction"  # User corrections


@dataclass
class LearningEntry:
    """A single learning entry from user interaction."""
    learning_type: LearningType
    category: str  # e.g., "naming_convention", "file_structure"
    pattern: str  # What to look for
    preference: str  # What the user prefers
    confidence: float = 0.0  # Confidence score (0.0 to 1.0)
    occurrences: int = 1  # How many times observed
    last_seen: Optional[str] = None
    created_at: Optional[str] = None
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "learning_type": self.learning_type.value,
            "category": self.category,
            "pattern": self.pattern,
            "preference": self.preference,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
            "examples": self.examples[:5],  # Keep last 5 examples
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningEntry":
        return cls(
            learning_type=LearningType(data["learning_type"]),
            category=data["category"],
            pattern=data["pattern"],
            preference=data["preference"],
            confidence=data.get("confidence", 0.0),
            occurrences=data.get("occurrences", 1),
            last_seen=data.get("last_seen"),
            created_at=data.get("created_at"),
            examples=data.get("examples", []),
        )


@dataclass
class UserContext:
    """Complete user context including preferences and learned patterns."""
    user_id: str = "default"
    preferences: dict[str, Any] = field(default_factory=dict)
    code_styles: dict[str, Any] = field(default_factory=dict)
    workflows: list[str] = field(default_factory=list)
    learned_patterns: list[LearningEntry] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    total_interactions: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "code_styles": self.code_styles,
            "workflows": self.workflows,
            "learned_patterns": [p.to_dict() for p in self.learned_patterns],
            "corrections": self.corrections,
            "total_interactions": self.total_interactions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserContext":
        return cls(
            user_id=data.get("user_id", "default"),
            preferences=data.get("preferences", {}),
            code_styles=data.get("code_styles", {}),
            workflows=data.get("workflows", []),
            learned_patterns=[
                LearningEntry.from_dict(p) for p in data.get("learned_patterns", [])
            ],
            corrections=data.get("corrections", []),
            total_interactions=data.get("total_interactions", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class PreferenceDetector:
    """Detect user preferences from interactions."""

    # Common preference patterns
    NAMING_PATTERNS = {
        "snake_case": r"\b[a-z]+_[a-z]+\b",
        "camelCase": r"\b[a-z]+[A-Z][a-z]+\b",
        "PascalCase": r"\b[A-Z][a-z]+[A-Z][a-z]+\b",
        "kebab-case": r"\b[a-z]+-[a-z]+\b",
    }

    CODE_STYLE_PATTERNS = {
        "arrow_functions": r"=>\s*{",
        "async_await": r"async\s+\w+\s*\(",
        "try_catch": r"try\s*{",
        "error_handling": r"catch\s*\(|\.catch\(",
        "type_annotations": r":\s*(str|int|bool|list|dict)",
    }

    def detect_preferences(self, user_message: str, context: str = "") -> list[LearningEntry]:
        """Detect preferences from user message and context."""
        preferences = []
        message_lower = user_message.lower()

        # Detect naming preferences
        for style, pattern in self.NAMING_PATTERNS.items():
            if re.search(pattern, user_message):
                preferences.append(LearningEntry(
                    learning_type=LearningType.PREFERENCE,
                    category="naming_convention",
                    pattern=pattern,
                    preference=style,
                    confidence=0.6,
                    examples=[user_message[:100]],
                ))

        # Detect code style preferences
        for style, pattern in self.CODE_STYLE_PATTERNS.items():
            if re.search(pattern, context):
                preferences.append(LearningEntry(
                    learning_type=LearningType.CODE_STYLE,
                    category="code_style",
                    pattern=pattern,
                    preference=style,
                    confidence=0.7,
                    examples=[context[:100]],
                ))

        # Detect explicit preferences
        explicit_patterns = [
            (r"(?:use|prefer|like|want)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:style|approach|method)", "explicit_preference"),
            (r"(?:don't|do not)\s+(?:use|prefer|like)\s+(\w+(?:\s+\w+)?)", "negative_preference"),
            (r"(?:always|never)\s+(\w+(?:\s+\w+)?)", "strong_preference"),
        ]

        for pattern, category in explicit_patterns:
            match = re.search(pattern, message_lower)
            if match:
                preferences.append(LearningEntry(
                    learning_type=LearningType.PREFERENCE,
                    category=category,
                    pattern=pattern,
                    preference=match.group(1),
                    confidence=0.9,
                    examples=[user_message[:100]],
                ))

        return preferences


class ContextAnalyzer:
    """Analyze conversation context for learning opportunities."""

    def analyze_context(self, messages: list[dict]) -> dict[str, Any]:
        """Analyze conversation context for patterns."""
        analysis = {
            "topics": [],
            "technologies": [],
            "complexity": "medium",
            "user_expertise": "intermediate",
        }

        # Extract topics and technologies
        tech_keywords = [
            "react", "python", "javascript", "typescript", "fastapi",
            "node", "express", "django", "flask", "vue", "angular",
            "mongodb", "postgresql", "mysql", "redis", "docker",
        ]

        all_text = " ".join([m.get("content", "") for m in messages]).lower()

        for tech in tech_keywords:
            if tech in all_text:
                analysis["technologies"].append(tech)

        # Determine complexity
        complex_keywords = ["architecture", "design pattern", "microservice", "distributed"]
        simple_keywords = ["hello", "basic", "simple", "tutorial"]

        if any(kw in all_text for kw in complex_keywords):
            analysis["complexity"] = "high"
        elif any(kw in all_text for kw in simple_keywords):
            analysis["complexity"] = "low"

        # Determine user expertise
        if analysis["complexity"] == "high":
            analysis["user_expertise"] = "advanced"
        elif analysis["complexity"] == "low":
            analysis["user_expertise"] = "beginner"

        return analysis


class SelfLearningSystem:
    """
    Main self-learning system that coordinates all learning components.
    
    Capabilities:
    1. Learn from user chats and corrections
    2. Detect and store preferences
    3. Adapt code style to user preferences
    4. Provide context-aware responses
    5. Multi-session memory persistence
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path.cwd() / ".ise_ai_learning"
        
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.preference_detector = PreferenceDetector()
        self.context_analyzer = ContextAnalyzer()
        self.user_context: Optional[UserContext] = None
        
    async def initialize(self, user_id: str = "default"):
        """Initialize the learning system and load user context."""
        self.user_context = await self._load_user_context(user_id)
        if self.user_context is None:
            self.user_context = UserContext(
                user_id=user_id,
                created_at=datetime.now(UTC).isoformat(),
            )

    async def learn_from_interaction(
        self,
        user_message: str,
        assistant_response: str,
        context: str = "",
        session_id: Optional[str] = None,
    ) -> list[LearningEntry]:
        """
        Learn from a single user interaction.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
            context: Additional context (code, files, etc.)
            session_id: Session identifier
            
        Returns:
            List of learning entries created
        """
        if self.user_context is None:
            await self.initialize()

        # Detect preferences
        new_preferences = self.preference_detector.detect_preferences(
            user_message, context
        )

        # Analyze context
        context_analysis = self.context_analyzer.analyze_context([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response},
        ])

        # Update user context
        self.user_context.total_interactions += 1
        self.user_context.updated_at = datetime.now(UTC).isoformat()

        # Merge new preferences
        for pref in new_preferences:
            self._merge_preference(pref)

        # Store context analysis
        if context_analysis["technologies"]:
            self.user_context.preferences["technologies"] = list(
                set(
                    self.user_context.preferences.get("technologies", [])
                    + context_analysis["technologies"]
                )
            )

        # Save user context
        await self._save_user_context()

        return new_preferences

    async def get_personalized_context(self, task: str) -> dict[str, Any]:
        """
        Get personalized context for generating a response.
        
        Args:
            task: The user's task/message
            
        Returns:
            Dictionary with personalized context
        """
        if self.user_context is None:
            await self.initialize()

        context = {
            "user_preferences": self.user_context.preferences,
            "code_styles": self.user_context.code_styles,
            "learned_patterns": [
                p.to_dict() for p in self.user_context.learned_patterns
                if p.confidence > 0.7
            ],
            "recommendations": self._generate_recommendations(task),
        }

        return context

    async def record_response_preference(
        self,
        style: str,
        message_excerpt: str = "",
    ) -> LearningEntry:
        """Store an explicit user preference for how replies should be shaped."""
        if self.user_context is None:
            await self.initialize()

        normalized = style.strip().lower()
        preference_map = {
            "concise": "concise",
            "shorter": "concise",
            "structured": "structured",
            "more structured": "structured",
        }
        stored = preference_map.get(normalized, normalized or "concise")

        entry = LearningEntry(
            learning_type=LearningType.PREFERENCE,
            category="response_style",
            pattern=r"response_style",
            preference=stored,
            confidence=0.95,
            examples=[message_excerpt[:120]] if message_excerpt else [],
        )
        self._merge_preference(entry)
        self.user_context.preferences["response_style"] = stored
        self.user_context.updated_at = datetime.now(UTC).isoformat()
        await self._save_user_context()
        return entry

    def _merge_preference(self, preference: LearningEntry):
        """Merge a new preference into user context."""
        # Check if similar preference exists
        for existing in self.user_context.learned_patterns:
            if (
                existing.category == preference.category
                and existing.pattern == preference.pattern
            ):
                # Update existing
                existing.occurrences += 1
                existing.last_seen = datetime.now(UTC).isoformat()
                existing.confidence = min(1.0, existing.confidence + 0.1)
                if preference.examples:
                    existing.examples.extend(preference.examples)
                return

        # Add new preference
        preference.created_at = datetime.now(UTC).isoformat()
        preference.last_seen = datetime.now(UTC).isoformat()
        self.user_context.learned_patterns.append(preference)

    def _generate_recommendations(self, task: str) -> list[str]:
        """Generate recommendations based on learned preferences."""
        recommendations = []

        response_style = self.user_context.preferences.get("response_style")
        if response_style == "concise":
            recommendations.append(
                "Keep responses concise: lead with the answer, avoid filler, and prefer short high-signal paragraphs."
            )
        elif response_style == "structured":
            recommendations.append(
                "Use stronger structure: short lead line, clear emphasis, and compact bullets when they help."
            )

        # Check for naming preferences
        naming_prefs = [
            p for p in self.user_context.learned_patterns
            if p.category == "naming_convention" and p.confidence > 0.7
        ]
        if naming_prefs:
            top_pref = max(naming_prefs, key=lambda p: p.confidence)
            recommendations.append(
                f"Use {top_pref.preference} for naming conventions"
            )

        # Check for code style preferences
        style_prefs = [
            p for p in self.user_context.learned_patterns
            if p.category == "code_style" and p.confidence > 0.7
        ]
        if style_prefs:
            styles = [p.preference for p in style_prefs]
            recommendations.append(
                f"Apply code styles: {', '.join(styles)}"
            )

        return recommendations

    async def _load_user_context(self, user_id: str) -> Optional[UserContext]:
        """Load user context from storage."""
        context_file = self.storage_path / f"{user_id}.json"
        if not context_file.exists():
            return None

        try:
            content = context_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return UserContext.from_dict(data)
        except Exception:
            return None

    async def _save_user_context(self):
        """Save user context to storage."""
        if self.user_context is None:
            return

        context_file = self.storage_path / f"{self.user_context.user_id}.json"
        try:
            payload = json.dumps(self.user_context.to_dict(), indent=2)
            context_file.write_text(payload, encoding="utf-8")
        except Exception as e:
            print(f"Error saving user context: {e}")

    async def get_learning_stats(self) -> dict[str, Any]:
        """Get learning statistics for dashboard."""
        if self.user_context is None:
            await self.initialize()

        return {
            "total_interactions": self.user_context.total_interactions,
            "preferences_learned": len(self.user_context.learned_patterns),
            "code_styles": len(self.user_context.code_styles),
            "technologies": self.user_context.preferences.get("technologies", []),
            "top_patterns": sorted(
                self.user_context.learned_patterns,
                key=lambda p: p.confidence,
                reverse=True,
            )[:5],
        }


# Singleton instance
_learning_system: Optional[SelfLearningSystem] = None


def get_learning_system() -> SelfLearningSystem:
    """Get or create learning system instance."""
    global _learning_system
    if _learning_system is None:
        _learning_system = SelfLearningSystem()
    return _learning_system
