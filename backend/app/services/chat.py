from functools import lru_cache
from typing import AsyncIterator

from backend.app.core.config import settings
from backend.app.models.message import Message
from backend.app.providers.base import LLMProvider
from backend.app.providers.ollama import OllamaProvider


class ChatService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def _build_effort_instruction(self, effort: str) -> str:
        instructions = {
            "low": (
                "Reason with low effort. Prefer a fast, concise answer and avoid unnecessary detail."
            ),
            "medium": (
                "Reason with medium effort. Balance speed, clarity, and completeness."
            ),
            "high": (
                "Reason with high effort. Be more deliberate, check your reasoning carefully, "
                "and provide a more complete answer when the question benefits from it."
            ),
        }
        return instructions.get(effort, instructions["medium"])

    def _build_generation_options(self, effort: str) -> dict:
        profiles = {
            "low": {"temperature": 0.2, "num_predict": 256},
            "medium": {"temperature": 0.15, "num_predict": 512},
            "high": {"temperature": 0.1, "num_predict": 1024},
        }
        return profiles.get(effort, profiles["medium"])

    def _build_messages(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        effort: str = "medium",
    ) -> list[Message]:
        # Compose one system message so provider adapters receive a clean message list.
        system_parts = [
            settings.system_prompt,
            self._build_effort_instruction(effort),
            (
                "You can use long-term memory across different chats. "
                "If a fact comes from long-term memory, say that you remember it from saved memory, "
                "not that it was only mentioned in the current chat. "
                "If you do not know something, say so plainly."
            ),
        ]
        if custom_instructions.strip():
            system_parts.append(f"Custom instructions:\n{custom_instructions.strip()}")
        memory_items = memory_items or []
        if memory_items:
            system_parts.append(
                "Long-term memory:\n" + "\n".join(f"- {item}" for item in memory_items)
            )
        if memory_note.strip():
            system_parts.append(memory_note.strip())
        tool_context = tool_context or []
        if tool_context:
            system_parts.append(
                "Tool results:\n" + "\n\n".join(tool_context)
            )
        messages = [Message(role="system", content="\n\n".join(system_parts))]
        messages.extend(conversation)
        messages.append(Message(role="user", content=user_message))
        return messages

    async def generate_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        model: str | None = None,
        effort: str = "medium",
    ) -> tuple[str, str]:
        selected_model = model or settings.default_model
        messages = self._build_messages(
            user_message=user_message,
            conversation=conversation,
            custom_instructions=custom_instructions,
            memory_items=memory_items,
            memory_note=memory_note,
            tool_context=tool_context,
            effort=effort,
        )
        reply = await self.provider.generate(
            messages=messages,
            model=selected_model,
            options=self._build_generation_options(effort),
        )
        return reply, selected_model

    async def stream_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        model: str | None = None,
        effort: str = "medium",
    ) -> tuple[AsyncIterator[str], str]:
        selected_model = model or settings.default_model
        messages = self._build_messages(
            user_message=user_message,
            conversation=conversation,
            custom_instructions=custom_instructions,
            memory_items=memory_items,
            memory_note=memory_note,
            tool_context=tool_context,
            effort=effort,
        )
        stream = self.provider.stream_generate(
            messages=messages,
            model=selected_model,
            options=self._build_generation_options(effort),
        )
        return stream, selected_model

    async def available_models(self) -> list[str]:
        return await self.provider.list_models()


@lru_cache
def get_chat_service() -> ChatService:
    """Reuse one chat service instance across requests."""
    return ChatService(provider=OllamaProvider())
