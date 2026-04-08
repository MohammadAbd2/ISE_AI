from dataclasses import dataclass
import asyncio
import json
from typing import AsyncIterator

from app.models.message import Message
from app.schemas.chat import (
    ChatAttachment,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImageIntelLog,
    WebSearchLog,
)
from app.services.chat import ChatService
from app.services.history import HistoryService
from app.services.orchestrator import get_multi_agent_orchestrator
from app.services.profile import (
    ProfileService,
    extract_helpful_memory,
    is_confirmation,
    is_rejection,
    parse_memory_intent,
)
from app.services.tools import AgentToolbox
from app.services.capability_gap_detector import (
    CapabilityGapDetector,
    get_capability_gap_detector,
)
from app.services.evolution_session import get_evolution_session_manager
from app.services.autonomous_developer import (
    AutonomousDeveloper,
    get_autonomous_developer,
)
from app.services.self_learning import get_learning_system
from app.services.intent_classifier import get_intent_classifier


@dataclass(slots=True)
class AgentDecision:
    reply: str | None = None
    memory_note: str = ""
    tool_context: list[str] | None = None
    used_agents: list[str] | None = None
    search_logs: list[WebSearchLog] | None = None
    image_logs: list[ImageIntelLog] | None = None
    render_blocks: list[dict] | None = None


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
        # Self-learning system
        self.learning_system = get_learning_system()
        self.intent_classifier = get_intent_classifier()

    async def respond(self, payload: ChatRequest, session_id: str | None = None) -> ChatResponse:
        profile = await self.profile_service.get_profile()

        # Determine if we should use agent mode
        use_agent_mode = self._should_use_agent_mode(payload.message, payload.mode)

        if use_agent_mode:
            # Use autonomous agent for coding tasks
            decision = await self._decide(
                payload.message,
                session_id=session_id,
                attachments=payload.attachments,
            )
        else:
            # Check if this is a filesystem query
            intent = self.intent_classifier.classify(payload.message, payload.mode)
            if intent.use_filesystem:
                # Handle filesystem query directly with toolbox
                results = await self.toolbox.run_requested_tools(payload.message)
                if results:
                    reply = self.toolbox.format_direct_reply(results)
                    response = ChatResponse(
                        reply=reply,
                        model=payload.model or "agent",
                    )
                    await self._learn_from_interaction(payload, response)
                    return response

            # Use regular chat for questions - still run orchestrator to get tools/search
            orchestration = await self.orchestrator.run(
                user_message=payload.message,
                session_id=session_id,
                attachments=payload.attachments,
            )
            decision = AgentDecision(
                memory_note="",
                tool_context=orchestration.tool_context if orchestration.tool_context else None,
                search_logs=orchestration.search_logs or [],
                image_logs=orchestration.image_logs or [],
                render_blocks=orchestration.render_blocks or [],
            )

        if decision.reply is not None:
            response = ChatResponse(
                reply=decision.reply,
                model=payload.model or "agent",
                search_logs=decision.search_logs or [],
                image_logs=decision.image_logs or [],
                render_blocks=decision.render_blocks or [],
            )
            # Learn from this interaction
            await self._learn_from_interaction(payload, response)
            return response
            
        # Normalize schema objects into the provider-facing message model.
        conversation = [
            Message(role=message.role, content=message.content)
            for message in payload.conversation
        ]
        
        # Get personalized context from learning system
        personalized_context = await self._get_personalized_context(payload.message)
        
        reply, model = await self.service.generate_reply(
            user_message=payload.message,
            conversation=conversation,
            custom_instructions=profile.get("custom_instructions", ""),
            memory_items=profile.get("memory", []),
            memory_note=decision.memory_note,
            tool_context=decision.tool_context + personalized_context if decision.tool_context else personalized_context,
            model=payload.model,
            effort=payload.effort,
        )
        
        response = ChatResponse(
            reply=reply,
            model=model,
            search_logs=decision.search_logs or [],
            image_logs=decision.image_logs or [],
            render_blocks=decision.render_blocks or [],
        )
        
        # Learn from this interaction
        await self._learn_from_interaction(payload, response)
        
        return response

    async def stream_response(
        self,
        payload: ChatRequest,
        conversation: list[ChatMessage] | list[Message] | None = None,
        session_id: str | None = None,
    ) -> tuple[AsyncIterator[str], str, list[WebSearchLog], list[ImageIntelLog], list[dict]]:
        profile = await self.profile_service.get_profile()

        # Determine if we should use agent mode
        use_agent_mode = self._should_use_agent_mode(payload.message, payload.mode)

        if use_agent_mode:
            # Use autonomous agent for coding tasks
            decision = await self._decide(
                payload.message,
                session_id=session_id,
                attachments=payload.attachments,
            )
        else:
            # Check if this is a filesystem query
            intent = self.intent_classifier.classify(payload.message, payload.mode)
            if intent.use_filesystem:
                # Handle filesystem query directly with toolbox
                results = await self.toolbox.run_requested_tools(payload.message)
                if results:
                    reply = self.toolbox.format_direct_reply(results)
                    return (
                        self._stream_text(reply),
                        payload.model or "agent",
                        [],
                        [],
                        [],
                    )

            # Use regular chat for questions - still run orchestrator to get tools/search
            orchestration = await self.orchestrator.run(
                user_message=payload.message,
                session_id=session_id,
                attachments=payload.attachments,
            )
            decision = AgentDecision(
                memory_note="",
                tool_context=orchestration.tool_context if orchestration.tool_context else None,
                search_logs=orchestration.search_logs or [],
                image_logs=orchestration.image_logs or [],
                render_blocks=orchestration.render_blocks or [],
            )
        
        if decision.reply is not None:
            return (
                self._stream_text(decision.reply),
                payload.model or "agent",
                decision.search_logs or [],
                decision.image_logs or [],
                decision.render_blocks or [],
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
        return stream, model, decision.search_logs or [], decision.image_logs or [], decision.render_blocks or []

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
            from app.services.capability_registry import get_capability_registry
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
                render_blocks=orchestration.render_blocks,
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
            render_blocks=orchestration.render_blocks,
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
        """Stream text word by word for better UX."""
        words = text.split(" ")
        for i, word in enumerate(words):
            # Add space before word (except for first word)
            yield (word + " ") if i < len(words) - 1 else word
            # Small delay for natural streaming effect
            await asyncio.sleep(0.01)

    def _should_use_agent_mode(self, message: str, mode: str) -> bool:
        return self.intent_classifier.classify(message, mode).use_agent

    async def _learn_from_interaction(self, payload: ChatRequest, response: ChatResponse):
        """Learn from a user interaction to improve future responses."""
        try:
            # Initialize learning system
            await self.learning_system.initialize()
            
            # Learn from the interaction
            await self.learning_system.learn_from_interaction(
                user_message=payload.message,
                assistant_response=response.reply,
                context="\n".join(payload.attachments) if payload.attachments else "",
                session_id=payload.session_id,
            )
        except Exception as e:
            # Don't let learning failures break the chat
            print(f"Learning system error: {e}")

    async def _get_personalized_context(self, task: str) -> list[str]:
        """Get personalized context based on learned preferences."""
        try:
            # Initialize learning system
            await self.learning_system.initialize()
            
            # Get personalized context
            context = await self.learning_system.get_personalized_context(task)
            
            # Format as context for the LLM
            context_parts = []
            
            if context.get("user_preferences"):
                context_parts.append(
                    f"User preferences: {json.dumps(context['user_preferences'])}"
                )
            
            if context.get("code_styles"):
                context_parts.append(
                    f"Preferred code styles: {json.dumps(context['code_styles'])}"
                )
            
            if context.get("recommendations"):
                context_parts.append(
                    f"Recommendations: {', '.join(context['recommendations'])}"
                )
            
            return context_parts
        except Exception as e:
            # Don't let context failures break the chat
            print(f"Context generation error: {e}")
            return []
