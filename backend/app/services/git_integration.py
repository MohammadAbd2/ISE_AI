"""
Git Integration Service

Provides:
- Commit message generation
- PR description writing
- Code review assistance
- Change analysis
- Branch management
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str = ""
    staged_changes: list[str] = field(default_factory=list)
    unstaged_changes: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    is_clean: bool = True


@dataclass
class CommitSuggestion:
    """Suggested commit with message and changes."""
    message: str
    description: str = ""
    files: list[str] = field(default_factory=list)
    type: str = "feat"  # feat, fix, docs, style, refactor, test, chore
    scope: str = ""
    is_breaking: bool = False


class GitIntegration:
    """
    Git integration for commit/PR assistance.
    
    Similar to GitHub Copilot's Git features.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.git_root = self._find_git_root()
    
    def _find_git_root(self) -> Optional[Path]:
        """Find the git repository root."""
        current = self.project_root
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None
    
    def is_git_repo(self) -> bool:
        """Check if project is a git repository."""
        return self.git_root is not None
    
    async def get_status(self) -> GitStatus:
        """Get git repository status."""
        if not self.is_git_repo():
            return GitStatus(is_clean=True)
        
        status = GitStatus()
        
        try:
            # Get current branch
            result = await self._run_git_command("git branch --show-current")
            status.branch = result.stdout.strip()
            
            # Get status
            result = await self._run_git_command("git status --porcelain")
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            
            for line in lines:
                if not line:
                    continue
                status_code = line[:2]
                file_path = line[3:]
                
                if status_code.startswith("A") or status_code.startswith("M"):
                    if status_code[1] == " ":
                        status.staged_changes.append(file_path)
                    else:
                        status.unstaged_changes.append(file_path)
                elif status_code.startswith("??"):
                    status.untracked_files.append(file_path)
            
            # Get ahead/behind
            result = await self._run_git_command("git rev-list --left-right --count HEAD...@{upstream}")
            if result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    status.ahead = int(parts[0])
                    status.behind = int(parts[1])
            
            status.is_clean = (
                len(status.staged_changes) == 0 and
                len(status.unstaged_changes) == 0 and
                len(status.untracked_files) == 0
            )
            
        except Exception:
            pass
        
        return status
    
    async def generate_commit_message(self, changes: Optional[list[str]] = None) -> CommitSuggestion:
        """
        Generate a commit message based on changes.
        
        Analyzes diffs to suggest conventional commit format.
        """
        if not self.is_git_repo():
            return CommitSuggestion(message="Initial commit")
        
        # Get diff
        diff = await self._get_staged_diff()
        
        # Analyze changes
        suggestion = self._analyze_changes_for_commit(diff)
        
        return suggestion
    
    def _analyze_changes_for_commit(self, diff: str) -> CommitSuggestion:
        """Analyze diff to suggest commit message."""
        # Detect change type
        has_additions = "+" in diff and not diff.count("+") == diff.count("+++")
        has_deletions = "-" in diff and not diff.count("-") == diff.count("---")
        has_docs = any(word in diff.lower() for word in ["readme", "doc", "comment", "help"])
        has_tests = any(word in diff.lower() for word in ["test", "spec", "fixture"])
        has_fix = any(word in diff.lower() for word in ["fix", "bug", "error", "issue", "crash"])
        
        # Determine commit type
        if has_fix:
            commit_type = "fix"
        elif has_tests:
            commit_type = "test"
        elif has_docs:
            commit_type = "docs"
        elif has_additions and not has_deletions:
            commit_type = "feat"
        elif has_deletions and not has_additions:
            commit_type = "refactor"
        else:
            commit_type = "feat"
        
        # Generate message
        messages = {
            "feat": "Add new feature",
            "fix": "Fix bug",
            "docs": "Update documentation",
            "test": "Add tests",
            "refactor": "Refactor code",
            "style": "Format code",
            "chore": "Update dependencies",
        }
        
        return CommitSuggestion(
            message=f"{commit_type}: {messages.get(commit_type, 'Update code')}",
            description="Auto-generated commit message based on changes",
            type=commit_type,
        )
    
    async def _get_staged_diff(self) -> str:
        """Get diff of staged changes."""
        result = await self._run_git_command("git diff --cached")
        return result.stdout or ""
    
    async def _run_git_command(self, command: str) -> asyncio.subprocess.Process:
        """Run a git command."""
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(self.git_root or self.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        process.stdout = stdout.decode("utf-8", errors="ignore")
        process.stderr = stderr.decode("utf-8", errors="ignore")
        process.returncode = process.returncode
        return process
    
    async def generate_pr_description(
        self,
        title: str = "",
        branch_from: str = "",
        branch_to: str = "main"
    ) -> str:
        """
        Generate a PR description.
        
        Includes:
        - Summary of changes
        - Type of change
        - Checklist
        - Related issues
        """
        # Get diff between branches
        if branch_from and branch_to:
            diff = await self._get_branch_diff(branch_from, branch_to)
        else:
            diff = await self._get_staged_diff()
        
        # Analyze changes
        analysis = self._analyze_changes_for_pr(diff)
        
        # Build PR description
        description = f"""# {title or "Pull Request"}

## 📝 Summary
{analysis['summary']}

## 🔄 Type of Change
- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] 🧪 Tests
- [ ] 📚 Documentation
- [ ] ⚡ Performance improvement
- [ ] 🔧 Refactoring

## 📁 Files Changed
{analysis['files_summary']}

## ✅ Checklist
- [ ] Code follows project guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated

## 📌 Related Issues
{analysis['related_issues']}

---
*Generated by ISE AI Git Integration*
"""
        
        return description
    
    def _analyze_changes_for_pr(self, diff: str) -> dict:
        """Analyze changes for PR description."""
        lines = diff.split("\n")
        
        added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
        deleted = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
        
        files_changed = len(set(
            re.search(r"\+\+\+ b/(.+)", line).group(1)
            for line in lines
            if line.startswith("+++") and re.search(r"\+\+\+ b/(.+)", line)
        ))
        
        # Detect change types
        has_features = any(word in diff.lower() for word in ["add", "create", "new", "implement"])
        has_fixes = any(word in diff.lower() for word in ["fix", "bug", "error", "issue"])
        has_tests = any(word in diff.lower() for word in ["test", "spec", "assert"])
        
        summary_parts = []
        if has_features:
            summary_parts.append("Added new functionality")
        if has_fixes:
            summary_parts.append("Fixed bugs")
        if has_tests:
            summary_parts.append("Added tests")
        
        summary = " and ".join(summary_parts) if summary_parts else "Code changes"
        
        return {
            "summary": f"{summary}. Changed {files_changed} file(s), +{added}/-{deleted} lines.",
            "files_summary": f"{files_changed} file(s) modified",
            "related_issues": "Fixes #ISSUE_NUMBER",
        }
    
    async def _get_branch_diff(self, branch_from: str, branch_to: str) -> str:
        """Get diff between two branches."""
        command = f"git diff {branch_to}..{branch_from}"
        result = await self._run_git_command(command)
        return result.stdout or ""
    
    async def get_recent_commits(self, count: int = 5) -> list[str]:
        """Get recent commit messages."""
        if not self.is_git_repo():
            return []
        
        command = f"git log -{count} --oneline"
        result = await self._run_git_command(command)
        
        if result.stdout:
            return result.stdout.strip().split("\n")
        return []
    
    async def stage_files(self, files: list[str]) -> bool:
        """Stage files for commit."""
        if not files or not self.is_git_repo():
            return False
        
        command = "git add " + " ".join(files)
        result = await self._run_git_command(command)
        return result.returncode == 0
    
    async def commit(self, message: str) -> bool:
        """Create a commit."""
        if not self.is_git_repo():
            return False
        
        command = f'git commit -m "{message}"'
        result = await self._run_git_command(command)
        return result.returncode == 0


# Global instance
_git: Optional[GitIntegration] = None


def get_git_integration(project_root: Optional[Path] = None) -> Optional[GitIntegration]:
    """Get or create git integration instance."""
    global _git
    if _git is None:
        if project_root is None:
            project_root = Path.cwd()
        _git = GitIntegration(project_root)
    return _git
