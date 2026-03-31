from dataclasses import dataclass
from typing import AsyncIterator

from backend.app.models.message import Message
from backend.app.schemas.chat import (
    ChatAttachment,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImageIntelLog,
    WebSearchLog,
)
from backend.app.services.chat import ChatService
from backend.app.services.history import HistoryService
from backend.app.services.orchestrator import get_multi_agent_orchestrator
from backend.app.services.profile import (
    ProfileService,
    extract_helpful_memory,
    is_confirmation,
    is_rejection,
    parse_memory_intent,
)
from backend.app.services.tools import AgentToolbox
from backend.app.services.evolution_agent import EvolutionAgent, get_evolution_agent
from backend.app.services.capability_gap_detector import (
    CapabilityGapDetector,
    get_capability_gap_detector,
)


@dataclass(slots=True)
class AgentDecision:
    reply: str | None = None
    memory_note: str = ""
    tool_context: list[str] | None = None
    used_agents: list[str] | None = None
    search_logs: list[WebSearchLog] | None = None
    image_logs: list[ImageIntelLog] | None = None


class ChatAgent:
    """
    Thin orchestration layer for conversation policy.
    Now includes evolution detection for autonomous capability development.
    """

    def __init__(
        self,
        service: ChatService,
        profile_service: ProfileService,
        history_service: HistoryService | None = None,
        evolution_agent: EvolutionAgent | None = None,
        gap_detector: CapabilityGapDetector | None = None,
    ) -> None:
        self.service = service
        self.profile_service = profile_service
        self.history_service = history_service
        self.toolbox = AgentToolbox(chat_service=service, profile_service=profile_service)
        self.orchestrator = get_multi_agent_orchestrator(self.toolbox)
        self.evolution_agent = evolution_agent or get_evolution_agent()
        self.gap_detector = gap_detector or get_capability_gap_detector()

    async def respond(self, payload: ChatRequest, session_id: str | None = None) -> ChatResponse:
        profile = await self.profile_service.get_profile()
        decision = await self._decide(
            payload.message,
            session_id=session_id,
            attachments=payload.attachments,
        )
        if decision.reply is not None:
            return ChatResponse(
                reply=decision.reply,
                model=payload.model or "agent",
                search_logs=decision.search_logs or [],
                image_logs=decision.image_logs or [],
            )
        # Normalize schema objects into the provider-facing message model.
        conversation = [
            Message(role=message.role, content=message.content)
            for message in payload.conversation
        ]
        reply, model = await self.service.generate_reply(
            user_message=payload.message,
            conversation=conversation,
            custom_instructions=profile.get("custom_instructions", ""),
            memory_items=profile.get("memory", []),
            memory_note=decision.memory_note,
            tool_context=decision.tool_context,
            model=payload.model,
            effort=payload.effort,
        )
        return ChatResponse(
            reply=reply,
            model=model,
            search_logs=decision.search_logs or [],
            image_logs=decision.image_logs or [],
        )

    async def stream_response(
        self,
        payload: ChatRequest,
        conversation: list[ChatMessage] | list[Message] | None = None,
        session_id: str | None = None,
    ) -> tuple[AsyncIterator[str], str, list[WebSearchLog]]:
        profile = await self.profile_service.get_profile()
        decision = await self._decide(
            payload.message,
            session_id=session_id,
            attachments=payload.attachments,
        )
        if decision.reply is not None:
            return (
                self._stream_text(decision.reply),
                payload.model or "agent",
                decision.search_logs or [],
                decision.image_logs or [],
            )
        source = conversation if conversation is not None else payload.conversation
        normalized = [
            item if isinstance(item, Message) else Message(role=item.role, content=item.content)
            for item in source
        ]
        stream, model = await self.service.stream_reply(
            user_message=payload.message,
            conversation=normalized,
            custom_instructions=profile.get("custom_instructions", ""),
            memory_items=profile.get("memory", []),
            memory_note=decision.memory_note,
            tool_context=decision.tool_context,
            model=payload.model,
            effort=payload.effort,
        )
        return stream, model, decision.search_logs or [], decision.image_logs or []

    async def models(self) -> list[str]:
        return await self.service.available_models()

    async def _decide(
        self,
        user_message: str,
        session_id: str | None,
        attachments: list[ChatAttachment],
    ) -> AgentDecision:
        profile = await self.profile_service.get_profile()
        
        # NEW: Check for capability gaps and offer development
        try:
            evolution_decision = await self.evolution_agent.analyze_request(user_message)
            if evolution_decision.action == "offer_development":
                # AI detected a missing capability and should offer to develop it
                return AgentDecision(reply=evolution_decision.message)
        except Exception as e:
            # If evolution analysis fails, continue with normal flow
            pass
        
        pending_reply = await self._handle_pending_confirmation(user_message, session_id)
        if pending_reply is not None:
            return AgentDecision(reply=pending_reply)

        memory_reply = await self._handle_memory_intent(user_message, session_id)
        if memory_reply is not None:
            return AgentDecision(reply=memory_reply)

        orchestration = await self.orchestrator.run(
            user_message=user_message,
            session_id=session_id,
            attachments=attachments,
        )
        if orchestration.direct_reply is not None:
            return AgentDecision(
                reply=orchestration.direct_reply,
                used_agents=orchestration.used_agents,
                image_logs=orchestration.image_logs,
            )

        memory_note = ""
        for item in extract_helpful_memory(user_message, profile.get("memory", [])):
            await self.profile_service.remember(item)
            memory_note = "Memory update: user profile facts were updated automatically."

        return AgentDecision(
            memory_note=memory_note,
            tool_context=orchestration.tool_context,
            used_agents=orchestration.used_agents,
            search_logs=orchestration.search_logs,
            image_logs=orchestration.image_logs,
        )

    async def _handle_pending_confirmation(
        self,
        user_message: str,
        session_id: str | None,
    ) -> str | None:
        if session_id is None or self.history_service is None:
            return None
        pending = await self.history_service.get_pending_action(session_id)
        if pending is None:
            return None
        if is_confirmation(user_message):
            await self.history_service.set_pending_action(session_id, None)
            return await self._execute_pending_action(pending)
        if is_rejection(user_message):
            await self.history_service.set_pending_action(session_id, None)
            return "The pending memory change was canceled. No saved memory was deleted."
        return (
            "I have a pending memory deletion request. Reply `yes` to confirm or `no` to cancel."
        )

    async def _handle_memory_intent(
        self,
        user_message: str,
        session_id: str | None,
    ) -> str | None:
        sync_reply = await self._handle_memory_sync_request(user_message)
        if sync_reply is not None:
            return sync_reply

        intent = parse_memory_intent(user_message)
        if intent is None:
            return None

        if intent.action == "show":
            profile = await self.profile_service.get_profile()
            memory = profile.get("memory", [])
            if not memory:
                return "I do not currently have any saved memory."
            return "Saved memory:\n" + "\n".join(f"- {item}" for item in memory)

        if intent.action == "remember" and intent.entries:
            saved = await self.profile_service.remember_many(intent.entries)
            return "Saved to memory:\n" + "\n".join(f"- {item}" for item in saved)

        if intent.action in {"forget", "forget_all"}:
            if session_id is None or self.history_service is None:
                return (
                    "I need an active chat session before I can confirm a destructive memory change. "
                    "Please send the request again in the current chat."
                )
            pending_action = {"action": intent.action, "query": intent.query}
            await self.history_service.set_pending_action(session_id, pending_action)
            if intent.action == "forget_all":
                return (
                    "I am going to clear all saved memory. Reply `yes` to confirm or `no` to cancel."
                )
            return (
                f"I am going to remove memory related to `{intent.query}`. "
                "Reply `yes` to confirm or `no` to cancel."
            )

        return None

    async def _handle_memory_sync_request(self, user_message: str) -> str | None:
        lower = user_message.lower()
        memory_verbs = ["add", "update", "save", "store", "put"]
        if "memory" not in lower or not any(verb in lower for verb in memory_verbs):
            return None

        profile = await self.profile_service.get_profile()
        memory_items = profile.get("memory", [])
        extracted_entries = extract_helpful_memory(user_message, memory_items)
        if extracted_entries:
            saved = await self.profile_service.remember_many(extracted_entries)
            return "Saved to memory:\n" + "\n".join(f"- {item}" for item in saved)

        entries: list[str] = []

        if any(phrase in lower for phrase in ["your new name", "your name", "your nickname"]):
            entries.extend(
                item
                for item in memory_items
                if item.startswith("The assistant's name is")
                or item.startswith("The assistant's nickname is")
            )
        if any(phrase in lower for phrase in ["my name", "user name"]):
            entries.extend(
                item
                for item in memory_items
                if item.startswith("The user's name is")
            )

        entries = list(dict.fromkeys(entries))
        if entries:
            saved = await self.profile_service.remember_many(entries)
            return "Saved to memory:\n" + "\n".join(f"- {item}" for item in saved)

        if "update the memory" in lower or "update memory" in lower:
            return "Tell me the exact fact you want me to add or update in memory."

        return None

    async def _execute_pending_action(self, pending: dict) -> str:
        action = pending.get("action")
        if action == "forget_all":
            await self.profile_service.forget_all()
            return "All saved memory has been cleared."
        if action == "forget":
            query = pending.get("query", "")
            removed = await self.profile_service.forget(query)
            if removed:
                return f"Removed saved memory related to `{query}`."
            return f"No saved memory entry matched `{query}`."
        return "There was no valid pending action to execute."

    async def _stream_text(self, text: str) -> AsyncIterator[str]:
        yield text
