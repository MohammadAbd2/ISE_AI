from functools import lru_cache
import re
import shutil
import subprocess
import sys
import tempfile

from backend.app.services.artifacts import ArtifactService, get_artifact_service


class SandboxService:
    """Run small code snippets in an isolated temporary workspace with a timeout."""

    def __init__(self, artifact_service: ArtifactService) -> None:
        self.artifact_service = artifact_service

    def should_execute(self, user_message: str) -> bool:
        lower = user_message.lower()
        return (
            "```" in user_message
            and any(trigger in lower for trigger in ["run", "execute", "sandbox", "test this code"])
        )

    async def execute_from_message(self, session_id: str, user_message: str) -> str | None:
        match = re.search(r"```(\w+)?\n([\s\S]*?)```", user_message)
        if not match:
            return None
        language = (match.group(1) or "python").lower()
        code = match.group(2).strip()
        if not code:
            return None
        result = await self._execute(language, code)
        await self.artifact_service.create_artifact(
            session_id=session_id,
            kind="sandbox",
            title=f"{language} execution",
            content=result,
            metadata={"language": language},
        )
        return result

    async def _execute(self, language: str, code: str) -> str:
        command, filename = self._command_for(language)
        with tempfile.TemporaryDirectory(prefix="ise_ai_sandbox_") as workdir:
            file_path = f"{workdir}/{filename}"
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(code)
            result = subprocess.run(
                [*command, file_path],
                capture_output=True,
                text=True,
                timeout=12,
                cwd=workdir,
                check=False,
            )
        stdout = result.stdout.strip() or "(no stdout)"
        stderr = result.stderr.strip()
        if stderr:
            return (
                f"Sandbox execution result\n"
                f"Exit code: {result.returncode}\n"
                f"Stdout:\n{stdout}\n\nStderr:\n{stderr}"
            )
        return (
            f"Sandbox execution result\n"
            f"Exit code: {result.returncode}\n"
            f"Stdout:\n{stdout}"
        )

    def _command_for(self, language: str) -> tuple[list[str], str]:
        if language in {"python", "py"}:
            return [sys.executable], "snippet.py"
        if language in {"javascript", "js"}:
            node = shutil.which("node")
            if node is None:
                raise ValueError("Node.js is not installed, so JavaScript sandbox execution is unavailable.")
            return [node], "snippet.js"
        if language in {"bash", "sh", "shell"}:
            shell = shutil.which("bash")
            if shell is None:
                raise ValueError("bash is not installed, so shell sandbox execution is unavailable.")
            return [shell], "snippet.sh"
        raise ValueError(f"Unsupported sandbox language: {language}")


@lru_cache
def get_sandbox_service() -> SandboxService:
    return SandboxService(artifact_service=get_artifact_service())
