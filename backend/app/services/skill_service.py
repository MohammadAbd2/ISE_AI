"""
Skill Service for managing complex agentic workflows.
Allows the AI to use pre-defined strategies and sub-prompts for specific tasks.
"""

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.core.config import settings


@dataclass
class Skill:
    """Represents a pre-defined agent skill/workflow."""
    name: str
    description: str
    prompt: str
    tools: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillService:
    """
    Manages agent skills and workflows.
    Loads skills from .codex/skills/ and provides bundled skills.
    """

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            self.project_root = Path(settings.backend_root).parent.parent
        else:
            self.project_root = project_root
            
        self.skills_dir = self.project_root / ".codex" / "skills"
        self.skills: Dict[str, Skill] = {}
        self._load_skills()
        self._register_bundled_skills()

    def _load_skills(self):
        """Load skills from .codex/skills/ directory."""
        if not self.skills_dir.exists():
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    skill = self._parse_skill_md(content)
                    if skill:
                        self.skills[skill.name] = skill
                except Exception:
                    continue

    def _parse_skill_md(self, content: str) -> Optional[Skill]:
        """Parse a SKILL.md file with frontmatter."""
        import re
        
        # Simple frontmatter parsing
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter_raw = match.group(1)
        body = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
            return Skill(
                name=frontmatter.get("name", "unknown"),
                description=frontmatter.get("description", ""),
                prompt=body.strip(),
                tools=frontmatter.get("tools", []),
                version=frontmatter.get("version", "1.0.0"),
                metadata=frontmatter,
            )
        except Exception:
            return None

    def _register_bundled_skills(self):
        """Register skills that are built into the application."""
        # 'remember' skill (inspired by Claude Code)
        self.skills["remember"] = Skill(
            name="remember",
            description="Review and organize project memory and conventions.",
            prompt="""# Memory Review & Organization

Your goal is to review the project's memory landscape and propose updates to conventions.

STEPS:
1. Read CLAUDE.md and any other documentation files.
2. Analyze recent changes and developer preferences.
3. Identify outdated instructions or conflicting conventions.
4. Propose clear, actionable updates to CLAUDE.md.

RULES:
- Be concise.
- Focus on patterns and standards.
- Do not modify files without explicit confirmation.
""",
            tools=["read_file", "write_file", "glob_search"]
        )

        # 'verify' skill
        self.skills["verify"] = Skill(
            name="verify",
            description="Run comprehensive verification on recent changes.",
            prompt="""# Verification Workflow

Your goal is to ensure the codebase remains stable and correct after changes.

STEPS:
1. Identify all modified files.
2. Find associated test files.
3. Run relevant tests and linters.
4. Fix any discovered issues iteratively.
5. Report final status.
""",
            tools=["execute_command", "glob_search", "lsp_index"]
        )

        # 'debug' skill
        self.skills["debug"] = Skill(
            name="debug",
            description="Systematically diagnose and fix a reported bug.",
            prompt="""# Debugging Workflow

Your goal is to find the root cause of an issue and implement a fix.

STEPS:
1. Reproduce the bug with a test case.
2. Use LSP and grep to trace the execution flow.
3. Inspect variable states and logs.
4. Implement the fix.
5. Verify the fix with the reproduction test.
""",
            tools=["execute_command", "lsp_definition", "lsp_hover", "search_in_files"]
        )

        # 'self-improve' skill
        self.skills["self-improve"] = Skill(
            name="self-improve",
            description="The agent analyzes its own gaps and implements improvements to its tools or logic.",
            prompt="""# Self-Improvement Workflow

Your goal is to enhance your own capabilities by adding new tools or fixing logic gaps.

STEPS:
1. Identify a missing tool or a limitation in your current execution.
2. Search for relevant implementation patterns in the codebase.
3. Draft the new tool implementation in `backend/app/services/tool_executor.py`.
4. Register the tool in `backend/app/services/dynamic_tool_registry.py`.
5. Verify the new capability with a test script.

RULES:
- Be extremely careful when modifying core agent files.
- Always create a backup before writing.
- Use `ask_permission` before deploying a major change to yourself.
""",
            tools=["read_file", "write_file", "execute_command", "system_doctor"]
        )

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all available skills."""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
            }
            for skill in self.skills.values()
        ]


# Global instance
_skill_service: Optional[SkillService] = None


def get_skill_service(project_root: Optional[Path] = None) -> SkillService:
    """Get or create skill service instance."""
    global _skill_service
    if _skill_service is None:
        _skill_service = SkillService(project_root)
    return _skill_service
