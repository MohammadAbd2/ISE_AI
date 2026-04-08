from dataclasses import dataclass
from datetime import UTC, datetime
import subprocess
from pathlib import Path

from app.services.chat import ChatService
from app.services.profile import ProfileService
from app.plugins.filesystem.plugin import FileSystemPlugin


@dataclass(slots=True)
class ToolResult:
    name: str
    content: str


class AgentToolbox:
    """Small internal tool registry used by the chat agent."""

    def __init__(self, chat_service: ChatService, profile_service: ProfileService) -> None:
        self.chat_service = chat_service
        self.profile_service = profile_service
        self.filesystem_plugin = FileSystemPlugin()

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
        """Use FileSystemPlugin for real, accurate file system access"""
        try:
            path = self._extract_path_from_query(user_message)
            
            # Use FileSystem Plugin for accurate results
            if "how many" in user_message.lower():
                result = self.filesystem_plugin.count_files_in_folder(folder=path or None)
                if result["success"]:
                    total = result["total_files"]
                    categories = result.get("by_category", {})
                    content = f"**Total files in {result['folder']}: {total}**\n\n"
                    if categories:
                        content += "Files by category:\n"
                        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                            content += f"  • {cat}: {count}\n"
                    extensions = result.get("by_extension", {})
                    if extensions:
                        content += "\nTop file types:\n"
                        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:5]:
                            ext_display = ext if ext else "(no extension)"
                            content += f"  • {ext_display}: {count}\n"
                    return ToolResult(name="File System", content=content)
                else:
                    return ToolResult(name="File System", content=f"Error: {result.get('error', 'Unknown error')}")
            else:
                # List files
                result = self.filesystem_plugin.list_files(folder=path or None, limit=20)
                if result["success"]:
                    files = result.get("files", [])
                    content = f"**Files in {result['folder']}** ({result['count']} total)\n\n"
                    if files:
                        for f in files:
                            size_mb = f.get("size", 0) / (1024 * 1024)
                            if size_mb < 0.01:
                                size_str = f"{f.get('size', 0)} B"
                            else:
                                size_str = f"{size_mb:.2f} MB"
                            content += f"  • {f['name']} ({size_str}) - {f.get('category', 'unknown')}\n"
                        if result['count'] > 20:
                            content += f"\n... and {result['count'] - 20} more files"
                    return ToolResult(name="File System", content=content)
                else:
                    return ToolResult(name="File System", content=f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            return ToolResult(name="File System", content=f"Error: {str(e)}")

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
