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
from backend.app.services.capability_gap_detector import (
    CapabilityGapDetector,
    get_capability_gap_detector,
)
from backend.app.services.evolution_session import get_evolution_session_manager
from backend.app.services.autonomous_developer import (
    AutonomousDeveloper,
    get_autonomous_developer,
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
    Includes autonomous self-development capabilities.
    """

    def __init__(
        self,
        service: ChatService,
        profile_service: ProfileService,
        history_service: HistoryService | None = None,
        gap_detector: CapabilityGapDetector | None = None,
    ) -> None:
        self.service = service
        self.profile_service = profile_service
        self.history_service = history_service
        self.toolbox = AgentToolbox(chat_service=service, profile_service=profile_service)
        self.orchestrator = get_multi_agent_orchestrator(self.toolbox)
        self.gap_detector = gap_detector or get_capability_gap_detector()
        # Use global session manager for persistent pending capabilities
        self.session_manager = get_evolution_session_manager()
        # Autonomous developer for self-improvement
        self.developer = get_autonomous_developer()

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

        # Check if user is approving a pending capability development
        if session_id:
            pending_capability = self.session_manager.get_pending_capability(session_id)
            if pending_capability and self._is_approval(user_message):
                # Clear the pending offer
                self.session_manager.clear_pending(session_id)

                # Start autonomous development
                try:
                    development_reply = await self._develop_capability(pending_capability)
                    return AgentDecision(reply=development_reply)
                except Exception as e:
                    return AgentDecision(
                        reply=f"Failed to develop {pending_capability}: {str(e)}"
                    )

        # Check for capability gaps and offer development
        # But first check if capability was already developed
        gaps = self.gap_detector.detect_gaps(user_message)
        if gaps:
            gap = gaps[0]
            
            # Check if capability is now available (was just developed)
            from backend.app.services.capability_registry import get_capability_registry
            registry = get_capability_registry()
            if registry.has_capability(gap.capability_name):
                # Capability is available, let the orchestrator handle it
                pass  # Continue to orchestrator
            else:
                # Track this pending capability for this session
                if session_id:
                    self.session_manager.offer_capability(session_id, gap.capability_name)
                # Return the offer message
                return AgentDecision(reply=gap.suggested_action)

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

    def _is_approval(self, message: str) -> bool:
        """Check if message is an approval response."""
        lower = message.lower().strip()
        approval_responses = [
            "yes", "y", "ok", "okay", "sure", "go ahead", "develop it",
            "develop my skills", "improve yourself", "add it", "install it"
        ]
        return lower in approval_responses or any(
            lower.startswith(resp) for resp in approval_responses
        )

    async def _develop_capability(self, capability_name: str) -> str:
        """
        Trigger autonomous capability development with progress logging.
        
        This is similar to how Qwen Code develops features:
        1. Search for models/packages
        2. Download and install
        3. Generate integration code
        4. Test and validate
        5. Show progress logs throughout

        Args:
            capability_name: Name of capability to develop

        Returns:
            Response message with progress logs
        """
        try:
            # Start autonomous development
            progress = await self.developer.develop_capability(capability_name)
            
            # Return progress log
            return progress.to_log_string()
            
        except Exception as e:
            import traceback
            error_msg = (
                f"❌ Error during capability development:\n\n"
                f"```\n{str(e)}\n```\n\n"
                f"Stack trace:\n```\n{traceback.format_exc()}\n```"
            )
            return error_msg

    async def _stream_text(self, text: str) -> AsyncIterator[str]:
        yield text
