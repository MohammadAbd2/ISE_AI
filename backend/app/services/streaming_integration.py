"""
Integration helpers for using chat enhancements with existing routes.
Shows how to integrate ChatEnhancer and EnhancedAgentOrchestrator into the API.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

from backend.app.services.chat_enhancer import ChatEnhancer, StreamConfig
from backend.app.services.enhanced_agent import EnhancedAgentOrchestrator
from backend.app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)


class StreamingResponseManager:
    """Manages streaming responses with enhancements."""

    def __init__(self):
        self.enhancer = ChatEnhancer(StreamConfig())
        self.orchestrator = EnhancedAgentOrchestrator()

    async def enhanced_stream_response(
        self,
        base_stream_fn,
        payload: ChatRequest,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Wrap a stream function with enhancements.

        Usage:
            manager = StreamingResponseManager()
            
            async def get_base_stream():
                return await service.stream_reply(...)
            
            enhanced_stream = manager.enhanced_stream_response(
                get_base_stream, 
                payload, 
                session_id
            )
            
            async for chunk in enhanced_stream:
                yield chunk

        Args:
            base_stream_fn: Async function that returns a stream
            payload: Chat request payload
            session_id: Session ID for logging/memory
        """
        try:
            # Get the initial stream
            base_stream = await base_stream_fn()

            # Wrap with enhancement
            async for chunk in self.enhancer.stream_with_retry(
                base_stream_fn, base_stream
            ):
                yield chunk

        except asyncio.TimeoutError:
            logger.error("Stream timeout")
            yield "[Stream timeout - please try again]"

        except asyncio.CancelledError:
            logger.info("Stream cancelled by client")
            raise

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"[Error: {str(e)[:100]}]"

    async def analyze_and_decompose_task(
        self, message: str, context: Optional[str] = None
    ) -> dict:
        """
        Analyze task and optionally decompose it.

        Usage:
            manager = StreamingResponseManager()
            
            analysis = await manager.analyze_and_decompose_task(
                "Build a REST API with authentication",
                context="Python FastAPI project"
            )
            
            if analysis['complexity'] == 'complex':
                # Use decomposed subtasks
                for subtask in analysis['subtasks']:
                    print(f"Task: {subtask['description']}")

        Args:
            message: The user message to analyze
            context: Optional context about the project/task

        Returns:
            Dict with task analysis and decomposition
        """
        try:
            # Analyze task
            analysis = await self.orchestrator.analyzer.analyze_task(message)

            result = {
                "task": message,
                "complexity": analysis.complexity,
                "estimated_steps": analysis.estimated_steps,
                "suggested_agents": analysis.suggested_agents,
                "requires_verification": analysis.requires_verification,
                "reasoning": analysis.reasoning,
            }

            # Decompose if complex
            if analysis.complexity == "complex":
                decomposition = await self.orchestrator.decomposer.decompose(
                    message, analysis
                )
                result["subtasks"] = [
                    {
                        "id": task["id"],
                        "description": task["description"],
                        "agent": task["agent"],
                        "priority": task["priority"],
                    }
                    for task in decomposition.subtasks
                ]
                result["orchestration_strategy"] = (
                    decomposition.orchestration_strategy
                )
                result["verification_points"] = decomposition.verification_points

            return result

        except Exception as e:
            logger.error(f"Task analysis error: {e}")
            return {
                "task": message,
                "error": str(e),
                "complexity": "moderate",  # Default to moderate on error
            }

    def get_reasoning_enhancement(
        self, task_complexity: str
    ) -> str:
        """
        Get a reasoning prompt enhancement based on task complexity.

        Usage:
            manager = StreamingResponseManager()
            
            prompt = manager.get_reasoning_enhancement("complex")
            full_prompt = f"{user_message}\\n\\n{prompt}"

        Args:
            task_complexity: one of 'simple', 'moderate', 'complex'

        Returns:
            A reasoning enhancement prompt
        """
        return self.orchestrator.suggest_reasoning_approach(task_complexity)

    def record_interaction_feedback(
        self,
        interaction_id: str,
        feedback_type: str,
        content: str,
        rating: Optional[int] = None,
    ):
        """
        Record feedback about an interaction for learning.

        Usage:
            manager = StreamingResponseManager()
            
            manager.record_interaction_feedback(
                interaction_id="msg_123",
                feedback_type="positive",
                content="Response was very helpful",
                rating=5
            )

        Args:
            interaction_id: Unique ID for the interaction
            feedback_type: 'positive', 'negative', or 'suggestion'
            content: Feedback content
            rating: Optional 1-5 rating
        """
        self.orchestrator.feedback.collect_feedback(
            interaction_id, feedback_type, content, rating
        )
        logger.info(f"Feedback recorded: {feedback_type}")

    def get_improvement_suggestions(self) -> list[str]:
        """
        Get suggestions for system improvements based on feedback.

        Usage:
            manager = StreamingResponseManager()
            
            suggestions = manager.get_improvement_suggestions()
            for suggestion in suggestions:
                print(suggestion)

        Returns:
            List of improvement suggestions
        """
        return self.orchestrator.feedback.get_improvement_suggestions()

    def remember_context(self, key: str, value, context: str = "execution"):
        """
        Store information in agent short-term memory.

        Usage:
            manager = StreamingResponseManager()
            
            manager.remember_context("api_key", "sk_xxx", context="authentication")
            api_key = manager.recall_context("api_key")

        Args:
            key: Memory key
            value: Value to remember
            context: Context label
        """
        self.orchestrator.memory.remember(key, value, context)
        logger.debug(f"Remembered {key} in context {context}")

    def recall_context(self, key: str):
        """
        Retrieve information from agent short-term memory.

        Args:
            key: Memory key to retrieve

        Returns:
            The remembered value or None
        """
        return self.orchestrator.memory.recall(key)

    def clear_session_memory(self):
        """Clear all session memory."""
        self.orchestrator.memory.clear()
        logger.info("Session memory cleared")


# Global instance
_streaming_manager: Optional[StreamingResponseManager] = None


def get_streaming_manager() -> StreamingResponseManager:
    """Get or create the global streaming manager."""
    global _streaming_manager
    if _streaming_manager is None:
        _streaming_manager = StreamingResponseManager()
    return _streaming_manager


# Example of how to use in routes.py:
"""
from backend.app.services.streaming_integration import get_streaming_manager

@router.post("/api/chat/stream")
async def stream_chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    history: HistoryService = Depends(get_history_service),
    profile: ProfileService = Depends(get_profile_service),
) -> StreamingResponse:
    agent = ChatAgent(
        service=service,
        profile_service=profile,
        history_service=history,
    )
    
    manager = get_streaming_manager()
    
    # Analyze task first
    analysis = await manager.analyze_and_decompose_task(payload.message)
    
    # Use enhanced streaming
    async def get_stream():
        reply_stream, model, search_logs, image_logs, render_blocks = (
            await agent.stream_response(
                payload,
                conversation=conversation,
                session_id=session["id"],
            )
        )
        return reply_stream
    
    async def event_stream():
        chunks = []
        async for chunk in manager.enhanced_stream_response(
            get_stream, payload, session["id"]
        ):
            chunks.append(chunk)
            yield json.dumps({"type": "text", "content": chunk})
        
        # Store completion for feedback
        full_response = "".join(chunks)
        await history.append_message(
            session["id"],
            "assistant",
            full_response,
            model,
        )
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
"""
