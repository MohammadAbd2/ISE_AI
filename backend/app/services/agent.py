import asyncio
import json
import re
import os
import shutil
from pathlib import Path
from typing import AsyncIterator, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, UTC

from app.models.message import Message
from app.schemas.chat import (
    ChatAttachment,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImageIntelLog,
    WebSearchLog,
    RenderBlock,
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
from app.services.research_memory import get_research_memory_service
from app.services.self_reflection import get_self_reflection_service
from app.services.turn_diagnostics import get_turn_diagnostics_service
from app.services.self_upgrade_executor import SelfUpgradeExecutor
from app.services.self_rewrite_manager import SelfRewriteManager
from app.services.tool_registry import get_tool_registry, PythonExecutorTool, WebScraperTool, WebResearchTool
from app.services.advanced_planner import AdvancedPlanner, ExecutionPlan, SubTask, TaskStatus, TaskPriority
from app.services.planning_agent import AutonomousPlanningAgent, get_planning_agent
from app.core.config import settings
from app.services.project_exports import get_project_export_service
from app.services.backup import get_backup_manager
from app.services.programming_agi_runtime import get_programming_agi_runtime


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
        self.research_memory = get_research_memory_service()
        self.self_reflection = get_self_reflection_service()
        self.turn_diagnostics = get_turn_diagnostics_service()
        self.self_upgrade_executor = SelfUpgradeExecutor()
        self.self_rewrite_manager = SelfRewriteManager()
        self.tool_registry = get_tool_registry()
        self.tool_registry.register(PythonExecutorTool())
        self.tool_registry.register(WebScraperTool())
        self.tool_registry.register(WebResearchTool())
        self.advanced_planner = AdvancedPlanner()

    async def respond(self, payload: ChatRequest, session_id: str | None = None) -> ChatResponse:
        profile = await self.profile_service.get_profile()
        intent = self.intent_classifier.classify(payload.message, payload.mode)

        # Determine if we should use agent mode
        use_agent_mode = intent.use_agent

        # Check for pending confirmation first
        pending_reply = await self._handle_pending_confirmation(payload.message, session_id)
        if pending_reply:
            if isinstance(pending_reply, ChatResponse):
                return pending_reply
            return ChatResponse(reply=str(pending_reply), model=payload.model or "agent")

        explicit_self_rewrite = self.self_rewrite_manager.classify(payload.message).should_handle
        explicit_self_reflection = self.self_reflection.should_activate(payload.message)
        if use_agent_mode or explicit_self_rewrite or explicit_self_reflection:
            # Use autonomous agent for coding tasks
            decision = await self._decide(
                payload.message,
                session_id=session_id,
                attachments=payload.attachments,
            )
        else:
            # FIRST: Try to execute simple file creation directly (bypass LLM)
            file_creation_result = await self._try_execute_file_creation(payload.message)
            if file_creation_result:
                response = ChatResponse(
                    reply=file_creation_result,
                    model=payload.model or "agent",
                )
                await self._learn_from_interaction(payload, response)
                return response

            # Check if this is a filesystem query (read-only operations)
            intent = self.intent_classifier.classify(payload.message, payload.mode)
            if intent.use_filesystem:
                # Handle filesystem query directly with toolbox (read-only: count, list, read)
                results = await self.toolbox.run_requested_tools(payload.message)
                if results:
                    reply = self.toolbox.format_direct_reply(results)
                    response = ChatResponse(
                        reply=reply,
                        model=payload.model or "agent",
                    )
                    await self._learn_from_interaction(payload, response)
                    return response

            # Check if this is a file creation/editing query (write operations)
            # These need to go to the coding agent which ACTUALLY creates files
            if intent.kind == "coding":
                # Route to coding agent for file creation/editing
                decision = await self._decide(
                    payload.message,
                    session_id=session_id,
                    attachments=payload.attachments,
                )
            else:
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
            self._record_turn_diagnostic(payload, intent, decision)
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
        
        try:
            reply, model = await self.service.generate_reply(
                user_message=payload.message,
                conversation=conversation,
                custom_instructions=profile.get("custom_instructions", ""),
                memory_items=profile.get("memory", []),
                memory_note=decision.memory_note,
                tool_context=(decision.tool_context or []) + personalized_context,
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
        except Exception as exc:
            response = ChatResponse(
                reply=self._llm_failure_reply(exc),
                model=payload.model or "agent",
                search_logs=decision.search_logs or [],
                image_logs=decision.image_logs or [],
                render_blocks=decision.render_blocks or [],
            )
        self._record_turn_diagnostic(payload, intent, decision)
        
        # Learn from this interaction
        await self._learn_from_interaction(payload, response)
        
        return response

    async def models(self) -> list[str]:
        """Return available models from the chat service."""
        return await self.service.available_models()

    async def stream_response(
        self,
        payload: ChatRequest,
        conversation: list[ChatMessage] | list[Message] | None = None,
        session_id: str | None = None,
        progress_callback=None,
    ) -> tuple[AsyncIterator[str], str, list[WebSearchLog], list[ImageIntelLog], list[dict]]:
        profile = await self.profile_service.get_profile()
        intent = self.intent_classifier.classify(payload.message, payload.mode)
        session = await self.history_service.get_session(session_id) if self.history_service and session_id else None

        # Determine if we should use agent mode
        use_agent_mode = intent.use_agent

        # Check for pending confirmation first
        pending_reply = await self._handle_pending_confirmation(payload.message, session_id)
        if pending_reply:
            if isinstance(pending_reply, ChatResponse):
                return (
                    self._stream_text(pending_reply.reply),
                    pending_reply.model,
                    pending_reply.search_logs or [],
                    pending_reply.image_logs or [],
                    pending_reply.render_blocks or [],
                )
            return (
                self._stream_text(str(pending_reply)),
                payload.model or "agent",
                [],
                [],
                [],
            )

        explicit_self_rewrite = self.self_rewrite_manager.classify(payload.message).should_handle
        if use_agent_mode or explicit_self_rewrite or self.self_reflection.should_activate(payload.message):
            # Use autonomous agent for coding tasks
            decision = await self._decide(
                payload.message,
                session_id=session_id,
                attachments=payload.attachments,
                progress_callback=progress_callback,
            )
        else:
            # Check if this is a filesystem query (read-only operations)
            if intent.use_filesystem:
                # Handle filesystem query directly with toolbox (read-only: count, list, read)
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

            # Check if this is a file creation/editing query (write operations)
            # These need to go to the coding agent
            if intent.kind == "coding":
                # Route to coding agent for file creation/editing
                decision = await self._decide(
                    payload.message,
                    session_id=session_id,
                    attachments=payload.attachments,
                    progress_callback=progress_callback,
                )
            else:
                # For simple file creation requests, try to execute them directly
                file_creation_result = await self._try_execute_file_creation(payload.message)
                if file_creation_result:
                    return (
                        self._stream_text(file_creation_result),
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
        
        if decision and decision.reply is not None:
            self._record_turn_diagnostic(payload, intent, decision)
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

        continue_fallback = self._build_continue_fallback(payload.message, session)
        if continue_fallback:
            self._record_turn_diagnostic(payload, intent, decision)
            return (
                self._stream_text(continue_fallback),
                payload.model or "agent",
                (decision.search_logs or []) if decision else [],
                (decision.image_logs or []) if decision else [],
                (decision.render_blocks or []) if decision else [],
            )
        
        # Get personalized context from learning system
        personalized_context = await self._get_personalized_context(payload.message)
        
        try:
            reply_iter, model = await self.service.stream_reply(
                user_message=payload.message,
                conversation=normalized,
                custom_instructions=profile.get("custom_instructions", ""),
                memory_items=profile.get("memory", []),
                memory_note=decision.memory_note if decision else "",
                tool_context=((decision.tool_context or []) if decision else []) + personalized_context,
                model=payload.model,
                effort=payload.effort,
            )
            self._record_turn_diagnostic(payload, intent, decision)
            return (
                reply_iter,
                model,
                (decision.search_logs or []) if decision else [],
                (decision.image_logs or []) if decision else [],
                (decision.render_blocks or []) if decision else [],
            )
        except Exception as exc:
            self._record_turn_diagnostic(payload, intent, decision)
            return (
                self._stream_text(self._llm_failure_reply(exc)),
                payload.model or "agent",
                decision.search_logs or [],
                decision.image_logs or [],
                decision.render_blocks or [],
            )

    async def _decide(
        self,
        user_message: str,
        session_id: str | None = None,
        attachments: list[str] | None = None,
        progress_callback=None,
    ) -> AgentDecision:
        """
        Determine which autonomous capability to use.
        """
        # 1. Check for explicit self-rewrite request
        rewrite_decision = self.self_rewrite_manager.classify(user_message)
        if rewrite_decision.should_handle:
            result = await self.self_rewrite_manager.execute(
                user_message,
                session_id=session_id,
                progress_callback=progress_callback,
            )
            return AgentDecision(
                reply=result.reply,
                render_blocks=result.render_blocks,
                used_agents=result.used_agents,
            )

        # 2. Check for self-reflection/improvement request only when it is explicit.
        if self.self_reflection.should_activate(user_message) and not self._looks_like_user_project_task(user_message):
            if self.self_reflection.should_execute(user_message):
                guidance = await self.self_reflection.build_guidance()
                packet = self.self_reflection.extract_execution_packet(guidance)
                if packet:
                    result = await self.self_upgrade_executor.execute_packet(packet, session_id=session_id)
                    return AgentDecision(
                        reply=result.reply,
                        render_blocks=result.render_blocks,
                        used_agents=result.used_agents,
                    )
            guidance = await self.self_reflection.build_guidance()
            return AgentDecision(
                reply=guidance["reply"],
                render_blocks=guidance["render_blocks"],
                used_agents=["self-reflection-agent"],
            )

        # 3. Handle complex tasks with roadmap and sandbox
        intent = self.intent_classifier.classify(user_message, "agent")
        if intent.kind == "coding" or self._is_complex_task(user_message):
            return await self._handle_complex_task(user_message, session_id, progress_callback)

        # 4. Fallback to standard orchestration
        orchestration = await self.orchestrator.run(
            user_message=user_message,
            session_id=session_id,
            attachments=attachments,
        )
        return AgentDecision(
            memory_note="",
            tool_context=orchestration.tool_context if orchestration.tool_context else None,
            search_logs=orchestration.search_logs or [],
            image_logs=orchestration.image_logs or [],
            render_blocks=orchestration.render_blocks or [],
        )

    def _is_download_request(self, message: str) -> bool:
        lower = message.lower()
        return any(token in lower for token in ("zip", "download", "downloadable", "give me the file", "give me the zip", "export"))

    def _is_complex_task(self, message: str) -> bool:
        lower = message.lower()
        complex_keywords = ["create", "build", "entire", "full", "landing page", "website", "application", "system", "project", "zip", "download"]
        return any(kw in lower for kw in complex_keywords) and len(message.split()) > 5

    def _looks_like_user_project_task(self, message: str) -> bool:
        lower = message.lower()
        task_terms = [
            "create", "build", "zip", "download", "component", "react", "frontend", "backend",
            "file", "landing page", "website", "project", "sandbox", "merge", "documentation",
            "dashboard", "terminal", "fix this", "fix the app", "implement", "roadmap first",
        ]
        self_terms = ["yourself", "your self", "your own code", "self-upgrade", "improve yourself", "fix yourself"]
        return any(term in lower for term in task_terms) and not any(term in lower for term in self_terms)

    async def _handle_complex_task(
        self,
        user_message: str,
        session_id: str | None,
        progress_callback=None,
    ) -> AgentDecision:
        """Route chat coding/build tasks through the dynamic Programming AGI.

        This makes the normal chat use the same engine as the MAX Dynamic AGI
        panel: dynamic contract planning, safe sandbox ingestion, verification,
        repair, preview contract, AGI_Output export, and merge metadata.
        """
        runtime = get_programming_agi_runtime()
        if progress_callback:
            await progress_callback({
                "type": "programming_agi_run",
                "payload": {
                    "status": "running",
                    "title": "Programming AGI started",
                    "message": "Routing through dynamic planner, sandbox, verifier, repair, preview, and export agents.",
                },
            })
        result = runtime.run(user_message, export_zip=self._is_download_request(user_message))
        blocks = self._programming_agi_render_blocks(result)
        if progress_callback:
            await progress_callback({"type": "programming_agi_run", "payload": result})

        if session_id and self.history_service:
            await self.history_service.set_pending_action(session_id, {
                "action": "programming_agi_merge",
                "run_id": result.get("run_id"),
                "sandbox_path": result.get("sandbox_path"),
                "export": result.get("export"),
                "preview": result.get("preview"),
            })

        status = result.get("status", "processed")
        changed_count = len(result.get("files_changed") or [])
        preview = result.get("preview") or {}
        export = result.get("export") or {}
        reply = (
            f"Programming AGI run {status}. "
            f"{changed_count} file(s) changed. "
            f"Preview: {preview.get('url') or 'not available'}. "
            f"ZIP: {'ready' if export.get('path') else 'not requested or blocked'}."
        )
        return AgentDecision(
            reply=reply,
            render_blocks=blocks,
            used_agents=["ProgrammingAGI", "RouterAgent", "PlannerAgent", "VerifierAgent", "RepairAgent", "PreviewAgent", "ExportAgent"],
        )

    def _programming_agi_render_blocks(self, result: dict) -> list[dict]:
        steps = result.get("steps") or []
        files = result.get("files_changed") or []
        validation = result.get("validation") or {}
        export = result.get("export") or {}
        return [
            {"type": "programming_agi_run", "payload": result},
            {
                "type": "report",
                "payload": {
                    "title": "Dynamic Programming AGI Result",
                    "summary": "The chat agent used the dynamic AGI runtime instead of the legacy static sandbox component.",
                    "highlights": [
                        f"Status: {result.get('status')}",
                        f"Progress: {result.get('progress')}%",
                        f"Files changed: {len(files)}",
                        f"Validation: {'passed' if validation.get('passed') else 'needs attention'}",
                        f"Output root: {export.get('output_root', './AGI_Output')}",
                    ],
                },
            },
            {
                "type": "plan_result",
                "payload": {
                    "title": "Stateful AGI workflow",
                    "status": result.get("status"),
                    "steps": [
                        {
                            "step_number": idx + 1,
                            "description": step.get("title"),
                            "target": step.get("agent"),
                            "status": step.get("status"),
                            "error": step.get("error"),
                        }
                        for idx, step in enumerate(steps)
                    ],
                },
            },
            {
                "type": "file_result",
                "payload": {
                    "title": "Sandbox file changes",
                    "files": [{"path": path, "title": path, "summary": "Changed by Programming AGI"} for path in files],
                },
            },
        ]

    async def _handle_pending_confirmation(
        self,
        user_message: str,
        session_id: str | None,
    ) -> Any | None:
        if session_id is None:
            return None

        # 1. Check for evolution pending capability
        pending_cap = self.session_manager.get_pending_capability(session_id)
        if pending_cap:
            if self._is_approval(user_message):
                self.session_manager.clear_pending(session_id)
                return await self._develop_capability(pending_cap.capability_name)
            if is_rejection(user_message):
                self.session_manager.clear_pending(session_id)
                return "Capability development canceled."

        # 2. Check for history pending action (merge, forget, etc.)
        if self.history_service:
            pending = await self.history_service.get_pending_action(session_id)
            if pending:
                if self._is_download_request(user_message) and pending.get("export_artifact"):
                    artifact = pending.get("export_artifact") or {}
                    return ChatResponse(
                        reply="Your ZIP is ready below. Click the download button to save it to your local machine.",
                        model="agent",
                        render_blocks=[{
                            "type": "file_result",
                            "payload": {
                                "title": "Latest sandbox ZIP",
                                "files": [{
                                    "title": artifact.get("title", "Sandbox ZIP"),
                                    "summary": "Download the latest generated sandbox artifact.",
                                    "artifact_id": artifact.get("id"),
                                }],
                            },
                        }],
                    )
                if self._is_approval(user_message):
                    await self.history_service.set_pending_action(session_id, None)
                    return await self._execute_pending_action(pending, session_id)
                if is_rejection(user_message):
                    await self.history_service.set_pending_action(session_id, None)
                    return "The pending action was canceled."
            
        return None

    async def _execute_pending_action(self, pending: dict, session_id: str | None = None) -> Any:
        action = pending.get("action")
        if action == "merge_sandbox":
            return await self._merge_sandbox_to_local(pending, session_id)
        
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

    async def _merge_sandbox_to_local(self, pending: dict, session_id: str | None) -> ChatResponse:
        sandbox_branch = pending.get("sandbox_branch")
        changed_files = pending.get("changed_files", [])
        user_message = pending.get("user_message", "")
        
        if not sandbox_branch:
            return ChatResponse(reply="Error: Sandbox branch not found.", model="agent")

        # Determine output path: output -> user -> session -> project
        user_id = "default_user" # Fallback
        try:
            profile = await self.profile_service.get_profile()
            user_id = profile.get("id", user_id)
        except: pass
        
        session_id_str = session_id or "default_session"
        project_name = self._extract_project_name(user_message)
        
        output_root = Path(settings.backend_root).parent.parent / "output"
        target_dir = output_root / user_id / session_id_str / project_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        sandbox_path = pending.get("sandbox_path")
        sandbox_dir = Path(sandbox_path) if sandbox_path else None
        if not sandbox_dir or not sandbox_dir.exists():
            return ChatResponse(reply="Error: Sandbox workspace not found. It may have been removed.", model="agent")

        backup_manager = get_backup_manager()
        backup_info = backup_manager.create_backup(
            reason=f"Pre-merge backup for sandbox {sandbox_branch}",
            files=None if not target_dir.exists() else [str(target_dir.relative_to(Path(settings.project_root)))] if target_dir.exists() else None,
        )

        # Copy files to local output folder
        merged_files = []
        for rel_path in changed_files:
            src = sandbox_dir / rel_path
            dst = target_dir / rel_path
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                merged_files.append(rel_path)

        export_result = None
        try:
            export_result = await get_project_export_service().export_directory(
                source_dir=target_dir,
                session_id=session_id or session_id_str,
                title=f"{project_name} export",
                filename=f"{project_name}.zip",
            )
        except Exception:
            export_result = None

        reply = (
            f"✅ **Successfully merged changes to your local machine!**\n\n"
            f"📁 **Output Location:** `{target_dir}`\n"
            f"📄 **Files Merged:** {len(merged_files)}\n"
            f"📦 **ZIP Export:** {'ready below with a download icon' if export_result else 'not generated'}\n\n"
            f"You can now find your project files in the path above."
        )

        highlights = [f"Destination: {target_dir}", f"Files: {len(merged_files)}"]
        if backup_info.get("status") == "success":
            highlights.append(f"Backup: {backup_info.get('id')}")
        if export_result and export_result.artifact:
            highlights.append(f"Download artifact: {export_result.artifact['title']}")

        return ChatResponse(
            reply=reply,
            model="agent",
            render_blocks=[
                {
                    "type": "report",
                    "payload": {
                        "title": "Merge Complete",
                        "summary": "Project files were copied from the sandbox, backed up before merge, and packaged for download.",
                        "highlights": highlights,
                    }
                }
            ]
        )


    def _extract_project_name(self, message: str) -> str:
        # Simple extraction, can be improved
        match = re.search(r"(?:project|called|named)\s+['\"]?([\w-]+)['\"]?", message, re.I)
        if match:
            return match.group(1)
        return "restaurant_landing_page" if "restaurant" in message.lower() else "generated_project"

    def _is_approval(self, message: str) -> bool:
        """Check if message is an approval response."""
        lower = message.lower().strip()
        approval_responses = [
            "yes", "y", "ok", "okay", "sure", "go ahead", "develop it",
            "develop my skills", "improve yourself", "add it", "install it", "merge", "merge it"
        ]
        return lower in approval_responses or any(
            lower.startswith(resp) for resp in approval_responses
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

    async def _develop_capability(self, capability_name: str) -> str:
        """
        Trigger autonomous capability development with progress logging.
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

    def _llm_failure_reply(self, exc: Exception | None) -> str:
        base = "I encountered an issue generating a response."
        detail = str(exc).strip() if exc else ""
        if detail:
            return f"{base}\n\nDetails: {detail}"
        return base

    def _build_continue_fallback(self, user_message: str, session: dict | None) -> str | None:
        lower = (user_message or "").strip().lower()
        if lower not in {"continue", "keep going", "go on"}:
            return None
        if not session:
            return None

        messages = session.get("messages", [])
        for message in reversed(messages):
            if message.get("role") != "assistant":
                continue
            render_blocks = message.get("render_blocks") or []
            summary = self._summarize_render_blocks(render_blocks)
            if summary:
                return summary
        return None

    def _summarize_render_blocks(self, render_blocks: list[dict]) -> str | None:
        if not render_blocks:
            return None

        report_summary = None
        plan_payload = None
        file_payload = None
        execution_payload = None

        for block in render_blocks:
            block_type = block.get("type")
            payload = block.get("payload") or {}
            if block_type == "report" and not report_summary:
                report_summary = payload.get("summary")
            elif block_type == "plan_result" and not plan_payload:
                plan_payload = payload
            elif block_type == "file_result" and not file_payload:
                file_payload = payload
            elif block_type == "execution_packet" and not execution_payload:
                execution_payload = payload

        lines: list[str] = []
        if report_summary:
            lines.append(report_summary)
        if plan_payload:
            status = plan_payload.get("status", "unknown")
            steps = plan_payload.get("steps") or []
            completed = sum(1 for step in steps if (step.get("status") or "").lower() == "completed")
            lines.append(f"Execution status: {status}. Completed steps: {completed}/{len(steps)}.")
            pending = [step for step in steps if (step.get("status") or "").lower() not in {"completed"}][:3]
            if pending:
                lines.append(
                    "Next pending items: "
                    + "; ".join(step.get("description", "pending step") for step in pending if step.get("description"))
                    + "."
                )
        if file_payload:
            files = file_payload.get("files") or []
            if files:
                lines.append(
                    "Latest changed files: " + ", ".join(file.get("path", "unknown") for file in files[:5] if file.get("path")) + "."
                )
        if execution_payload:
            merge_ready = execution_payload.get("merge_ready")
            if merge_ready is not None:
                lines.append(f"Merge ready: {'yes' if merge_ready else 'no'}.")

        if not lines:
            return None
        return "\n\n".join(lines)

    def _should_use_agent_mode(self, message: str, mode: str) -> bool:
        return self.intent_classifier.classify(message, mode).use_agent

    def _record_turn_diagnostic(self, payload: ChatRequest, intent, decision: AgentDecision) -> None:
        self.turn_diagnostics.record(
            message=payload.message,
            mode=payload.mode,
            intent_kind=intent.kind,
            use_agent=intent.use_agent,
            used_agents=decision.used_agents or [],
            search_count=len(decision.search_logs or []),
            image_count=len(decision.image_logs or []),
            render_block_types=[block.get("type", "") for block in (decision.render_blocks or []) if isinstance(block, dict)],
            had_reply=decision.reply is not None,
        )

    async def _try_execute_file_creation(self, user_message: str) -> str | None:
        """
        Try to execute a simple file operation request directly.
        """
        import re
        from app.services.tool_executor import ToolExecutor
        from app.plugins.filesystem.plugin import FileSystemPlugin
        from app.core.config import settings

        project_root = Path(settings.backend_root).parent.parent
        fs_plugin = FileSystemPlugin(root_path=str(project_root))

        lower = user_message.lower()

        # === FILE DELETION ===
        if any(phrase in lower for phrase in ["delete file", "delete the file", "remove file", "remove the file"]):
            patterns = [
                r"(?:delete|remove)\s+(?:the\s+)?file\s+['\"]?([\w./_-]+)['\"]?",
                r"(?:delete|remove)\s+['\"]?([\w./_-]+\.\w+)['\"]?",
            ]
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    file_path = match.group(1).strip()
                    if not file_path.startswith("/"):
                        full_path = str(project_root / file_path)
                    else:
                        full_path = file_path

                    result = fs_plugin.delete_file(file_path=full_path)
                    if result["success"]:
                        return (
                            f"🗑️ **File deleted:** `{result.get('path', file_path)}`\n"
                            f"*Freed {result.get('size_freed', 0)} bytes*"
                        )
                    else:
                        return f"❌ **Delete failed:** {result.get('error', 'Unknown error')}"
            return None

        # === FILE RENAME ===
        if any(phrase in lower for phrase in ["rename file", "rename the file"]):
            patterns = [
                r"rename\s+(?:file\s+)?['\"]?([\w./_-]+)['\"]?\s+to\s+['\"]?([\w./_-]+)['\"]?",
            ]
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    old_path = match.group(1).strip()
                    new_path = match.group(2).strip()
                    if not old_path.startswith("/"):
                        old_full = str(project_root / old_path)
                    else:
                        old_full = old_path
                    if not new_path.startswith("/"):
                        new_full = str(project_root / new_path)
                    else:
                        new_full = new_path

                    result = fs_plugin.rename_file(old_path=old_full, new_path=new_full)
                    if result["success"]:
                        return (
                            f"✏️ **File renamed:** `{old_path}` → `{new_path}`"
                        )
                    else:
                        return f"❌ **Rename failed:** {result.get('error', 'Unknown error')}"
            return None

        # === FILE UPDATE/WRITE ===
        if any(phrase in lower for phrase in ["write to file", "write content to", "save to file", "update file", "update the file", "edit file", "edit the file"]):
            patterns = [
                r"(?:write|save)\s+['\"]([^'\"]+)['\"]\s+(?:to|into)\s+['\"]?([\w./_-]+)['\"]?",
                r"(?:update|edit)\s+(?:file\s+)?['\"]?([\w./_-]+)['\"]?\s+(?:with|to)\s+['\"]([^'\"]+)['\"]?",
            ]
            for pattern in patterns:
                match = re.search(pattern, user_message.lower())
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        if '.' in groups[0] and '/' in groups[0]:
                            file_path, content = groups[0].strip(), groups[1].strip()
                        else:
                            content, file_path = groups[0].strip(), groups[1].strip()

                        if not file_path.startswith("/"):
                            full_path = str(project_root / file_path)
                        else:
                            full_path = file_path

                        try:
                            executor = ToolExecutor()
                            result = executor.write_file(path=full_path, content=content)
                            return (
                                f"✏️ **File updated:** `{result['path']}`\n"
                                f"*Wrote {result['bytes_written']} bytes*"
                            )
                        except Exception as e:
                            return f"❌ **Write failed:** {str(e)}"
            return None

        # === FILE CREATION ===
        if not any(phrase in lower for phrase in ["create", "write", "make", "new file"]):
            return None

        patterns = [
            r"(?:create|write|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+)?([\w.-]+)\s+(?:inside|in)\s+(?:the\s+)?(?:folder\s+)?([\w./-]+)\s+(?:contain|with\s+content|containing)\s+['\"]([^'\"]+)['\"]",
            r"(?:create|write|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+)?([\w.-]+)\s+(?:contain|with\s+content|containing)\s+['\"]([^'\"]+)['\"]",
            r"(?:create|write|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+)?([\w.-]+)\s+with\s+content\s+['\"]([^'\"]+)['\"]",
            r"(?:write|put)\s+['\"]([^'\"]+)['\"]\s+(?:to|into|in)\s+(?:file\s+)?([\w./-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    filename, folder, content = groups
                    file_path = str(project_root / folder / filename)
                elif len(groups) == 2:
                    if '.' in groups[0] and len(groups[0]) < 50:
                        filename, content = groups
                        file_path = str(project_root / filename)
                    else:
                        content, filename = groups
                        file_path = str(project_root / filename)
                else:
                    continue

                try:
                    executor = ToolExecutor()
                    result = executor.write_file(file_path, content)

                    if result.get("status") == "success":
                        return (
                            f"📝 **Creating file:** `{file_path}`\n\n"
                            f"**Content:**\n```\n{content}\n```\n\n"
                            f"✅ **File created successfully!**\n"
                            f"- **Path:** `{file_path}`\n"
                            f"- **Size:** {result.get('bytes_written', 0)} bytes\n"
                            f"- **Lines:** {len(content.splitlines())}"
                        )
                    else:
                        return None
                except Exception as e:
                    return None

        return None

    async def _learn_from_interaction(self, payload: ChatRequest, response: ChatResponse):
        """Learn from a user interaction to improve future responses."""
        try:
            await self.learning_system.initialize()
            await self.learning_system.learn_from_interaction(
                user_message=payload.message,
                assistant_response=response.reply,
                context="\n".join(payload.attachments) if payload.attachments else "",
                session_id=payload.session_id,
            )
        except Exception as e:
            print(f"Learning system error: {e}")

    async def _save_research_to_memory(self, query: str, search_logs: list[WebSearchLog] | None):
        """Automatically save research facts to long-term memory after a search."""
        if not search_logs:
            return
        
        for log in search_logs:
            if log.status == "failed" or not log.sources:
                continue
            
            facts_to_save = []
            if log.summary and len(log.summary) > 30:
                facts_to_save.append(f"Research: {log.summary}")
            
            for source in log.sources[:2]:
                if source.snippet and len(source.snippet) > 40:
                    first_part = source.snippet.split('.')[0].strip()
                    if len(first_part) > 30:
                        facts_to_save.append(f"From {source.domain or source.url}: {first_part}")
            
            if facts_to_save:
                for fact in facts_to_save[:3]:
                    await self.profile_service.remember(fact)

    async def _get_personalized_context(self, task: str) -> list[str]:
        """Get personalized context including learned preferences and research memory."""
        context_parts = []
        
        try:
            await self.learning_system.initialize()
            learning_context = await self.learning_system.get_personalized_context(task)
            if learning_context:
                if learning_context.get("user_preferences"):
                    context_parts.append(
                        f"User preferences: {json.dumps(learning_context['user_preferences'])}"
                    )
                if learning_context.get("code_styles"):
                    context_parts.append(
                        f"Preferred code styles: {json.dumps(learning_context['code_styles'])}"
                    )
                if learning_context.get("recommendations"):
                    context_parts.append(
                        f"Recommendations: {', '.join(learning_context['recommendations'])}"
                    )
        except Exception as e:
            print(f"Learning context error: {e}")
        
        try:
            research_context = self.research_memory.get_research_context(task)
            if research_context:
                context_parts.append(f"Research memory: {len(research_context)} facts available")
        except Exception as e:
            print(f"Research context error: {e}")
        
        return context_parts
