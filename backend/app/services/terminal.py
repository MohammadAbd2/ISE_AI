"""
Terminal Integration and Live Debug Support

Provides:
- Run commands from chat
- Parse error output
- Auto-fix from errors
- Live terminal integration
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional


@dataclass
class TerminalOutput:
    """Output from a terminal command."""
    command: str
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    executed_at: str = ""
    duration_ms: int = 0
    error_analysis: Optional[dict] = None
    suggested_fix: Optional[str] = None


@dataclass
class ErrorAnalysis:
    """Analysis of an error from terminal output."""
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    stack_trace: list[str] = field(default_factory=list)
    suggested_fix: str = ""
    confidence: float = 0.0


class TerminalIntegration:
    """
    Terminal integration for running commands and analyzing errors.
    
    Similar to Cursor's and Copilot's terminal integration.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.allowed_commands = {
            "python", "python3", "node", "npm", "yarn", "pnpm",
            "pip", "pip3", "git", "pytest", "py.test", "cargo",
            "make", "cmake", "gcc", "g++", "clang", "rustc",
            "docker", "docker-compose", "kubectl", "terraform",
            "ls", "dir", "cd", "pwd", "cat", "head", "tail",
            "grep", "find", "wc", "sort", "uniq", "awk", "sed",
            "curl", "wget", "ssh", "scp", "rsync",
            "chmod", "chown", "mkdir", "rmdir", "cp", "mv", "rm",
            "echo", "env", "which", "where", "whoami",
        }
        
        # Dangerous commands that are blocked
        self.blocked_patterns = [
            r"rm\s+-rf\s+/",
            r"rm\s+-rf\s+~",
            r"sudo\s+rm",
            r">\s*/dev/sd",
            r">\s*/etc/",
            r"dd\s+",
            r"mkfs",
            r"chmod\s+777\s+/",
        ]
    
    async def run_command(self, command: str, timeout: int = 120) -> TerminalOutput:
        """Run a command and capture output."""
        start_time = datetime.now(UTC)
        
        # Security checks
        if not self._is_command_allowed(command):
            return TerminalOutput(
                command=command,
                stderr=f"Command not allowed: {command.split()[0] if command.split() else 'empty'}",
                return_code=-1,
                executed_at=start_time.isoformat(),
            )
        
        if self._is_command_dangerous(command):
            return TerminalOutput(
                command=command,
                stderr="Dangerous command blocked",
                return_code=-1,
                executed_at=start_time.isoformat(),
            )
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            end_time = datetime.now(UTC)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            output = TerminalOutput(
                command=command,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                return_code=process.returncode,
                executed_at=start_time.isoformat(),
                duration_ms=duration_ms,
            )
            
            # Analyze errors if any
            if process.returncode != 0 or stderr:
                output.error_analysis = self._analyze_error(output)
                output.suggested_fix = self._generate_fix(output)
            
            return output
            
        except asyncio.TimeoutError:
            return TerminalOutput(
                command=command,
                stderr=f"Command timed out after {timeout}s",
                return_code=-1,
                executed_at=start_time.isoformat(),
                duration_ms=timeout * 1000,
            )
        except Exception as e:
            return TerminalOutput(
                command=command,
                stderr=f"Error executing command: {str(e)}",
                return_code=-1,
                executed_at=start_time.isoformat(),
            )
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is in allowed list."""
        base_cmd = command.split()[0] if command.split() else ""
        return base_cmd in self.allowed_commands
    
    def _is_command_dangerous(self, command: str) -> bool:
        """Check if command matches dangerous patterns."""
        for pattern in self.blocked_patterns:
            if re.search(pattern, command):
                return True
        return False
    
    def _analyze_error(self, output: TerminalOutput) -> dict:
        """Analyze error output to extract useful information."""
        error_text = output.stderr or output.stdout
        
        analysis = {
            "error_type": "unknown",
            "error_message": "",
            "file_path": None,
            "line_number": None,
            "suggestions": [],
        }
        
        # Python errors
        python_error = self._parse_python_error(error_text)
        if python_error:
            return python_error
        
        # Node.js errors
        node_error = self._parse_node_error(error_text)
        if node_error:
            return node_error
        
        # TypeScript errors
        ts_error = self._parse_typescript_error(error_text)
        if ts_error:
            return ts_error
        
        # Generic error parsing
        analysis["error_message"] = error_text.split("\n")[0][:200]
        
        return analysis
    
    def _parse_python_error(self, error_text: str) -> Optional[dict]:
        """Parse Python traceback."""
        # Match Python traceback pattern
        traceback_pattern = r'Traceback \(most recent call last\):.*?File "([^"]+)", line (\d+)'
        match = re.search(traceback_pattern, error_text, re.DOTALL)
        
        if match:
            return {
                "error_type": "python_exception",
                "error_message": error_text.split("\n")[-1][:200],
                "file_path": match.group(1),
                "line_number": int(match.group(2)),
                "suggestions": [
                    "Check the error message for the exception type",
                    "Review the code at the indicated line",
                    "Look for common issues: NoneType, KeyError, IndexError",
                ],
            }
        
        # Match syntax error
        syntax_pattern = r'File "([^"]+)", line (\d+)\n\s+\^\nSyntaxError: (.+)'
        match = re.search(syntax_pattern, error_text)
        
        if match:
            return {
                "error_type": "syntax_error",
                "error_message": match.group(3),
                "file_path": match.group(1),
                "line_number": int(match.group(2)),
                "suggestions": [
                    "Check for missing colons, parentheses, or quotes",
                    "Verify proper indentation",
                    "Look for typos in keywords",
                ],
            }
        
        return None
    
    def _parse_node_error(self, error_text: str) -> Optional[dict]:
        """Parse Node.js error output."""
        # Match Node.js stack trace
        stack_pattern = r'at\s+(?:.+?\s+)?\(([^:]+):(\d+):(\d+)\)'
        match = re.search(stack_pattern, error_text)
        
        if match:
            return {
                "error_type": "nodejs_exception",
                "error_message": error_text.split("\n")[0][:200],
                "file_path": match.group(1),
                "line_number": int(match.group(1)),
                "column": int(match.group(2)),
                "suggestions": [
                    "Check for undefined variables",
                    "Verify async/await usage",
                    "Look for type errors",
                ],
            }
        
        return None
    
    def _parse_typescript_error(self, error_text: str) -> Optional[dict]:
        """Parse TypeScript compiler errors."""
        # Match TS error pattern
        ts_pattern = r'([^:]+):(\d+):(\d+)\s+-\s+error\s+TS(\d+):\s+(.+)'
        match = re.search(ts_pattern, error_text)
        
        if match:
            error_code = match.group(4)
            error_message = match.group(5)
            
            suggestions = self._get_ts_suggestions(error_code)
            
            return {
                "error_type": "typescript_error",
                "error_message": f"TS{error_code}: {error_message}",
                "file_path": match.group(1),
                "line_number": int(match.group(2)),
                "column": int(match.group(3)),
                "suggestions": suggestions,
            }
        
        return None
    
    def _get_ts_suggestions(self, error_code: str) -> list[str]:
        """Get suggestions for common TypeScript errors."""
        suggestions_map = {
            "2304": ["Cannot find name - check if variable is declared or imported"],
            "2307": ["Cannot find module - check if package is installed"],
            "2339": ["Property does not exist - check type definition"],
            "2345": ["Argument type mismatch - check function signature"],
            "2531": ["Object is possibly null - add null check"],
            "2532": ["Object is possibly undefined - add undefined check"],
            "7006": ["Parameter implicitly has any type - add type annotation"],
            "7053": ["Element implicitly has any type - add index signature"],
        }
        return suggestions_map.get(error_code, ["Check TypeScript documentation for this error"])
    
    def _generate_fix(self, output: TerminalOutput) -> Optional[str]:
        """Generate a suggested fix based on error analysis."""
        if not output.error_analysis:
            return None
        
        analysis = output.error_analysis
        
        # Python-specific fixes
        if analysis.get("error_type") == "syntax_error":
            return "Fix the syntax error at the indicated line. Common fixes: add missing colon, close parentheses, or fix indentation."
        
        if "ModuleNotFoundError" in analysis.get("error_message", ""):
            module = re.search(r"No module named '([^']+)'", analysis.get("error_message", ""))
            if module:
                return f"Install the missing package: `pip install {module.group(1)}`"
        
        if "ImportError" in analysis.get("error_message", ""):
            return "Check if the module is installed and the import path is correct."
        
        # TypeScript-specific fixes
        if analysis.get("error_type") == "typescript_error":
            return "Fix the TypeScript type error. Add proper type annotations or fix the type mismatch."
        
        # Node.js-specific fixes
        if analysis.get("error_type") == "nodejs_exception":
            if "Cannot find module" in analysis.get("error_message", ""):
                return "Install missing dependencies: `npm install`"
        
        return None
    
    def get_run_command(self, file_path: str) -> str:
        """Get the appropriate run command for a file."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        commands = {
            ".py": f"python {file_path}",
            ".js": f"node {file_path}",
            ".ts": f"npx ts-node {file_path}",
            ".jsx": f"npx babel-node {file_path}",
            ".tsx": f"npx ts-node {file_path}",
            ".sh": f"bash {file_path}",
            ".rb": f"ruby {file_path}",
            ".go": f"go run {file_path}",
            ".rs": f"cargo run",
        }
        
        return commands.get(suffix, f"# Unknown file type: {suffix}")
    
    def get_test_command(self, framework: str = "auto") -> str:
        """Get the appropriate test command."""
        commands = {
            "pytest": "pytest -v",
            "unittest": "python -m unittest discover -v",
            "jest": "npx jest",
            "mocha": "npx mocha",
            "vitest": "npx vitest",
            "cargo": "cargo test",
            "go": "go test ./...",
            "auto": "pytest -v",  # Default
        }
        
        return commands.get(framework, commands["auto"])


# Global instance
_terminal: Optional[TerminalIntegration] = None


def get_terminal_integration(project_root: Optional[Path] = None) -> TerminalIntegration:
    """Get or create terminal integration instance."""
    global _terminal
    if _terminal is None:
        if project_root is None:
            project_root = Path.cwd()
        _terminal = TerminalIntegration(project_root)
    return _terminal
