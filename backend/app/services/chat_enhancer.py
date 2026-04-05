"""
Enhanced chat service with improved error handling, retry logic, and streaming optimization.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for streaming behavior."""
    chunk_size: int = 50  # Batch this many tokens before sending
    flush_interval: float = 0.1  # Flush after this many seconds even if buffer not full
    max_retries: int = 3
    retry_delay: float = 0.5
    timeout: float = 30.0


class ChatEnhancer:
    """Enhances chat service with better error handling and streaming optimization."""

    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config or StreamConfig()
        self.logger = logger

    async def stream_with_retry(
        self,
        stream_fn,
        base_stream: AsyncIterator[str],
        max_retries: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Wrap a stream with retry logic and error handling.
        
        Args:
            stream_fn: Function that returns a new stream on retry
            base_stream: The initial stream to use
            max_retries: Override default max retries
        """
        retries = 0
        max_attempts = (max_retries or self.config.max_retries) + 1
        current_stream = base_stream
        buffer = ""
        last_flush = time.time()

        while retries < max_attempts:
            try:
                async for chunk in current_stream:
                    try:
                        buffer += chunk
                        current_time = time.time()
                        should_flush = (
                            len(buffer) >= self.config.chunk_size or
                            (current_time - last_flush) >= self.config.flush_interval
                        )

                        if should_flush and buffer:
                            yield buffer
                            buffer = ""
                            last_flush = time.time()
                    except Exception as chunk_err:
                        self.logger.error(f"Error processing chunk: {chunk_err}")
                        if buffer:
                            yield buffer
                            buffer = ""
                        raise

                # Flush any remaining buffer
                if buffer:
                    yield buffer

                return  # Success

            except asyncio.TimeoutError:
                self.logger.warning(f"Stream timeout (attempt {retries + 1}/{max_attempts})")
                retries += 1
                if retries < max_attempts:
                    await asyncio.sleep(self.config.retry_delay * (retries ** 1.5))
                    current_stream = await stream_fn()
                else:
                    raise

            except asyncio.CancelledError:
                self.logger.info("Stream cancelled by client")
                if buffer:
                    yield buffer
                raise

            except Exception as e:
                self.logger.error(f"Stream error (attempt {retries + 1}/{max_attempts}): {e}")
                retries += 1
                if retries < max_attempts:
                    await asyncio.sleep(self.config.retry_delay * retries)
                    try:
                        current_stream = await stream_fn()
                    except Exception as retry_err:
                        self.logger.error(f"Failed to create retry stream: {retry_err}")
                        raise
                else:
                    raise

    async def batch_stream_chunks(
        self,
        stream: AsyncIterator[str],
        buffer_size: int = 50,
        flush_interval: float = 0.1,
    ) -> AsyncIterator[str]:
        """
        Batch small chunks from stream for more efficient rendering.
        
        Args:
            stream: Input stream
            buffer_size: Number of tokens to batch before sending
            flush_interval: Max time to wait before sending partial buffer
        """
        buffer = ""
        last_flush = time.time()

        try:
            async for chunk in stream:
                buffer += chunk
                current_time = time.time()

                if (
                    len(buffer) >= buffer_size or
                    (current_time - last_flush) >= flush_interval
                ):
                    if buffer:
                        yield buffer
                        buffer = ""
                        last_flush = time.time()

            # Final flush
            if buffer:
                yield buffer

        except Exception as e:
            self.logger.error(f"Error in batch_stream_chunks: {e}")
            if buffer:
                yield buffer
            raise

    async def optimize_conversation_context(
        self,
        messages: list,
        max_context_tokens: int = 4000,
        summary_threshold: int = 10,
    ) -> list:
        """
        Optimize conversation context to fit within token limits.
        
        Strategy:
        1. Keep the last N messages (recent context)
        2. Summarize older messages if needed
        3. Preserve any important semantic markers
        """
        if len(messages) <= summary_threshold:
            return messages

        recent_messages = messages[-summary_threshold:]
        older_messages = messages[:-summary_threshold]

        # For now, keep recent messages and drop oldest
        # In production, would implement smart summarization
        optimized = recent_messages

        self.logger.info(
            f"Optimized context: {len(messages)} → {len(optimized)} messages"
        )
        return optimized

    async def handle_context_window_error(
        self,
        original_error: Exception,
        current_context_size: int,
    ) -> dict:
        """
        Handle context window exceeded errors with strategy.
        
        Returns:
            Dict with 'action' and 'data' keys for error recovery
        """
        if "context" not in str(original_error).lower():
            return {"action": "propagate", "error": original_error}

        return {
            "action": "reduce_context",
            "reduction_percent": 20,
            "reason": "Context window exceeded",
        }


class AdaptiveStreamController:
    """Controls streaming behavior based on network and performance metrics."""

    def __init__(self):
        self.chunk_timings: list[float] = []
        self.error_count = 0
        self.max_chunk_size = 100
        self.min_chunk_size = 10

    def update_performance(self, processing_time: float):
        """Track performance to adapt streaming."""
        self.chunk_timings.append(processing_time)
        if len(self.chunk_timings) > 100:
            self.chunk_timings.pop(0)

    def get_optimal_chunk_size(self) -> int:
        """Calculate optimal chunk size based on performance."""
        if not self.chunk_timings:
            return 50

        avg_time = sum(self.chunk_timings[-10:]) / min(10, len(self.chunk_timings))

        # If average time is high, reduce chunk size for more responsive UI
        if avg_time > 0.2:
            return max(self.min_chunk_size, int(50 * 0.8))
        elif avg_time < 0.05:
            return min(self.max_chunk_size, int(50 * 1.2))
        else:
            return 50

    def record_error(self):
        """Record an error for adaptive behavior."""
        self.error_count += 1
        if self.error_count > 5:
            # Back off if too many errors
            self.max_chunk_size = max(10, int(self.max_chunk_size * 0.8))


class ContextWindowManager:
    """Manages conversation context to stay within token limits."""

    def __init__(self, max_tokens: int = 4000, reserve_tokens: int = 500):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters."""
        return len(text) // 4

    def can_fit_message(self, message: str) -> bool:
        """Check if message fits in context."""
        tokens = self.estimate_tokens(message)
        return tokens <= self.available_tokens

    def update_available_tokens(self, used_tokens: int):
        """Update available tokens after using some."""
        self.available_tokens = max(0, self.available_tokens - used_tokens)

    def has_space(self, estimated_tokens: int = 100) -> bool:
        """Check if there's space for more context."""
        return self.available_tokens >= estimated_tokens


async def create_enhanced_stream(
    stream_fn,
    config: Optional[StreamConfig] = None,
    enable_batching: bool = True,
) -> AsyncIterator[str]:
    """
    Create an enhanced stream with automatic batching and retry logic.
    
    Args:
        stream_fn: Async function that returns a stream
        config: StreamConfig for customization
        enable_batching: Whether to batch chunks
    """
    enhancer = ChatEnhancer(config)
    base_stream = await stream_fn()

    if enable_batching:
        return enhancer.batch_stream_chunks(
            await enhancer.stream_with_retry(stream_fn, base_stream)
        )
    else:
        return enhancer.stream_with_retry(stream_fn, base_stream)
