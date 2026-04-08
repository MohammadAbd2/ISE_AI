from dataclasses import dataclass
from datetime import UTC, datetime
import subprocess
from pathlib import Path

from app.services.chat import ChatService
from app.services.profile import ProfileService


@dataclass(slots=True)
class ToolResult:
    name: str
    content: str


class AgentToolbox:
    """Small internal tool registry used by the chat agent."""

    def __init__(self, chat_service: ChatService, profile_service: ProfileService) -> None:
        self.chat_service = chat_service
        self.profile_service = profile_service

    async def run_requested_tools(self, user_message: str) -> list[ToolResult]:
        lower = user_message.lower()
        results: list[ToolResult] = []

        if self._should_list_memory(lower):
            results.append(await self._memory_tool())
        if self._should_list_models(lower):
            results.append(await self._models_tool())
        if self._should_show_time(lower):
            results.append(self._time_tool())
        if self._should_show_profile(lower):
            results.append(await self._profile_tool())
        if self._should_list_files(lower):
            results.append(await self._list_files_tool(user_message))

        return self._dedupe_results(results)

    def should_answer_directly(self, user_message: str, results: list[ToolResult]) -> bool:
        if not results:
            return False
        lower = user_message.lower()
        direct_markers = [
            "show",
            "list",
            "display",
            "count",
            "how many",
            "what do you remember",
            "what models",
            "available models",
            "what time",
            "what date",
            "profile",
        ]
        return any(marker in lower for marker in direct_markers)

    def format_direct_reply(self, results: list[ToolResult]) -> str:
        return "\n\n".join(
            f"{result.name}:\n{result.content}"
            for result in results
        )

    def format_prompt_context(self, results: list[ToolResult]) -> list[str]:
        return [
            f"{result.name}\n{result.content}"
            for result in results
        ]

    async def _memory_tool(self) -> ToolResult:
        profile = await self.profile_service.get_profile()
        memory = profile.get("memory", [])
        if not memory:
            return ToolResult(
                name="Memory",
                content="No saved memory entries are currently stored.",
            )
        return ToolResult(
            name="Memory",
            content="\n".join(f"- {item}" for item in memory),
        )

    async def _models_tool(self) -> ToolResult:
        models = await self.chat_service.available_models()
        return ToolResult(
            name="Models",
            content="\n".join(f"- {model}" for model in models),
        )

    def _time_tool(self) -> ToolResult:
        now = datetime.now(UTC)
        return ToolResult(
            name="Current Time",
            content=(
                f"UTC date: {now.date().isoformat()}\n"
                f"UTC time: {now.strftime('%H:%M:%S')}"
            ),
        )

    async def _profile_tool(self) -> ToolResult:
        profile = await self.profile_service.get_profile()
        custom = profile.get("custom_instructions", "").strip() or "No custom instructions saved."
        memory_count = len(profile.get("memory", []))
        return ToolResult(
            name="Profile",
            content=(
                f"Custom instructions: {custom}\n"
                f"Saved memory entries: {memory_count}"
            ),
        )

    def _should_list_memory(self, lower: str) -> bool:
        phrases = [
            "show memory",
            "display memory",
            "list memory",
            "what do you remember",
            "what is in memory",
            "what's in memory",
            "saved memory",
        ]
        return any(phrase in lower for phrase in phrases)

    def _should_list_models(self, lower: str) -> bool:
        phrases = [
            "what models",
            "available models",
            "installed models",
            "list models",
            "show models",
        ]
        return any(phrase in lower for phrase in phrases)

    def _should_show_time(self, lower: str) -> bool:
        phrases = [
            "what time",
            "current time",
            "what date",
            "today's date",
            "todays date",
        ]
        return any(phrase in lower for phrase in phrases)

    def _should_show_profile(self, lower: str) -> bool:
        phrases = [
            "show profile",
            "display profile",
            "custom instructions",
            "assistant profile",
        ]
        return any(phrase in lower for phrase in phrases)

    def _should_list_files(self, lower: str) -> bool:
        phrases = [
            "how many files",
            "files in the",
            "list files in",
            "count files",
            "count the files",
            "how many files in",
            "list dir",
            "list directory",
            "show files in",
        ]
        return any(phrase in lower for phrase in phrases)

    async def _list_files_tool(self, user_message: str) -> ToolResult:
        try:
            path = self._extract_path_from_query(user_message)
            target_path = Path(path) if path else Path.cwd()
            
            if not target_path.exists():
                return ToolResult(
                    name="File System",
                    content=f"Path not found: {target_path}"
                )
            
            if target_path.is_file():
                return ToolResult(
                    name="File System",
                    content=f"This is a file, not a directory: {target_path.name}"
                )
            
            files = []
            try:
                for item in target_path.iterdir():
                    if not item.name.startswith("."):
                        files.append(item)
            except PermissionError:
                return ToolResult(
                    name="File System",
                    content=f"Permission denied accessing: {target_path}"
                )
            
            file_count = len(files)
            file_list = "\n".join(f"- {f.name}" for f in sorted(files)[:20])
            
            result_text = f"Directory: {target_path}\nTotal files/folders: {file_count}"
            if files:
                result_text += f"\n\nContents (showing first 20):\n{file_list}"
                if file_count > 20:
                    result_text += f"\n... and {file_count - 20} more items"
            
            return ToolResult(
                name="File System",
                content=result_text
            )
        except Exception as e:
            return ToolResult(
                name="File System",
                content=f"Error listing files: {str(e)}"
            )

    def _extract_path_from_query(self, user_message: str) -> str:
        lower = user_message.lower()
        
        # Extract path patterns like "files in the tests folder", "files in ./src"
        import re
        
        patterns = [
            r"files in\s+(?:the\s+)?(?:\'|\")?([^\'\"?\n]+?)(?:\'|\")?(?:\s|folder|directory|\?|$)",
            r"in\s+(?:the\s+)?(?:\'|\")?([^\'\"?\n]+?)(?:\'|\")?(?:\s|folder|directory|\?|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                path_str = match.group(1).strip()
                # Handle common patterns
                if "tests" in path_str:
                    return "tests"
                if "src" in path_str or "source" in path_str:
                    return "src"
                if "backend" in path_str:
                    return "backend"
                if "frontend" in path_str:
                    return "frontend"
                if "extensions" in path_str:
                    return "extensions"
                return path_str.strip()
        
        return ""

    def _dedupe_results(self, results: list[ToolResult]) -> list[ToolResult]:
        seen: set[str] = set()
        deduped: list[ToolResult] = []
        for result in results:
            if result.name in seen:
                continue
            seen.add(result.name)
            deduped.append(result)
        return deduped
