from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.app.schemas.chat import ChatAttachment, ImageIntelLog, WebSearchLog
from backend.app.services.documents import DocumentService, get_document_service
from backend.app.services.image_intel import ImageIntelService, get_image_intel_service
from backend.app.services.sandbox import SandboxService, get_sandbox_service
from backend.app.services.search import SearchService, get_search_service
from backend.app.services.tools import AgentToolbox
from backend.app.services.url_content import UrlContentService, get_url_content_service
from backend.app.services.video_intel import VideoGenService, get_video_gen_service

# Try to import image generation service (may not exist yet)
try:
    from backend.app.services.image_generation import generate_image as generate_image_service
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
            from backend.app.services.capability_registry import get_capability_registry
            registry = get_capability_registry()
            self.capability_available = registry.has_capability("image_generation")
        except Exception:
            self.capability_available = IMAGE_GEN_AVAILABLE

    def should_generate(self, user_message: str) -> bool:
        """Check if user is requesting image generation."""
        if not self.capability_available:
            return False
        
        lower = user_message.lower()
        
        # Check for image generation requests
        keywords = [
            "generate image",
            "generate picture",
            "create image",
            "create picture",
            "draw me",
            "draw a",
            "make an image",
            "make a picture",
            "random image",
            "random picture",
            "show me the generated picture",
            "show me the picture",
            "show me the image",
        ]
        
        return any(kw in lower for kw in keywords)

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
        lower = user_message.lower()
        
        # Common patterns
        patterns = [
            r"generate (?:a|an|the|random)?\s*(?:image|picture|photo)?\s*(?:of|for)?\s*(.+?)(?:\.|!|$)",
            r"create (?:a|an|the)?\s*(?:image|picture|photo)?\s*(?:of|for)?\s*(.+?)(?:\.|!|$)",
            r"draw (?:me|a|an|the)?\s*(.+?)(?:\.|!|$)",
            r"make (?:me|a|an|the)?\s*(?:image|picture|photo)?\s*(?:of|for)?\s*(.+?)(?:\.|!|$)",
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                prompt = match.group(1).strip()
                if prompt and len(prompt) > 2:
                    return prompt
        
        # Fallback: use the whole message
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

        # Check for image generation requests (after capability development)
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

        execution = await self.execution_agent.run(session_id, user_message)
        aggregate.tool_context.extend(execution.tool_context)
        aggregate.used_agents.extend(execution.used_agents)

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
