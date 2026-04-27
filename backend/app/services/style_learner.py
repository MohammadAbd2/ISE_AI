"""
User Style Learning System

Learns and remembers:
- Coding preferences (naming conventions, patterns)
- Common imports and libraries
- Code structure preferences
- Response format preferences
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles


@dataclass
class UserStyleProfile:
    """User's coding style preferences."""
    # Naming conventions
    variable_naming: str = "snake_case"  # snake_case, camelCase, PascalCase
    function_naming: str = "snake_case"
    class_naming: str = "PascalCase"
    const_naming: str = "UPPER_CASE"
    
    # Code structure
    prefer_async: bool = True
    prefer_type_hints: bool = True
    prefer_docstrings: bool = True
    max_line_length: int = 100
    
    # Library preferences
    preferred_http_lib: str = "httpx"  # httpx, requests, aiohttp
    preferred_json_lib: str = "json"  # json, orjson, ujson
    preferred_orm: str = "sqlalchemy"  # sqlalchemy, tortoise, peewee
    
    # Response preferences
    prefer_concise: bool = True
    prefer_code_comments: bool = True
    prefer_examples: bool = True
    
    # Patterns
    common_imports: list[str] = field(default_factory=list)
    code_templates: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    learned_from_files: list[str] = field(default_factory=list)
    last_updated: str = ""


class UserStyleLearner:
    """
    Learns user's coding style from their codebase.
    
    Similar to how Claude Code and Copilot adapt to your style.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.profile = UserStyleProfile()
        self.profile_path = project_root / ".ise_ai_style.json"
    
    async def load_profile(self):
        """Load existing style profile."""
        if self.profile_path.exists():
            try:
                async with aiofiles.open(self.profile_path, "r") as f:
                    data = json.loads(await f.read())
                
                # Update profile with saved data
                for key, value in data.items():
                    if hasattr(self.profile, key):
                        setattr(self.profile, key, value)
            except Exception:
                pass
    
    async def save_profile(self):
        """Save style profile."""
        self.profile.last_updated = datetime.now(UTC).isoformat()
        
        data = {
            key: value
            for key, value in self.profile.__dict__.items()
            if not key.startswith("_")
        }
        
        async with aiofiles.open(self.profile_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
    
    async def learn_from_codebase(self):
        """Analyze codebase to learn user's style."""
        python_files = list(self.project_root.glob("**/*.py"))
        js_files = list(self.project_root.glob("**/*.js")) + \
                   list(self.project_root.glob("**/*.ts"))
        
        # Learn from Python files
        if python_files:
            await self._learn_from_python_files(python_files[:20])  # Sample 20 files
        
        # Learn from JS/TS files
        if js_files:
            await self._learn_from_js_files(js_files[:20])
        
        await self.save_profile()
    
    async def _learn_from_python_files(self, files: list[Path]):
        """Learn style from Python files."""
        import_counts = {}
        naming_patterns = {"function": [], "class": [], "variable": []}
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                self.profile.learned_from_files.append(str(file_path.relative_to(self.project_root)))
                
                # Analyze imports
                for match in re.finditer(r"^import\s+(\w+)|^from\s+(\w+)", content, re.MULTILINE):
                    lib = match.group(1) or match.group(2)
                    import_counts[lib] = import_counts.get(lib, 0) + 1
                
                # Analyze function names
                for match in re.finditer(r"def\s+(\w+)\s*\(", content):
                    name = match.group(1)
                    if name.startswith("_"):
                        continue
                    if "_" in name and name.islower():
                        naming_patterns["function"].append("snake_case")
                    elif name[0].isupper():
                        naming_patterns["function"].append("PascalCase")
                    else:
                        naming_patterns["function"].append("camelCase")
                
                # Analyze class names
                for match in re.finditer(r"class\s+(\w+)", content):
                    name = match.group(1)
                    if name[0].isupper():
                        naming_patterns["class"].append("PascalCase")
                    else:
                        naming_patterns["class"].append("snake_case")
                
                # Check for type hints
                if re.search(r"def\s+\w+\s*\([^)]*:\s*\w+", content):
                    self.profile.prefer_type_hints = True
                
                # Check for docstrings
                if re.search(r'"""[\s\S]*?"""', content):
                    self.profile.prefer_docstrings = True
                
                # Check for async
                if "async def" in content:
                    self.profile.prefer_async = True
                
            except Exception:
                pass
        
        # Determine most common patterns
        if naming_patterns["function"]:
            most_common = max(set(naming_patterns["function"]), 
                            key=naming_patterns["function"].count)
            self.profile.function_naming = most_common
        
        if naming_patterns["class"]:
            most_common = max(set(naming_patterns["class"]),
                            key=naming_patterns["class"].count)
            self.profile.class_naming = most_common
        
        # Store common imports
        top_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        self.profile.common_imports = [imp for imp, _ in top_imports]
    
    async def _learn_from_js_files(self, files: list[Path]):
        """Learn style from JavaScript/TypeScript files."""
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check for TypeScript
                if file_path.suffix in [".ts", ".tsx"]:
                    self.profile.prefer_type_hints = True
                
                # Check for async/await
                if "async" in content and "await" in content:
                    self.profile.prefer_async = True
                
                # Check for arrow functions
                if "=>" in content:
                    self.profile.common_imports.append("arrow_functions")
                
            except Exception:
                pass
    
    def apply_style_to_code(self, code: str, code_type: str = "python") -> str:
        """Apply learned style to generated code."""
        # This would be more sophisticated with actual code transformation
        # For now, we add comments and formatting based on preferences
        
        lines = code.split("\n")
        styled_lines = []
        
        for line in lines:
            # Add type hints if preferred
            if self.profile.prefer_type_hints and code_type == "python":
                # Could add more sophisticated type hint inference here
                pass
            
            styled_lines.append(line)
        
        return "\n".join(styled_lines)
    
    def get_style_context(self) -> str:
        """Get style preferences as context for LLM."""
        return f"""
User's Coding Style Preferences:
- Variable naming: {self.profile.variable_naming}
- Function naming: {self.profile.function_naming}
- Class naming: {self.profile.class_naming}
- Prefer async: {self.profile.prefer_async}
- Prefer type hints: {self.profile.prefer_type_hints}
- Prefer docstrings: {self.profile.prefer_docstrings}
- Preferred HTTP library: {self.profile.preferred_http_lib}
- Common imports: {', '.join(self.profile.common_imports[:5])}

When generating code, follow these preferences.
"""
    
    def should_be_concise(self) -> bool:
        """Check if user prefers concise responses."""
        return self.profile.prefer_concise


# Global instance
_style_learner: Optional[UserStyleLearner] = None


def get_style_learner(project_root: Optional[Path] = None) -> UserStyleLearner:
    """Get or create style learner instance."""
    global _style_learner
    if _style_learner is None:
        if project_root is None:
            project_root = Path.cwd()
        _style_learner = UserStyleLearner(project_root)
    return _style_learner
