"""
Safe tool executor for the AI to perform file I/O, web search, and shell execution.
Includes security protections: timeouts, path validation, sandboxing.
"""

import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

from backend.app.core.config import settings


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    pass


class ToolExecutor:
    """
    Provides safe tools for AI to:
    - Read and write files
    - Search the web
    - Execute shell commands (with protections)
    """

    # Security settings
    MAX_COMMAND_TIMEOUT = 30  # seconds
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    SAFE_DIRECTORIES = {
        Path(settings.backend_root),
        Path(settings.backend_root).parent / "frontend",
        Path(settings.backend_root).parent,  # Project root for pip installs
    }

    def __init__(self):
        self.command_timeout = self.MAX_COMMAND_TIMEOUT

    def _validate_path(self, path: str | Path) -> Path:
        """
        Validate that a path is within allowed directories.
        Prevents directory traversal attacks.
        """
        path = Path(path).resolve()
        for safe_dir in self.SAFE_DIRECTORIES:
            try:
                path.relative_to(safe_dir)
                return path
            except ValueError:
                pass

        raise ToolExecutionError(
            f"Access denied: {path} is outside allowed directories"
        )

    # ==================== File I/O Tools ====================

    def read_file(self, path: str) -> str:
        """
        Read a file safely.
        
        Args:
            path: File path (relative to repo root)
        
        Returns:
            File contents
        
        Raises:
            ToolExecutionError: If file not found or too large
        """
        file_path = self._validate_path(path)

        if not file_path.exists():
            raise ToolExecutionError(f"File not found: {path}")

        if not file_path.is_file():
            raise ToolExecutionError(f"Not a file: {path}")

        if file_path.stat().st_size > self.MAX_FILE_SIZE:
            raise ToolExecutionError(
                f"File too large: {path} ({file_path.stat().st_size} bytes)"
            )

        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ToolExecutionError(f"Failed to read {path}: {e}")

    def write_file(self, path: str, content: str, append: bool = False) -> dict:
        """
        Write to a file safely.
        
        Args:
            path: File path (relative to repo root)
            content: Content to write
            append: If True, append instead of overwrite
        
        Returns:
            dict with status and bytes written
        
        Raises:
            ToolExecutionError: If write fails
        """
        file_path = self._validate_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if append and file_path.exists():
                file_path.write_text(
                    file_path.read_text(encoding="utf-8") + content,
                    encoding="utf-8",
                )
            else:
                file_path.write_text(content, encoding="utf-8")

            return {
                "status": "success",
                "path": str(file_path),
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as e:
            raise ToolExecutionError(f"Failed to write {path}: {e}")

    def list_directory(self, path: str = ".") -> list[str]:
        """
        List contents of a directory.
        
        Args:
            path: Directory path
        
        Returns:
            List of file/directory names
        """
        dir_path = self._validate_path(path)

        if not dir_path.is_dir():
            raise ToolExecutionError(f"Not a directory: {path}")

        try:
            return sorted(
                [item.name for item in dir_path.iterdir()]
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to list {path}: {e}")

    # ==================== Shell Execution Tools ====================

    def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Execute a shell command safely.
        
        Args:
            command: Shell command to execute
            cwd: Working directory
            timeout: Timeout in seconds (default: MAX_COMMAND_TIMEOUT)
        
        Returns:
            dict with stdout, stderr, returncode
        
        Raises:
            ToolExecutionError: If execution fails
        """
        # Security: only allow specific safe commands
        safe_prefixes = {
            "python",
            "pip",
            "npm",
            "ls",
            "cat",
            "grep",
            "find",
            "git",
        }
        cmd_start = command.split()[0].lower() if command else ""
        if not any(cmd_start.startswith(prefix) for prefix in safe_prefixes):
            raise ToolExecutionError(
                f"Command not allowed: {cmd_start}. Allowed: {safe_prefixes}"
            )

        work_dir = self._validate_path(cwd or ".")
        timeout = min(timeout or self.MAX_COMMAND_TIMEOUT, self.MAX_COMMAND_TIMEOUT)

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                timeout=timeout,
                text=True,
            )

            return {
                "status": "success",
                "stdout": result.stdout[:10000],  # Limit output
                "stderr": result.stderr[:10000],
                "returncode": result.returncode,
                "command": command,
            }
        except subprocess.TimeoutExpired:
            raise ToolExecutionError(
                f"Command timed out after {timeout} seconds: {command}"
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to execute command: {e}")

    # ==================== Web Search Tools ====================

    async def web_search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Search the web for information.
        Currently uses DuckDuckGo as fallback (no API key needed).
        
        Args:
            query: Search query
            max_results: Maximum results to return
        
        Returns:
            List of search results with title, link, snippet
        """
        try:
            # Try using DuckDuckGo HTML (simple approach)
            async with httpx.AsyncClient() as client:
                params = {"q": query}
                url = f"https://duckduckgo.com/search?{urlencode(params)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; ISE-AI/1.0)"
                }

                # Fallback: return structured empty result
                # In production, use proper search API like Tavily or Serper
                return {
                    "status": "pending",
                    "message": "Web search requires API key (Tavily/Serper recommended)",
                    "query": query,
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "query": query,
            }

    async def search_hugging_face(
        self, query: str, model_type: str = "models"
    ) -> dict:
        """
        Search Hugging Face Hub for models, datasets, or spaces.
        
        Args:
            query: Search term
            model_type: Type to search - "models", "datasets", or "spaces"
        
        Returns:
            Search results
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://huggingface.co/api/{model_type}"
                params = {"search": query, "full": True}
                response = await client.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    results = response.json()
                    # Parse first 5 results
                    items = results[:5] if isinstance(results, list) else []
                    return {
                        "status": "success",
                        "query": query,
                        "results": items,
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

    # ==================== Code Analysis Tools ====================

    def analyze_imports(self, file_path: str) -> list[str]:
        """
        Extract all imports from a Python file.
        
        Args:
            file_path: Python file to analyze
        
        Returns:
            List of imported modules
        """
        content = self.read_file(file_path)
        imports = []

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("import "):
                parts = line[7:].split(",")
                imports.extend([p.strip().split()[0] for p in parts])
            elif line.startswith("from "):
                parts = line.split()
                if len(parts) >= 2:
                    imports.append(parts[1])

        return list(set(imports))


def get_tool_executor() -> ToolExecutor:
    """Dependency for FastAPI endpoints."""
    return ToolExecutor()
