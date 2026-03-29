from typing import AsyncIterator

from backend.app.models.message import Message
from backend.app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from backend.app.services.chat import ChatService
from backend.app.services.profile import (
    ProfileService,
    detect_memory_command,
    extract_helpful_memory,
)


class ChatAgent:
    """
    Thin orchestration layer for conversation policy.
    Add tool routing, memory, or multi-agent delegation here later.
    """

    def __init__(self, service: ChatService, profile_service: ProfileService) -> None:
        self.service = service
        self.profile_service = profile_service

    async def respond(self, payload: ChatRequest) -> ChatResponse:
        profile = await self.profile_service.get_profile()
        memory_note = await self._apply_memory_policy(payload.message)
        conversation = [
            Message(role=message.role, content=message.content)
            for message in payload.conversation
        ]
        reply, model = await self.service.generate_reply(
            user_message=payload.message,
            conversation=conversation,
            custom_instructions=profile.get("custom_instructions", ""),
            memory_items=profile.get("memory", []),
            memory_note=memory_note,
            model=payload.model,
        )
        return ChatResponse(reply=reply, model=model)

    async def stream_response(
        self,
        payload: ChatRequest,
        conversation: list[ChatMessage] | list[Message] | None = None,
    ) -> tuple[AsyncIterator[str], str]:
        profile = await self.profile_service.get_profile()
        memory_note = await self._apply_memory_policy(payload.message)
        source = conversation if conversation is not None else payload.conversation
        normalized = [
            item if isinstance(item, Message) else Message(role=item.role, content=item.content)
            for item in source
        ]
        return await self.service.stream_reply(
            user_message=payload.message,
            conversation=normalized,
            custom_instructions=profile.get("custom_instructions", ""),
            memory_items=profile.get("memory", []),
            memory_note=memory_note,
            model=payload.model,
        )

    async def models(self) -> list[str]:
        return await self.service.available_models()

    async def _apply_memory_policy(self, user_message: str) -> str:
        action, payload = detect_memory_command(user_message)
        if action == "remember" and payload:
            await self.profile_service.remember(payload)
            return "Memory update: the user requested that this information be remembered."
        if action == "forget_all":
            await self.profile_service.forget_all()
            return "Memory update: all long-term memory has been cleared as requested."
        if action == "forget" and payload:
            removed = await self.profile_service.forget(payload)
            if removed:
                return "Memory update: the requested memory was removed."
            return "Memory update: no matching long-term memory entry was found."

        for item in extract_helpful_memory(user_message):
            await self.profile_service.remember(item)
        return ""
