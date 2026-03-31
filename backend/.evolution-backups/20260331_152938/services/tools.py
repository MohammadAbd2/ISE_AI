from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.services.chat import ChatService
from backend.app.services.profile import ProfileService


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

        return self._dedupe_results(results)

    def should_answer_directly(self, user_message: str, results: list[ToolResult]) -> bool:
        if not results:
            return False
        lower = user_message.lower()
        direct_markers = [
            "show",
            "list",
            "display",
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

    def _dedupe_results(self, results: list[ToolResult]) -> list[ToolResult]:
        seen: set[str] = set()
        deduped: list[ToolResult] = []
        for result in results:
            if result.name in seen:
                continue
            seen.add(result.name)
            deduped.append(result)
        return deduped
