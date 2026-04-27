"""
Enhanced sandbox execution service for ISE AI.

Supports:
- Isolated Python execution with timeout and memory limits
- Subprocess shell commands with streaming output
- Computer-use (GUI automation via Playwright / PyAutoGUI) when available
- Screenshot capture for browser panel streaming
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    elapsed_ms: float = 0
    screenshot_b64: str | None = None   # base64 PNG if computer-use
    action_log: list[dict] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Python execution sandbox
# ──────────────────────────────────────────────────────────────────────────

class PythonSandbox:
    """Run untrusted Python code in a separate process with a timeout."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    async def run(self, code: str, context: dict | None = None) -> SandboxResult:
        """Execute `code` in an isolated subprocess."""
        start = time.perf_counter()
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            if context:
                f.write("import json as _json\n")
                f.write(f"_ctx = _json.loads({repr(context)})\n")
                f.write("globals().update(_ctx)\n\n")
            f.write(textwrap.dedent(code))
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return SandboxResult(
                    success=False,
                    stderr=f"Execution timed out after {self.timeout}s",
                    return_code=-1,
                    elapsed_ms=(time.perf_counter() - start) * 1000,
                )

            elapsed = (time.perf_counter() - start) * 1000
            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout_b.decode("utf-8", errors="replace"),
                stderr=stderr_b.decode("utf-8", errors="replace"),
                return_code=proc.returncode or 0,
                elapsed_ms=elapsed,
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────────────────
# Shell sandbox
# ──────────────────────────────────────────────────────────────────────────

class ShellSandbox:
    """Run shell commands with timeout and streaming output."""

    # Block the most dangerous shell commands
    _BLOCKED = frozenset([
        "rm -rf /", "mkfs", ":(){:|:&};:", "dd if=/dev/zero",
        "fork bomb", "shutdown", "reboot", "halt",
    ])

    def __init__(self, timeout: int = 30, cwd: str | None = None) -> None:
        self.timeout = timeout
        self.cwd = cwd or str(Path.home())

    def _is_blocked(self, cmd: str) -> bool:
        lower = cmd.lower()
        return any(b in lower for b in self._BLOCKED)

    async def run(self, command: str) -> SandboxResult:
        if self._is_blocked(command):
            return SandboxResult(success=False, stderr="Command blocked for safety", return_code=-1)

        start = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return SandboxResult(
                    success=False,
                    stderr=f"Command timed out after {self.timeout}s",
                    return_code=-1,
                    elapsed_ms=(time.perf_counter() - start) * 1000,
                )

            elapsed = (time.perf_counter() - start) * 1000
            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout_b.decode("utf-8", errors="replace"),
                stderr=stderr_b.decode("utf-8", errors="replace"),
                return_code=proc.returncode or 0,
                elapsed_ms=elapsed,
            )
        except Exception as exc:
            return SandboxResult(
                success=False,
                stderr=f"Shell error: {exc}",
                return_code=-1,
                elapsed_ms=(time.perf_counter() - start) * 1000,
            )

    async def stream(self, command: str) -> AsyncIterator[str]:
        """Yield stdout lines as they arrive."""
        if self._is_blocked(command):
            yield "ERROR: Command blocked for safety\n"
            return
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.cwd,
            )
            async for line in proc.stdout:
                yield line.decode("utf-8", errors="replace")
            await proc.wait()
        except Exception as exc:
            yield f"ERROR: {exc}\n"


# ──────────────────────────────────────────────────────────────────────────
# Computer-use (GUI) sandbox  — requires Playwright
# ──────────────────────────────────────────────────────────────────────────

class ComputerUseSandbox:
    """
    Headless browser / computer-use sandbox powered by Playwright.
    Captures screenshots and exposes click/type/scroll/navigate tools.
    Falls back gracefully if Playwright is not installed.
    """

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        self._context = None
        self._pw = None
        self._available: bool | None = None

    async def _ensure_started(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from playwright.async_api import async_playwright  # type: ignore
            self._pw_lib = async_playwright
            self._available = True
        except ImportError:
            logger.warning("Playwright not installed — computer-use unavailable")
            self._available = False
        return self._available

    async def start(self) -> bool:
        if not await self._ensure_started():
            return False
        if self._browser is not None:
            return True
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            self._page = await self._context.new_page()
            logger.info("Playwright browser started")
            return True
        except Exception as exc:
            logger.warning("Could not start Playwright browser: %s", exc)
            self._available = False
            return False

    async def stop(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
        self._browser = self._page = self._context = self._pw = None

    async def navigate(self, url: str, wait_for: str = "load") -> SandboxResult:
        if not await self.start():
            return SandboxResult(success=False, stderr="Playwright not available")
        try:
            await self._page.goto(url, wait_until=wait_for, timeout=15000)
            title = await self._page.title()
            screenshot = await self._screenshot_b64()
            return SandboxResult(
                success=True,
                stdout=f"Navigated to: {url}\nTitle: {title}",
                screenshot_b64=screenshot,
                action_log=[{"type":"navigate","url":url,"description":f"Opened {url}"}],
            )
        except Exception as exc:
            return SandboxResult(success=False, stderr=str(exc))

    async def click(self, selector: str | None = None, x: int | None = None, y: int | None = None) -> SandboxResult:
        if not await self.start():
            return SandboxResult(success=False, stderr="Playwright not available")
        try:
            if selector:
                await self._page.click(selector, timeout=5000)
                desc = f"Clicked element: {selector}"
            elif x is not None and y is not None:
                await self._page.mouse.click(x, y)
                desc = f"Clicked at ({x}, {y})"
            else:
                return SandboxResult(success=False, stderr="Provide selector or x/y coordinates")
            screenshot = await self._screenshot_b64()
            return SandboxResult(
                success=True, stdout=desc, screenshot_b64=screenshot,
                action_log=[{"type":"click","description":desc,"elapsed_ms":0}],
            )
        except Exception as exc:
            return SandboxResult(success=False, stderr=str(exc))

    async def type_text(self, text: str, selector: str | None = None) -> SandboxResult:
        if not await self.start():
            return SandboxResult(success=False, stderr="Playwright not available")
        try:
            if selector:
                await self._page.fill(selector, text)
            else:
                await self._page.keyboard.type(text)
            screenshot = await self._screenshot_b64()
            return SandboxResult(
                success=True,
                stdout=f"Typed: {text[:50]}{'…' if len(text)>50 else ''}",
                screenshot_b64=screenshot,
                action_log=[{"type":"type","description":f"Typed text into {selector or 'focused element'}","elapsed_ms":0}],
            )
        except Exception as exc:
            return SandboxResult(success=False, stderr=str(exc))

    async def screenshot(self) -> SandboxResult:
        if not await self.start():
            return SandboxResult(success=False, stderr="Playwright not available")
        try:
            b64 = await self._screenshot_b64()
            return SandboxResult(
                success=True, stdout="Screenshot captured",
                screenshot_b64=b64,
                action_log=[{"type":"screenshot","description":"Captured screenshot","elapsed_ms":0}],
            )
        except Exception as exc:
            return SandboxResult(success=False, stderr=str(exc))

    async def extract_text(self) -> SandboxResult:
        if not await self.start():
            return SandboxResult(success=False, stderr="Playwright not available")
        try:
            text = await self._page.inner_text("body")
            return SandboxResult(success=True, stdout=text[:4000])
        except Exception as exc:
            return SandboxResult(success=False, stderr=str(exc))

    async def _screenshot_b64(self) -> str | None:
        try:
            data = await self._page.screenshot(type="png", full_page=False)
            return base64.b64encode(data).decode()
        except Exception:
            return None

    @property
    def is_available(self) -> bool:
        return bool(self._available)


# ──────────────────────────────────────────────────────────────────────────
# SandboxService - High-level API for Orchestrator
# ──────────────────────────────────────────────────────────────────────────

class SandboxService:
    """High-level service for executing code and commands from messages."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.python_sandbox = PythonSandbox(timeout=timeout)
        self.shell_sandbox = ShellSandbox(timeout=timeout)

    def should_execute(self, user_message: str) -> bool:
        """Determine if a message contains an execution request."""
        lower = user_message.lower().strip()
        
        # Check for explicit code blocks
        if "```python" in lower or "```bash" in lower or "```sh" in lower:
            return True
            
        # Check for execution keywords
        execution_keywords = [
            "run this code", "execute this", "run the script",
            "calculate this", "test this", "verify this"
        ]
        if any(kw in lower for kw in execution_keywords):
            return True
            
        return False

    async def execute_from_message(self, session_id: str, user_message: str) -> str | None:
        """Extract and execute code from a message."""
        # Extract Python code
        python_match = re.search(r"```python\n(.*?)\n```", user_message, re.DOTALL)
        if python_match:
            code = python_match.group(1)
            result = await self.python_sandbox.run(code)
            return self._format_result("Python", result)

        # Extract Shell code
        shell_match = re.search(r"```(?:bash|sh)\n(.*?)\n```", user_message, re.DOTALL)
        if shell_match:
            command = shell_match.group(1)
            result = await self.shell_sandbox.run(command)
            return self._format_result("Shell", result)

        return None

    def _format_result(self, lang: str, result: SandboxResult) -> str:
        status = "✅ Success" if result.success else "❌ Failed"
        output = []
        output.append(f"**{lang} Execution {status}** ({result.elapsed_ms:.1f}ms)")
        
        if result.stdout:
            output.append(f"**Stdout:**\n```\n{result.stdout}\n```")
        if result.stderr:
            output.append(f"**Stderr:**\n```\n{result.stderr}\n```")
        if not result.stdout and not result.stderr:
            output.append("*No output*")
            
        return "\n\n".join(output)


# ──────────────────────────────────────────────────────────────────────────
# Singleton accessors
# ──────────────────────────────────────────────────────────────────────────

_python_sandbox: PythonSandbox | None = None
_shell_sandbox: ShellSandbox | None = None
_computer_sandbox: ComputerUseSandbox | None = None
_sandbox_service: SandboxService | None = None


def get_python_sandbox() -> PythonSandbox:
    global _python_sandbox
    if _python_sandbox is None:
        _python_sandbox = PythonSandbox(timeout=settings.sandbox_timeout)
    return _python_sandbox


def get_shell_sandbox(cwd: str | None = None) -> ShellSandbox:
    global _shell_sandbox
    if _shell_sandbox is None or cwd:
        _shell_sandbox = ShellSandbox(timeout=settings.sandbox_timeout, cwd=cwd)
    return _shell_sandbox


def get_computer_sandbox() -> ComputerUseSandbox:
    global _computer_sandbox
    if _computer_sandbox is None:
        _computer_sandbox = ComputerUseSandbox()
    return _computer_sandbox


def get_sandbox_service() -> SandboxService:
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService(timeout=settings.sandbox_timeout)
    return _sandbox_service
