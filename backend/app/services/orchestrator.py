import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.schemas.chat import ChatAttachment, ImageIntelLog, WebSearchLog
from app.services.documents import DocumentService, get_document_service
from app.services.image_intel import ImageIntelService, get_image_intel_service
from app.services.sandbox import SandboxService, get_sandbox_service
from app.services.search import SearchService, get_search_service
from app.services.tools import AgentToolbox
from app.services.url_content import UrlContentService, get_url_content_service
from app.services.video_intel import VideoGenService, get_video_gen_service
from app.services.intent_classifier import get_intent_classifier
from app.services.artifacts import get_artifact_service
from app.services.dynamic_tool_registry import get_dynamic_tool_registry

# Try to import image generation service (may not exist yet)
try:
    from app.services.image_generation import generate_image as generate_image_service
    IMAGE_GEN_AVAILABLE = True
except ImportError:
    IMAGE_GEN_AVAILABLE = False
    generate_image_service = None


@dataclass(slots=True)
class OrchestratorResult:
    direct_reply: str | None = None
    tool_context: list[str] = field(default_factory=list)
    used_agents: list[str] = field(default_factory=list)
    search_logs: list[WebSearchLog] = field(default_factory=list)
    image_logs: list[ImageIntelLog] = field(default_factory=list)
    render_blocks: list[dict] = field(default_factory=list)


class UtilityAgent:
    name = "utility-agent"

    def __init__(self, toolbox: AgentToolbox) -> None:
        self.toolbox = toolbox

    async def run(self, user_message: str) -> OrchestratorResult:
        results = await self.toolbox.run_requested_tools(user_message)
        if self.toolbox.should_answer_directly(user_message, results):
            return OrchestratorResult(
                direct_reply=self.toolbox.format_direct_reply(results),
                used_agents=[self.name],
            )
        if results:
            return OrchestratorResult(
                tool_context=self.toolbox.format_prompt_context(results),
                used_agents=[self.name],
            )
        return OrchestratorResult()


class DocumentAgent:
    name = "document-agent"

    def __init__(self, document_service: DocumentService) -> None:
        self.document_service = document_service

    async def run(
        self,
        session_id: str | None,
        attachments: list[ChatAttachment],
        user_message: str,
    ) -> OrchestratorResult:
        context = await self.document_service.build_context(session_id, attachments, user_message)
        if not context:
            return OrchestratorResult()
        return OrchestratorResult(tool_context=context, used_agents=[self.name])


class ResearchAgent:
    name = "research-agent"

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        if session_id is None:
            return OrchestratorResult()
        context: list[str] = []
        context.extend(await self.search_service.recent_context(session_id, user_message))
        if not self.search_service.should_search(user_message):
            if context:
                return OrchestratorResult(tool_context=context, used_agents=[self.name])
            return OrchestratorResult()
        try:
            log = await self.search_service.search(session_id, query=user_message)
        except Exception as exc:
            log = self.search_service.failed_log(user_message, str(exc))
        context.append(self.search_service.build_prompt_context(log))
        return OrchestratorResult(
            tool_context=context,
            used_agents=[self.name],
            search_logs=[log],
            render_blocks=self.search_service.build_render_blocks(log),
        )


class UrlAgent:
    name = "url-agent"

    def __init__(self, url_content_service: UrlContentService) -> None:
        self.url_content_service = url_content_service

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        if session_id is None:
            return OrchestratorResult()
        try:
            context = await self.url_content_service.build_context(session_id, user_message)
        except Exception as exc:
            context = [f"URL analysis could not be completed: {exc}"]
        if not context:
            return OrchestratorResult()
        return OrchestratorResult(tool_context=context, used_agents=[self.name])


class ImageIntelAgent:
    name = "image-intel-agent"

    def __init__(self, image_intel_service: ImageIntelService) -> None:
        self._service = image_intel_service

    async def run(
        self,
        session_id: str | None,
        user_message: str,
        attachments: list[ChatAttachment],
    ) -> OrchestratorResult:
        if session_id is None:
            return OrchestratorResult()
        session_has = await self._service.session_has_recent_image(session_id)
        if not self._service.should_activate_sync(
            user_message,
            attachments,
            session_id,
            session_has,
        ):
            return OrchestratorResult()
        try:
            context, logs = await self._service.run(session_id, user_message, attachments)
        except Exception as exc:
            return OrchestratorResult(
                tool_context=[f"Image intelligence tools failed: {exc}"],
                used_agents=[self.name],
            )
        if not context and not logs:
            return OrchestratorResult()
        return OrchestratorResult(
            tool_context=context,
            used_agents=[self.name],
            image_logs=logs,
        )


class ExecutionAgent:
    name = "execution-agent"

    def __init__(self, sandbox_service: SandboxService) -> None:
        self.sandbox_service = sandbox_service

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        if session_id is None or not self.sandbox_service.should_execute(user_message):
            return OrchestratorResult()
        try:
            result = await self.sandbox_service.execute_from_message(session_id, user_message)
        except Exception as exc:
            result = f"Sandbox execution could not be completed: {exc}"
        if result is None:
            return OrchestratorResult()
        return OrchestratorResult(tool_context=[result], used_agents=[self.name])


class CapabilityAgent:
    name = "capability-agent"

    def __init__(self) -> None:
        self.registry = get_dynamic_tool_registry()
        self.artifacts = get_artifact_service()

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        if session_id is None:
            return OrchestratorResult()

        lower = user_message.lower()

        if self._wants_session_analytics(lower):
            payload = await self.registry.execute_tool_async(
                "session_analytics",
                session_id=session_id,
            )
            blocks = list(payload.get("render_blocks", []))
            if payload.get("visualization"):
                blocks.insert(0, {"type": "visualization", "payload": payload["visualization"]})
            blocks.append(
                {
                    "type": "report",
                    "payload": {
                        "title": "Session analytics",
                        "summary": "Loaded the latest visualization, render blocks, and artifacts for this session.",
                        "highlights": [
                            f"Artifacts: {len(payload.get('artifacts', []))}",
                            f"Context available: {'yes' if payload.get('has_context') else 'no'}",
                        ],
                    },
                }
            )
            return OrchestratorResult(
                direct_reply="Loaded the latest session analytics context.",
                used_agents=[self.name],
                render_blocks=blocks,
            )

        if self._wants_research_memory(lower):
            artifact = await self._latest_research_artifact(session_id)
            if artifact is None:
                return OrchestratorResult(
                    direct_reply="No saved research memory is available for this session yet.",
                    used_agents=[self.name],
                )
            result = await self.registry.execute_tool_async(
                "reopen_artifact",
                artifact_id=artifact["id"],
                session_id=session_id,
            )
            return OrchestratorResult(
                direct_reply=f"Reopened research memory: {artifact['title']}",
                used_agents=[self.name],
                render_blocks=result.get("render_blocks", []),
            )

        if self._wants_session_history(lower):
            payload = await self.registry.execute_tool_async(
                "session_history",
                session_id=session_id,
            )
            if payload.get("status") != "success":
                return OrchestratorResult()
            return OrchestratorResult(
                direct_reply=(
                    f"Session history: {payload['message_count']} messages in \"{payload['title']}\".\n\n"
                    + "\n".join(f"- {item['role']}: {item['content']}" for item in payload["messages"])
                ),
                used_agents=[self.name],
            )

        return OrchestratorResult()

    async def _latest_research_artifact(self, session_id: str) -> dict | None:
        rows = await self.artifacts.list_artifacts(session_id=session_id, kinds=["research"], limit=1)
        return rows[0] if rows else None

    def _wants_session_analytics(self, lower: str) -> bool:
        phrases = [
            "session analytics",
            "show analytics",
            "open analytics",
            "show session context",
            "show latest visualization",
        ]
        return any(phrase in lower for phrase in phrases)

    def _wants_research_memory(self, lower: str) -> bool:
        phrases = [
            "research memory",
            "open research memory",
            "show research memory",
            "latest research",
            "saved research",
        ]
        return any(phrase in lower for phrase in phrases)

    def _wants_session_history(self, lower: str) -> bool:
        phrases = [
            "session history",
            "chat history",
            "recent messages",
            "show conversation history",
        ]
        return any(phrase in lower for phrase in phrases)


class CodingAgent:
    """
    Intelligent coding agent with context understanding.

    NO TEMPLATES - Uses AI understanding to:
    - Analyze task context intelligently
    - Determine appropriate language/framework
    - Generate contextually appropriate code
    - Create proper file structures based on context
    """
    name = "coding-agent"

    def __init__(self) -> None:
        from app.services.intelligent_coding_agent import get_intelligent_coding_agent
        from app.services.planning_agent import get_planning_agent
        self.coding_agent = get_intelligent_coding_agent()
        self.planning_agent = get_planning_agent()
        self.intent_classifier = get_intent_classifier()
        self.artifacts = get_artifact_service()

    def should_code(self, user_message: str) -> bool:
        """Check if user is requesting a coding/development task."""
        if not self.intent_classifier.classify(user_message, "auto").use_agent:
            return False

        lower = user_message.lower()

        # Console/browser tasks
        if "console" in lower and ("log" in lower or "print" in lower or "browser" in lower):
            return True
        if "browser" in lower and ("log" in lower or "print" in lower or "console" in lower):
            return True

        # Development task triggers
        dev_triggers = [
            # Modification requests
            "change the", "change port", "change config", "update the", "modify the",
            "fix the", "debug", "bug in", "error in", "issue with",

            # Creation requests
            "create a", "create an", "create new", "add a", "add an", "add new",
            "implement a", "implement an", "write a", "write an", "generate a",

            # File operations - CRITICAL for file creation
            "edit file", "update file", "create file", "new file", "delete file",
            "write a new file", "write a file", "create a new file", "make a file",
            "save a file", "save to file",

            # Code-specific
            "add endpoint", "add route", "add function", "add class",
            "create endpoint", "create route", "create function", "create class",

            # Configuration
            "set port", "set config", "configure", "change setting",

            # Task requests
            "i need you to", "can you create", "can you change", "can you fix",
            "please create", "please fix", "please change", "please update",

            # Development actions
            "refactor", "optimize", "improve the", "enhance the",

            # Encryption/security
            "encrypt", "decrypt", "security", "authentication", "authorization",

            # Multi-step tasks
            "then", "next", "after that", "first", "second", "third",
        ]

        if any(trigger in lower for trigger in dev_triggers):
            # Exclude if it's clearly not about code
            exclude = ["create image", "create picture", "fix me a drink", "change clothes"]
            if not any(ex in lower for ex in exclude):
                return True

        # Check for specific technical patterns
        tech_patterns = [
            r"(?:port|PORT)\s*(?:=|:|from)?\s*\d+",  # Port numbers
            r"(?:endpoint|route)\s*['\"]/api/",  # API endpoints
            r"(?:function|method|class)\s+\w+",  # Code elements
            r"(?:file|module)\s+\w+\.py",  # Python files
            r"(?:create|make|build)\s+(?:a|an)?\s*\w+\s+(?:file|tool|utility|service|component)",
            r"write\s+(?:a|new|the)?\s*(?:file\s+)?(?:called\s+)?[\w.-]+",  # "write a file called..."
            r"create\s+(?:a|new|the)?\s*(?:file\s+)?(?:called\s+)?[\w.-]+",  # "create a file called..."
        ]

        for pattern in tech_patterns:
            if re.search(pattern, user_message):
                return True

        return False

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        """Execute autonomous coding task with intelligent context understanding."""
        # CRITICAL: Always execute coding tasks, don't let LLM describe them
        if session_id is None:
            # Create a default session ID if none provided
            session_id = "default-session"

        if not self.should_code(user_message):
            return OrchestratorResult()

        try:
            # Check if task has multiple steps (needs planning)
            has_multiple_steps = self._has_multiple_steps(user_message)

            if has_multiple_steps:
                # Use planning agent for multi-step tasks
                print(f"🔧 [CodingAgent] Multi-step task detected, using planning agent...")
                project_context = await self._load_project_context(session_id)
                plan = await self.planning_agent.execute_task_with_plan(
                    user_message,
                    project_context=project_context,
                )

                # Format the plan as a detailed log
                log_output = plan.to_log_string()
                print(f"✅ [CodingAgent] Plan executed: {plan.completed_steps}/{plan.total_steps} steps")

                if plan.status.value == "completed":
                    return OrchestratorResult(
                        direct_reply=f"✅ **Task Complete**\n\n{log_output}",
                        used_agents=[self.name],
                        render_blocks=self._build_render_blocks(
                            plan.task,
                            [
                                {
                                    "path": step.target,
                                    "summary": step.output[:180] if step.output else step.description,
                                }
                                for step in plan.steps
                                if step.action_type in {"create_file", "edit_file", "write_file"} or "/" in step.target or "." in step.target
                            ],
                            plan.status.value,
                            plan_steps=[
                                {
                                    "step_number": step.step_number,
                                    "description": step.description,
                                    "status": step.status.value,
                                    "target": step.target,
                                    "output": step.output[:240] if step.output else "",
                                    "error": step.error,
                                }
                                for step in plan.steps
                            ],
                        ),
                    )
                else:
                    return OrchestratorResult(
                        direct_reply=f"⚠️ **Task Status**\n\n{log_output}",
                        used_agents=[self.name],
                        render_blocks=self._build_render_blocks(
                            plan.task,
                            [],
                            plan.status.value,
                            plan_steps=[
                                {
                                    "step_number": step.step_number,
                                    "description": step.description,
                                    "status": step.status.value,
                                    "target": step.target,
                                    "output": step.output[:240] if step.output else "",
                                    "error": step.error,
                                }
                                for step in plan.steps
                            ],
                        ),
                    )
            else:
                # Use intelligent coding agent for single-step tasks
                print(f"🔧 [CodingAgent] Single-step task, using intelligent coding agent...")
                await self.coding_agent.initialize()
                progress = await self.coding_agent.execute_task(
                    user_message,
                    project_context=await self._load_project_context(session_id),
                )

                # Format the progress as a detailed log
                log_output = progress.to_log_string()
                print(f"✅ [CodingAgent] Task completed: {progress.message}")

                if progress.overall_status == "completed":
                    return OrchestratorResult(
                        direct_reply=f"✅ **Development Task Complete**\n\n{log_output}",
                        used_agents=[self.name],
                        render_blocks=self._build_render_blocks(
                            progress.task_description,
                            [
                                {
                                    "path": action.target,
                                    "summary": action.description,
                                    "diff": action.diff,
                                }
                                for action in progress.actions
                                if action.action_type in {"write", "edit", "repair"} and action.target
                            ],
                            progress.overall_status,
                        ),
                    )
                else:
                    return OrchestratorResult(
                        direct_reply=f"⚠️ **Task Status**\n\n{log_output}",
                        used_agents=[self.name],
                        render_blocks=self._build_render_blocks(
                            progress.task_description,
                            [
                                {
                                    "path": action.target,
                                    "summary": action.description,
                                    "diff": action.diff,
                                }
                                for action in progress.actions
                                if action.action_type in {"write", "edit", "repair"} and action.target
                            ],
                            progress.overall_status,
                        ),
                    )

        except Exception as e:
            import traceback
            error_msg = f"❌ **Coding Agent Error**\n\n```\n{str(e)}\n```\n\nStack trace:\n```\n{traceback.format_exc()}\n```"
            print(f"❌ [CodingAgent] Error: {e}")
            return OrchestratorResult(
                direct_reply=error_msg,
                used_agents=[self.name],
            )

    async def _load_project_context(self, session_id: str | None) -> dict:
        if not session_id:
            return {}
        artifacts = await self.artifacts.list_artifacts(session_id=session_id, kinds=["archive"], limit=1)
        if not artifacts:
            return {}
        return artifacts[0].get("metadata", {})

    def _build_render_blocks(
        self,
        task: str,
        files: list[dict],
        status: str,
        plan_steps: list[dict] | None = None,
    ) -> list[dict]:
        highlights = [f["path"] for f in files[:6] if f.get("path")]
        blocks = [
            {
                "type": "report",
                "payload": {
                    "title": "Coding task summary",
                    "summary": f"Task status: {status}.",
                    "highlights": [task, *highlights] if highlights else [task],
                },
            }
        ]
        if plan_steps:
            blocks.append(
                {
                    "type": "plan_result",
                    "payload": {
                        "title": "Execution plan",
                        "status": status,
                        "steps": plan_steps[:12],
                    },
                }
            )
        if files:
            blocks.append(
                {
                    "type": "file_result",
                    "payload": {
                        "title": "Files touched by coding agent",
                        "files": files[:8],
                    },
                }
            )
        return blocks

    def _has_multiple_steps(self, task: str) -> bool:
        """Check if a task has multiple steps that require planning."""
        task_lower = task.lower()
        
        # Check for step indicators
        step_indicators = [
            r"\bthen\b",
            r"\band then\b",
            r"\bnext\b",
            r"\bfirst\b.*?\bsecond\b",
            r"\d+\.\s",  # "1. do this 2. do that"
            r"\bstep\s+\d+\b",
        ]
        
        for pattern in step_indicators:
            if re.search(pattern, task_lower):
                return True
        
        # Check for multiple actions
        action_count = 0
        actions = ["create", "update", "edit", "delete", "show", "run", "execute"]
        for action in actions:
            if action in task_lower:
                action_count += 1
        
        return action_count >= 2


class VideoGenerationAgent:
    name = "video-generation-agent"

    def __init__(self, video_service: VideoGenService) -> None:
        self.video_service = video_service

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        """Handle video generation requests."""
        if session_id is None:
            return OrchestratorResult()
            
        if not self.video_service.should_generate_video(user_message):
            return OrchestratorResult()
        
        # Video generation requested but capability may not be available
        # Return context to inform the LLM about the situation
        return OrchestratorResult(
            tool_context=[
                "Video generation was requested. Note: Video generation capability requires special models.",
                "If capability is not developed, inform the user and offer to develop it.",
            ],
            used_agents=[self.name],
        )


class ImageGenerationAgent:
    name = "image-generation-agent"

    def __init__(self) -> None:
        # Check if capability is available
        try:
            from app.services.capability_registry import get_capability_registry
            registry = get_capability_registry()
            self.capability_available = registry.has_capability("image_generation")
        except Exception:
            self.capability_available = IMAGE_GEN_AVAILABLE

    def should_generate(self, user_message: str) -> bool:
        """Check if user is requesting image generation."""
        if not self.capability_available:
            return False

        lower = user_message.lower()

        # FIRST: Exclude search/find requests (these should go to ImageIntelAgent for web search)
        search_indicators = [
            "search for", "find", "look for", "find images", "find pictures",
            "search images", "search pictures", "search on the internet",
            "show me pictures", "show me images", "on the internet",
        ]
        if any(indicator in lower for indicator in search_indicators):
            return False

        # SECOND: Exclude coding/development tasks (these should go to CodingAgent)
        coding_indicators = [
            "file", "component", "react", "function", "class", "api",
            "endpoint", "route", "module", "import", "export", "frontend",
            "backend", "code", "script", "program", "create a file",
            "create file", "new file", "update file", "edit file",
            "create component", "create react", "create api",
            "create endpoint", "create function", "create class",
            "then", "next", "after that",  # Multi-step tasks
            ".jsx", ".tsx", ".js", ".ts", ".py",  # File extensions
        ]
        
        # If ANY coding indicator is present, NOT an image request
        if any(indicator in lower for indicator in coding_indicators):
            return False

        # Image generation triggers (MUST be explicit about images)
        image_triggers = [
            # Explicit image requests
            "generate image", "generate picture", "generate photo", "generate art",
            "create image", "create picture", "create photo", "create art",
            "draw me", "draw a picture", "draw an image",
            "make an image", "make a picture", "make art",
            "show me a picture", "show me an image", "show me a photo",
            "image of", "picture of", "photo of",
            "generate an image", "generate a picture",
            # Visual content requests
            "illustration", "illustrate", "visualize", "visualization",
            "logo", "icon", "banner", "poster",
        ]

        # Check for explicit image triggers
        if any(trigger in lower for trigger in image_triggers):
            return True

        # Check for descriptive image requests (MUST have visual keywords + strong generation intent)
        visual_keywords = [
            "cat", "dog", "sunset", "mountain", "ocean", "forest",
            "city", "building", "person", "animal", "flower", "tree",
            "car", "house", "food", "drink", "landscape", "portrait",
            "abstract", "colorful", "beautiful", "scenic", "nature",
            "space", "planet", "galaxy", "star", "moon", "sun",
        ]
        
        # Only match if it's clearly about visual content AND has strong generation intent
        if any(word in lower for word in visual_keywords):
            # Must have a STRONG creation verb (not just "show" or "picture")
            generation_verbs = ["generate", "create", "draw", "make"]
            if any(verb in lower for verb in generation_verbs):
                return True

        return False

    async def run(self, session_id: str | None, user_message: str) -> OrchestratorResult:
        """Handle image generation using the developed capability."""
        if session_id is None:
            return OrchestratorResult()
        
        if not self.should_generate(user_message):
            return OrchestratorResult()
        
        # Extract prompt from user message
        prompt = self._extract_prompt(user_message)
        
        try:
            # Call the actual image generation service
            if generate_image_service:
                image = await generate_image_service(
                    prompt=prompt,
                    width=512,
                    height=512,
                )
                
                if image:
                    # Convert to base64 for display
                    import base64
                    import io

                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    # Create structured image data for frontend
                    # Format: [IMAGE_DATA:base64|width:512|height:512|prompt:text]
                    image_data_marker = f"[IMAGE_DATA:{image_base64}|width:{image.width}|height:{image.height}|prompt:{prompt}]"

                    return OrchestratorResult(
                        direct_reply=f"✅ **Generated image for:** {prompt}\n\n{image_data_marker}\n\n*Generated using FLUX.1 model*",
                        used_agents=[self.name],
                    )
        except Exception as e:
            return OrchestratorResult(
                tool_context=[f"Image generation failed: {str(e)}"],
                used_agents=[self.name],
            )
        
        return OrchestratorResult()
    
    def _extract_prompt(self, user_message: str) -> str:
        """Extract the image generation prompt from user message."""
        import re
        
        lower = user_message.lower()
        
        # Remove common prefixes to get the actual subject
        prefixes_to_remove = [
            r"^(?:please|can you|could you|will you|would you)\s+",
            r"^(?:generate|create|draw|make|show me|i want|i need|i'd like)\s+",
            r"^(?:an?|the)\s+",
            r"^(?:image|picture|photo|art)\s+(?:of|for)?\s*",
            r"^(?:to see|seeing)\s+",
        ]
        
        cleaned = user_message.strip()
        for prefix in prefixes_to_remove:
            cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = " ".join(cleaned.split())
        
        # If we got something meaningful, use it
        if cleaned and len(cleaned) > 2:
            return cleaned
        
        # Try pattern matching for specific structures
        patterns = [
            # "generate/create/draw/make [a/an/the] X" or "generate/create/draw/make X"
            r"(?:generate|create|draw|make)\s+(?:an?|the)?\s*(.+?)(?:\.|!|$)",
            # "i want/need/like [to see] X"
            r"(?:i want|i need|i'd like)(?:\s+to\s+see)?\s+(?:an?|the)?\s*(.+?)(?:\.|!|$)",
            # "show me X"
            r"show\s+me\s+(?:an?|the)?\s*(.+?)(?:\.|!|$)",
            # "image/picture/photo of X"
            r"(?:image|picture|photo)\s+of\s+(.+?)(?:\.|!|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                prompt = match.group(1).strip()
                # Clean up the prompt
                prompt = " ".join(prompt.split())
                if prompt and len(prompt) > 2:
                    # Capitalize first letter
                    return prompt.capitalize()
        
        # Fallback: use the whole message, cleaned up
        return user_message.strip()


class MultiAgentOrchestrator:
    """Coordinate specialized sub-agents before the final language-model response."""

    def __init__(
        self,
        toolbox: AgentToolbox,
        document_service: DocumentService,
        search_service: SearchService,
        sandbox_service: SandboxService,
        url_content_service: UrlContentService,
        image_intel_service: ImageIntelService,
        video_service: VideoGenService,
    ) -> None:
        self.utility_agent = UtilityAgent(toolbox)
        self.document_agent = DocumentAgent(document_service)
        self.url_agent = UrlAgent(url_content_service)
        self.image_intel_agent = ImageIntelAgent(image_intel_service)
        self.image_generation_agent = ImageGenerationAgent()
        self.video_generation_agent = VideoGenerationAgent(video_service)
        self.research_agent = ResearchAgent(search_service)
        self.execution_agent = ExecutionAgent(sandbox_service)
        self.capability_agent = CapabilityAgent()
        self.coding_agent = CodingAgent()

    async def run(
        self,
        user_message: str,
        session_id: str | None,
        attachments: list[ChatAttachment],
    ) -> OrchestratorResult:
        aggregate = OrchestratorResult()

        utility = await self.utility_agent.run(user_message)
        if utility.direct_reply is not None:
            return utility
        aggregate.tool_context.extend(utility.tool_context)
        aggregate.used_agents.extend(utility.used_agents)

        documents = await self.document_agent.run(session_id, attachments, user_message)
        aggregate.tool_context.extend(documents.tool_context)
        aggregate.used_agents.extend(documents.used_agents)

        urls = await self.url_agent.run(session_id, user_message)
        aggregate.tool_context.extend(urls.tool_context)
        aggregate.used_agents.extend(urls.used_agents)

        images = await self.image_intel_agent.run(session_id, user_message, attachments)
        aggregate.tool_context.extend(images.tool_context)
        aggregate.used_agents.extend(images.used_agents)
        aggregate.image_logs.extend(images.image_logs)
        aggregate.render_blocks.extend(images.render_blocks)

        capability = await self.capability_agent.run(session_id, user_message)
        if capability.direct_reply is not None:
            return capability
        aggregate.tool_context.extend(capability.tool_context)
        aggregate.used_agents.extend(capability.used_agents)
        aggregate.render_blocks.extend(capability.render_blocks)

        # ⚡ CRITICAL: Check for coding/development tasks FIRST (HIGHEST PRIORITY)
        # This prevents coding requests from being misinterpreted as image requests
        coding = await self.coding_agent.run(session_id, user_message)
        if coding.direct_reply is not None:
            return coding  # Return immediately if coding agent handled it
        aggregate.tool_context.extend(coding.tool_context)
        aggregate.used_agents.extend(coding.used_agents)

        # Only check for image generation if NOT a coding task
        gen_image = await self.image_generation_agent.run(session_id, user_message)
        if gen_image.direct_reply is not None:
            return gen_image
        aggregate.tool_context.extend(gen_image.tool_context)
        aggregate.used_agents.extend(gen_image.used_agents)

        # Check for video generation requests
        video = await self.video_generation_agent.run(session_id, user_message)
        aggregate.tool_context.extend(video.tool_context)
        aggregate.used_agents.extend(video.used_agents)

        research = await self.research_agent.run(session_id, user_message)
        aggregate.tool_context.extend(research.tool_context)
        aggregate.used_agents.extend(research.used_agents)
        aggregate.search_logs.extend(research.search_logs)
        aggregate.render_blocks.extend(research.render_blocks)

        execution = await self.execution_agent.run(session_id, user_message)
        aggregate.tool_context.extend(execution.tool_context)
        aggregate.used_agents.extend(execution.used_agents)
        aggregate.render_blocks.extend(execution.render_blocks)

        aggregate.used_agents = list(dict.fromkeys(aggregate.used_agents))
        return aggregate


def get_multi_agent_orchestrator(toolbox: AgentToolbox) -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator(
        toolbox=toolbox,
        document_service=get_document_service(),
        search_service=get_search_service(),
        sandbox_service=get_sandbox_service(),
        url_content_service=get_url_content_service(),
        image_intel_service=get_image_intel_service(),
        video_service=get_video_gen_service(),
    )
