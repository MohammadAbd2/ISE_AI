from dataclasses import dataclass
from datetime import UTC, datetime
import subprocess
from pathlib import Path

from app.services.chat import ChatService
from app.services.profile import ProfileService
from app.plugins.filesystem.plugin import FileSystemPlugin
from app.services.project_indexing import get_project_indexer


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
        self.project_indexer = get_project_indexer()

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
            "how many folders",
            "how many directories",
            "files in the",
            "folders in the",
            "directories in the",
            "list files in",
            "list folders in",
            "list directories in",
            "count files",
            "count folders",
            "count directories",
            "count the files",
            "count the folders",
            "count the directories",
            "how many files in",
            "how many folders in",
            "how many directories in",
            "list dir",
            "list directory",
            "show files in",
            "show folders in",
            "show directories in",
            "what files",
            "what folders",
            "what directories",
            "inside the folder",
            "inside the directory",
            "within the folder",
            "within the directory",
            "search in files",
            "search for",
            "find in files",
            "replace in files",
            "search and replace",
            "find and replace",
            "file tree",
            "project tree",
            "directory tree",
        ]
        return any(phrase in lower for phrase in phrases)

    async def _list_files_tool(self, user_message: str) -> ToolResult:
        """Use FileSystemPlugin and ProjectIndexer for real, accurate file system access"""
        try:
            path = self._extract_path_from_query(user_message)
            lower = user_message.lower()

            # Check if asking for file tree
            if any(phrase in lower for phrase in ["file tree", "project tree", "directory tree", "show tree", "get tree"]):
                result = self.filesystem_plugin.get_file_tree(folder=path or None, max_depth=5)
                if result["success"]:
                    tree = result.get("tree", {})
                    root = result.get("root", "root")
                    content = f"🌳 **File tree for `{root}`:**\n\n"
                    content += self._format_tree_node(tree, indent=0)
                    return ToolResult(name="File Tree", content=content)
                else:
                    return ToolResult(name="File System", content=f"❌ Error: {result.get('error', 'Unknown error')}")

            # Check if asking for search in files
            if any(phrase in lower for phrase in ["search in files", "search for", "find in files", "find all"]):
                pattern = self._extract_search_pattern(user_message)
                if pattern:
                    result = self.filesystem_plugin.search_in_files(
                        pattern=pattern,
                        folder=path or None,
                        use_regex=False,
                        limit=50,
                    )
                    if result["success"]:
                        matches = result.get("results", [])
                        count = result.get("matches_found", 0)
                        files_searched = result.get("files_searched", 0)
                        content = f"🔍 **Search results for `{pattern}`:**\n\n"
                        content += f"*Found {count} matches in {files_searched} files*\n\n"
                        if matches:
                            for match in matches[:20]:
                                content += f"📄 `{match['file']}` line {match['line']}\n"
                                content += f"   `{match['content']}`\n\n"
                            if count > 20:
                                content += f"*... and {count - 20} more matches*\n"
                        return ToolResult(name="Search Results", content=content)
                    else:
                        return ToolResult(name="File System", content=f"❌ Error: {result.get('error', 'Unknown error')}")

            # Check if asking for replace in files
            if any(phrase in lower for phrase in ["replace in files", "search and replace", "find and replace"]):
                search_pattern = self._extract_search_pattern(user_message)
                replacement = self._extract_replacement_text(user_message)
                if search_pattern and replacement:
                    result = self.filesystem_plugin.replace_in_files(
                        search_pattern=search_pattern,
                        replacement=replacement,
                        folder=path or None,
                    )
                    if result["success"]:
                        files_modified = result.get("files_modified", 0)
                        total_replacements = result.get("total_replacements", 0)
                        modified_files = result.get("modified_files", [])
                        content = f"✏️ **Replace results:**\n\n"
                        content += f"*Modified {files_modified} files, {total_replacements} replacements*\n\n"
                        if modified_files:
                            for mf in modified_files:
                                content += f"📄 `{mf['file']}` - {mf['replacements']} replacements\n"
                        return ToolResult(name="Replace Results", content=content)
                    else:
                        return ToolResult(name="File System", content=f"❌ Error: {result.get('error', 'Unknown error')}")

            # Check if asking for folder/directory count
            if any(phrase in lower for phrase in ["how many folders", "how many directories", "count folders", "count directories"]):
                result = self.filesystem_plugin.list_directories(folder=path or None, recursive=False, limit=1000)
                if result["success"]:
                    directories = result.get("directories", [])
                    count = len(directories)
                    folder = result.get("folder", "root")
                    content = f"📁 **Total folders in `{folder}`:** **{count}**\n\n"
                    if directories:
                        content += "🗂️ **Folders:**\n"
                        for d in directories[:50]:
                            content += f"  📂 `{d}`\n"
                        if count > 50:
                            content += f"\n*... and {count - 50} more folders*"
                    return ToolResult(name="File System", content=content)
                else:
                    return ToolResult(name="File System", content=f"❌ Error: {result.get('error', 'Unknown error')}")

            # Check if asking for file count
            if "how many" in lower or "count" in lower:
                # Try Project Indexer first (faster, already indexed)
                if self.project_indexer.current_index:
                    result = self.project_indexer.count_files_in_folder(folder_path=path or "")
                    if result["success"]:
                        return self._format_file_count_result(result)

                # Fallback to FileSystemPlugin
                result = self.filesystem_plugin.count_files_in_folder(folder=path or None)
                if result["success"]:
                    return self._format_file_count_result(result)
                else:
                    return ToolResult(name="File System", content=f"Error: {result.get('error', 'Unknown error')}")

            # Check if asking to read a specific file
            if any(phrase in lower for phrase in ["content of", "read file", "show me the content", "display the content", "what's in the file", "what is in the file"]):
                file_path = self._extract_file_path_from_query(user_message)
                if file_path:
                    result = self.filesystem_plugin.read_file(file_path=file_path)
                    if result["success"]:
                        content_text = result.get("content", "")
                        file_name = result.get("file_name", file_path)
                        return ToolResult(name="File Content", content=f"**Content of `{file_name}`:**\n\n```\n{content_text}\n```")
                    else:
                        return ToolResult(name="File System", content=f"Error reading file: {result.get('error', 'Unknown error')}")

            # List files or directories
            if any(phrase in lower for phrase in ["list dir", "list directory", "list folders", "list directories", "show folders", "show directories"]):
                result = self.filesystem_plugin.list_directories(folder=path or None, recursive=False, limit=50)
                if result["success"]:
                    directories = result.get("directories", [])
                    folder = result.get("folder", "root")
                    content = f"📂 **Folders in `{folder}`** *({len(directories)} total)*\n\n"
                    if directories:
                        for d in directories[:50]:
                            content += f"  📁 `{d}`\n"
                    return ToolResult(name="File System", content=content)
                else:
                    return ToolResult(name="File System", content=f"❌ Error: {result.get('error', 'Unknown error')}")

            # Default: list files
            # Try Project Indexer first
            if self.project_indexer.current_index:
                result = self.project_indexer.list_files_in_folder(folder_path=path or "", limit=50)
                if result["success"]:
                    return self._format_file_list_result(result)

            # Fallback to FileSystemPlugin
            result = self.filesystem_plugin.list_files(folder=path or None, limit=50)
            if result["success"]:
                return self._format_file_list_result(result)
            else:
                return ToolResult(name="File System", content=f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            return ToolResult(name="File System", content=f"Error: {str(e)}")

    def _format_file_count_result(self, result: dict) -> ToolResult:
        """Format file count result with categories and nice formatting"""
        total = result.get("total_files", 0)
        folder = result.get("folder", "root")
        content = f"📊 **Total files in `{folder}`:** **{total}**\n\n"

        categories = result.get("by_category", {})
        if categories:
            content += "📁 **Files by category:**\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                content += f"  • `{cat}`: *{count}*\n"

        extensions = result.get("by_extension", {})
        if extensions:
            content += "\n📄 **Top file types:**\n"
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:5]:
                ext_display = ext if ext else "(no extension)"
                content += f"  • `{ext_display}`: *{count}*\n"

        return ToolResult(name="File System", content=content)

    def _format_file_list_result(self, result: dict) -> ToolResult:
        """Format file list result with nice formatting"""
        folder = result.get("folder", "root")
        files = result.get("files", [])
        count = result.get("count", len(files))

        content = f"📂 **Files in `{folder}`** *({count} total)*\n\n"
        if files:
            for f in files[:30]:
                # Handle both dict and string formats
                if isinstance(f, dict):
                    name = f.get("name", f.get("path", "unknown"))
                    size = f.get("size", 0)
                    size_mb = size / (1024 * 1024) if size > 0 else 0
                    if size_mb < 0.01:
                        size_str = f"{size} B"
                    else:
                        size_str = f"{size_mb:.2f} MB"
                    content += f"  📄 `{name}` *({size_str})*\n"
                else:
                    content += f"  📄 `{f}`\n"

            if count > 30:
                content += f"\n*... and {count - 30} more files*"

        return ToolResult(name="File System", content=content)

    def _extract_path_from_query(self, user_message: str) -> str:
        """Extract folder path from user query with better pattern matching"""
        lower = user_message.lower()
        import re

        # Pattern 1: "files in the ./tests folder", "files in assets", "files in ./frontend/src/components"
        # More comprehensive regex patterns
        patterns = [
            # "inside the folder ./path" or "inside the directory ./path"
            r"(?:in|inside|within)\s+(?:the\s+)?(?:folder|directory)\s+(?:['\"]?)(\.?/?[\w./_-]+)(?:['\"]?)(?:\s|\?|$)",
            # "inside ./path" (without "the folder")
            r"inside\s+(?:['\"]?)(\.?/?[\w./_-]+)(?:['\"]?)(?:\s|\?|$)",
            # "in the ./path/to/folder folder" or "in the 'path' directory"
            r"in\s+(?:the\s+)?(?:['\"]?)(\.?/?[\w./_-]+)(?:['\"]?)\s+(?:folder|directory)(?:\s|\?|$)",
            # "in ./path" or "in 'path'" - but NOT "in the <word>" where word is not a path
            # Only match if it starts with ./ or ../ or contains / or looks like a path
            r"in\s+(?:['\"]?)(\.[\w./_-]+)(?:['\"]?)(?:\s|\?|$)",
            # Specific known folder names
            r"\b(tests|test|src|source|backend|frontend|extensions|lib|app|components|utils|api|docs|config|scripts|assets|public|build|dist)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                path_str = match.group(1).strip() if match.lastindex and match.lastindex > 0 else match.group(0).strip()

                # Clean up the path - remove trailing punctuation but keep path chars
                path_str = path_str.rstrip("?.,;:")

                # Handle relative paths starting with ./ or ../
                if path_str.startswith("./") or path_str.startswith("../"):
                    return path_str

                # Handle absolute paths
                if path_str.startswith("/"):
                    return path_str

                # Handle simple folder names (but not common words like "the", "a", etc.)
                common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'many', 'much', 'some', 'any', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'just', 'don', 'now', 'project', 'files', 'file', 'folder', 'directory'}
                if path_str and path_str.lower() not in common_words and not any(c in path_str for c in ['?', '"', "'"]):
                    return path_str

        # If no path found, return empty string (will use root)
        return ""

    def _extract_file_path_from_query(self, user_message: str) -> str:
        """Extract specific file path from user query"""
        lower = user_message.lower()
        import re

        # Pattern: "main.jsx inside the folder ./frontend/src"
        patterns = [
            # "filename inside/in the folder ./path"
            r"([\w.-]+\.\w+)\s+(?:inside|in)\s+(?:the\s+)?(?:folder|directory)\s+(?:['\"]?)(\.?/?[\w./_-]+)(?:['\"]?)",
            # "inside the folder ./path show filename"
            r"(?:inside|in)\s+(?:the\s+)?(?:folder|directory)\s+(?:['\"]?)(\.?/?[\w./_-]+)(?:['\"]?).+?([\w.-]+\.\w+)",
            # "read ./path/to/file.ext"
            r"(?:read|show|display|content of)\s+(?:['\"]?)(\.?/?[\w./_-]+\.\w+)(?:['\"]?)",
            # Just filename with extension
            r"([\w.-]+\.(?:jsx|js|ts|tsx|py|json|txt|md|css|html|yml|yaml|xml|sh|bat|kt|java|c|cpp|h|hpp|rb|go|rs|php|swift|scala|pl|sql|graphql|toml|ini|cfg|conf))",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # First pattern: filename and folder
                    filename, folder = groups
                    return f"{folder}/{filename}" if folder else filename
                elif len(groups) == 1:
                    path_str = groups[0]
                    if path_str.startswith("./") or path_str.startswith("../") or path_str.startswith("/"):
                        return path_str
                    # Just a filename, try to find it in common locations
                    return path_str

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

    def _format_tree_node(self, node: dict, indent: int = 0) -> str:
        """Format tree node recursively"""
        if not node:
            return ""
        
        prefix = "  " * indent
        if node.get("type") == "directory":
            result = f"{prefix}📁 `{node.get('name', 'root')}/`\n"
            children = node.get("children", [])
            for child in children:
                result += self._format_tree_node(child, indent + 1)
            return result
        else:
            name = node.get("name", "unknown")
            size = node.get("size", 0)
            size_str = f" ({size} B)" if size > 0 else ""
            return f"{prefix}📄 `{name}`{size_str}\n"

    def _extract_search_pattern(self, user_message: str) -> str:
        """Extract search pattern from query"""
        import re
        lower = user_message.lower()
        
        # Patterns like "search for X", "find X", "search X in files"
        patterns = [
            r"(?:search|find|look for)\s+(?:the\s+)?(?:text\s+)?['\"]?([^'\"]+?)['\"]?(?:\s+in|\s+for|\s+of|$)",
            r"(?:search|find)\s+(?:for\s+)?['\"]?([\w.-]+)['\"]?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return match.group(1).strip()
        
        return ""

    def _extract_replacement_text(self, user_message: str) -> str:
        """Extract replacement text from query"""
        import re
        lower = user_message.lower()
        
        # Patterns like "replace with X", "replace X with Y"
        patterns = [
            r"replace\s+(?:with\s+)?['\"]?([^'\"]+?)['\"]?",
            r"with\s+['\"]?([^'\"]+?)['\"]?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                return match.group(1).strip()
        
        return ""
