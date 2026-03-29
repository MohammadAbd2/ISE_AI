from functools import lru_cache
from typing import AsyncIterator

from backend.app.core.config import settings
from backend.app.models.message import Message
from backend.app.providers.base import LLMProvider
from backend.app.providers.ollama import OllamaProvider


class ChatService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def generate_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        model: str | None = None,
    ) -> tuple[str, str]:
        selected_model = model or settings.default_model
        system_parts = [
            settings.system_prompt,
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
        messages = [Message(role="system", content="\n\n".join(system_parts))]
        messages.extend(conversation)
        messages.append(Message(role="user", content=user_message))
        reply = await self.provider.generate(messages=messages, model=selected_model)
        return reply, selected_model

    async def stream_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        model: str | None = None,
    ) -> tuple[AsyncIterator[str], str]:
        selected_model = model or settings.default_model
        system_parts = [
            settings.system_prompt,
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
        messages = [Message(role="system", content="\n\n".join(system_parts))]
        messages.extend(conversation)
        messages.append(Message(role="user", content=user_message))
        stream = self.provider.stream_generate(messages=messages, model=selected_model)
        return stream, selected_model

    async def available_models(self) -> list[str]:
        return await self.provider.list_models()


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(provider=OllamaProvider())
