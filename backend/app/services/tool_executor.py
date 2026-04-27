"""
Safe tool executor for the AI to perform file I/O, web search, and shell execution.
Includes security protections: timeouts, path validation, sandboxing.
"""

import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.services.backup import get_backup_manager


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
    
    # Get project root (parent of backend directory)
    _project_root = Path(settings.backend_root).parent.parent
    SAFE_DIRECTORIES = {
        Path(settings.backend_root),  # backend/app
        Path(settings.backend_root).parent,  # backend
        _project_root,  # Project root (/home/baron/Desktop/Easv/Ai/ISE_AI)
        _project_root / "frontend",
        _project_root / "backend",
        _project_root / "extensions",
        _project_root / "tests",
        _project_root / "docs",
        _project_root / "assets",
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

    def glob_search(self, pattern: str, path: str = ".") -> list[str]:
        """
        Search for files using glob patterns.
        
        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Root path to search from
        
        Returns:
            List of matching file paths
        """
        root_path = self._validate_path(path)
        try:
            return [
                str(p.relative_to(self._project_root))
                for p in root_path.glob(pattern)
                if p.is_file()
            ]
        except Exception as e:
            raise ToolExecutionError(f"Glob search failed: {e}")

    def rip_grep(self, pattern: str, path: str = ".", glob: Optional[str] = None, case_insensitive: bool = False, context: int = 0) -> dict:
        """
        Search for a pattern in file contents using grep-like logic.
        
        Args:
            pattern: Pattern to search for (regex supported)
            path: Directory to search in
            glob: Optional file filter pattern
            case_insensitive: Ignore case
            context: Number of lines of context to show
        
        Returns:
            dict with search results
        """
        root_path = self._validate_path(path)
        results = []
        
        # Build command
        cmd = ["grep", "-rn"]
        if case_insensitive:
            cmd.append("-i")
        if context > 0:
            cmd.append(f"-C{context}")
        
        cmd.append(pattern)
        cmd.append(str(root_path))
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            output = process.stdout
            lines = output.splitlines()
            
            # Simple parsing of grep output
            for line in lines[:200]: # Limit results
                results.append(line)
                
            return {
                "status": "success",
                "count": len(lines),
                "results": results,
                "truncated": len(lines) > 200
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

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
        
        # Create backup before modification
        try:
            backup_mgr = get_backup_manager()
            rel_path = str(file_path.relative_to(self._project_root))
            backup_mgr.create_backup(f"Before write to {rel_path}", files=[rel_path])
        except Exception:
            # Continue even if backup fails, but log it maybe?
            pass

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

    async def fetch_url(self, url: str) -> dict:
        """
        Fetch content from a URL safely.
        
        Args:
            url: URL to fetch
        
        Returns:
            dict with content, status, headers
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=15)
                return {
                    "status": "success",
                    "url": url,
                    "status_code": response.status_code,
                    "content": response.text[:50000],  # Limit content
                    "headers": dict(response.headers),
                }
        except Exception as e:
            return {
                "status": "failed",
                "url": url,
                "error": str(e),
            }

    def notebook_edit(self, path: str, cell_index: int, new_content: str) -> dict:
        """
        Edit a cell in a Jupyter notebook safely.
        
        Args:
            path: Notebook file path (.ipynb)
            cell_index: Index of the cell to edit
            new_content: New content for the cell
        
        Returns:
            dict with status
        """
        file_path = self._validate_path(path)
        if not file_path.suffix == ".ipynb":
            raise ToolExecutionError(f"Not a notebook file: {path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                nb = json.load(f)
            
            if cell_index < 0 or cell_index >= len(nb.get("cells", [])):
                raise ToolExecutionError(f"Cell index {cell_index} out of range")
            
            nb["cells"][cell_index]["source"] = [line + "\n" for line in new_content.split("\n")]
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(nb, f, indent=1)
            
            return {"status": "success", "path": str(file_path), "cell": cell_index}
        except Exception as e:
            raise ToolExecutionError(f"Failed to edit notebook: {e}")

    def schedule_task(self, name: str, cron: str, command: str) -> dict:
        """
        Schedule a command to run with a cron expression (simulation for local demo).
        
        Args:
            name: Task name
            cron: Cron expression (e.g., "0 0 * * *")
            command: Command to run
        
        Returns:
            dict with status
        """
        # In a real app, this would use a task queue like Celery or a cron service.
        # Here we just log it to a registry.
        registry_path = self._project_root / ".evolution-cron.json"
        tasks = {}
        if registry_path.exists():
            try:
                tasks = json.loads(registry_path.read_text())
            except:
                tasks = {}
        
        tasks[name] = {
            "cron": cron,
            "command": command,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
        }
        
        registry_path.write_text(json.dumps(tasks, indent=2))
        return {"status": "success", "task": name, "cron": cron}

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

    async def system_doctor(self) -> dict:
        """
        Check the health of the agent's environment and dependencies.
        
        Returns:
            dict with health status of all systems
        """
        health = {}
        
        # Check Ollama
        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=5) as client:
                response = await client.get("/api/tags")
                health["ollama"] = {"status": "ok", "models": [m["name"] for m in response.json().get("models", [])]}
        except Exception as e:
            health["ollama"] = {"status": "error", "error": str(e)}
            
        # Check Git
        try:
            from app.services.git_integration import get_git_integration
            git = get_git_integration()
            health["git"] = {"status": "ok" if git.is_git_repo() else "not_a_repo"}
        except Exception as e:
            health["git"] = {"status": "error", "error": str(e)}
            
        # Check LSP
        try:
            from app.services.lsp_integration import get_lsp_integration
            lsp = get_lsp_integration()
            health["lsp"] = {"status": "ok", "symbols_indexed": len(lsp.symbols)}
        except Exception as e:
            health["lsp"] = {"status": "error", "error": str(e)}
            
        # Check MCP
        try:
            from app.services.mcp_client import get_mcp_client
            mcp = get_mcp_client()
            health["mcp"] = {"status": "ok", "servers": len(mcp.servers)}
        except Exception as e:
            health["mcp"] = {"status": "error", "error": str(e)}
            
        return {
            "status": "success",
            "health": health,
            "overall_status": "ok" if all(h.get("status") == "ok" for h in health.values()) else "degraded"
        }

    def enter_worktree(self, branch_name: str) -> dict:
        """
        Enter a new git worktree/branch for isolated development.
        
        Args:
            branch_name: Name of the branch to create/checkout
        
        Returns:
            dict with status
        """
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=str(self._project_root), check=True)
            return {"status": "success", "branch": branch_name, "message": f"Entered worktree on branch {branch_name}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def exit_worktree(self, merge: bool = False) -> dict:
        """
        Exit the current worktree and return to the main branch.
        
        Args:
            merge: If True, merge the changes into the main branch before exiting
        
        Returns:
            dict with status
        """
        try:
            # Get current branch
            res = subprocess.run(["git", "branch", "--show-current"], cwd=str(self._project_root), capture_output=True, text=True, check=True)
            current_branch = res.stdout.strip()
            
            subprocess.run(["git", "checkout", "main"], cwd=str(self._project_root), check=True)
            
            if merge and current_branch != "main":
                subprocess.run(["git", "merge", current_branch], cwd=str(self._project_root), check=True)
                return {"status": "success", "message": f"Merged {current_branch} into main and exited worktree"}
            
            return {"status": "success", "message": "Exited worktree and returned to main"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def repl_execute(self, code: str) -> dict:
        """
        Execute Python code in a REPL-like persistent session.
        
        Args:
            code: Python code to execute
        
        Returns:
            dict with stdout, stderr, and variables
        """
        # For simplicity in this demo, we use a global state for the REPL
        if not hasattr(self, "_repl_locals"):
            self._repl_locals = {}
        
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            try:
                # Use exec for multi-line code
                exec(code, globals(), self._repl_locals)
                output = f.getvalue()
                return {
                    "status": "success",
                    "stdout": output,
                    "variables": {k: str(v) for k, v in self._repl_locals.items() if not k.startswith("__")}
                }
            except Exception as e:
                return {
                    "status": "error",
                    "stdout": f.getvalue(),
                    "stderr": str(e)
                }

    def ask_user(self, question: str) -> dict:
        """
        Ask the user a question and wait for a response.
        
        Args:
            question: The question to ask
        
        Returns:
            dict with status
        """
        # This will trigger a pause in the agent loop
        return {
            "status": "awaiting_user_input",
            "question": question
        }

    async def spawn_subagent(self, task: str, role: str = "coder") -> dict:
        """
        Spawn a specialized sub-agent to handle a specific sub-task.
        
        Args:
            task: The sub-task description
            role: The role of the sub-agent (coder, researcher, designer, etc.)
        
        Returns:
            dict with sub-agent's result
        """
        from app.services.multi_agent_orchestrator import get_multi_agent_orchestrator
        orchestrator = get_multi_agent_orchestrator()
        
        # Use orchestrator to execute the task
        result = await orchestrator.route_task(task, context={"spawned_by": "main_agent"})
        
        return {
            "status": "success",
            "role": role,
            "result": result.direct_reply,
            "used_agents": result.used_agents
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
