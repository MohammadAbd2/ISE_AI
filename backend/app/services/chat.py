from __future__ import annotations

from functools import lru_cache
from typing import AsyncIterator

from app.core.config import settings
from app.models.message import Message
from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider
from app.services.model_manager import get_model_manager
from app.services.system_prompt import SYSTEM_PROMPT


class ChatService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.model_manager = get_model_manager()

    def _build_grounding_instruction(self, has_tool_context: bool) -> str:
        base_rules = [
            "For current, latest, recent, live, or today's information, never rely on model memory alone.",
            "If tool results are present, treat them as the source of truth for this reply.",
            "Never claim that you searched the web unless tool results actually contain web search results.",
            "Never invent prices, dates, source names, article counts, command outputs, or test results.",
            "When a coding task was executed, describe what actually changed and what verification really ran.",
            "Prefer short paragraphs with clear technical substance.",
            "If the retrieved sources do not contain the exact answer, say that you could not verify it.",
        ]
        if not has_tool_context:
            return "Grounding policy:\n- " + "\n- ".join(base_rules)
        tool_rules = [
            (
                "When tool results include web search results, answer from those results first and keep the answer grounded in them. "
                "If a source includes both a snippet and a longer page excerpt, prefer the page excerpt for factual detail when it is clearer."
            ),
            "For web-grounded answers, mention that you checked the web and cite source domains or titles plainly.",
            "If sources conflict, say that the sources disagree instead of choosing a fabricated value.",
            "If the web search returned no results, say exactly that and do not pretend otherwise.",
            (
                "When tool results include image search hits or generated media, reference them clearly and say whether they were searched or generated."
            ),
        ]
        return "Grounding policy:\n- " + "\n- ".join(base_rules + tool_rules)

    def _build_effort_instruction(self, effort: str) -> str:
        instructions = {
            "low": "Reason with low effort. Prefer a fast and concise answer.",
            "medium": "Reason with medium effort. Balance speed, clarity, and completeness.",
            "high": "Reason with high effort. Be deliberate, verify assumptions, and prefer robust implementation over speed.",
        }
        return instructions.get(effort, instructions["medium"])

    def _build_messages(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        effort: str = "medium",
    ) -> list[Message]:
        tool_context = tool_context or []
        max_context_chars = settings.max_tool_context_chars
        tool_context_str = ""

        if tool_context:
            accumulated_len = 0
            limited_context: list[str] = []
            for ctx in tool_context:
                if accumulated_len + len(ctx) + 2 <= max_context_chars:
                    limited_context.append(ctx)
                    accumulated_len += len(ctx) + 2
                else:
                    remaining = max_context_chars - accumulated_len
                    if remaining > 600:
                        limited_context.append(ctx[:remaining])
                    break
            tool_context_str = "\n\n".join(limited_context)

        system_parts = [
            SYSTEM_PROMPT,
            settings.system_prompt,
            self._build_effort_instruction(effort),
            (
                "You can use long-term memory across chats. If a fact comes from long-term memory, say that clearly. "
                "If you do not know something, say so plainly."
            ),
            self._build_grounding_instruction(bool(tool_context)),
        ]
        if custom_instructions.strip():
            system_parts.append(f"Custom instructions:\n{custom_instructions.strip()}")
        memory_items = memory_items or []
        if memory_items:
            system_parts.append("Long-term memory:\n" + "\n".join(f"- {item}" for item in memory_items))
        if memory_note.strip():
            system_parts.append(memory_note.strip())
        if tool_context_str:
            system_parts.append(
                "Tool results:\nUse these results as factual grounding. Do not override them with unsupported guesses.\n\n"
                + tool_context_str
            )
        messages = [Message(role="system", content="\n\n".join(system_parts))]
        messages.extend(conversation)
        messages.append(Message(role="user", content=user_message))
        return messages

    async def _available_models_safe(self) -> list[str]:
        try:
            return await self.provider.list_models()
        except Exception:
            return []

    async def generate_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        model: str | None = None,
        effort: str = "medium",
    ) -> tuple[str, str]:
        available_models = await self._available_models_safe()
        selection = self.model_manager.select_model(
            requested_model=model,
            user_message=user_message,
            effort=effort,
            available_models=available_models,
        )
        messages = self._build_messages(
            user_message=user_message,
            conversation=conversation,
            custom_instructions=custom_instructions,
            memory_items=memory_items,
            memory_note=memory_note,
            tool_context=tool_context,
            effort=effort,
        )
        reply = await self.provider.generate(
            messages=messages,
            model=selection.selected,
            options=selection.options,
        )
        return reply, selection.selected

    async def stream_reply(
        self,
        user_message: str,
        conversation: list[Message],
        custom_instructions: str = "",
        memory_items: list[str] | None = None,
        memory_note: str = "",
        tool_context: list[str] | None = None,
        model: str | None = None,
        effort: str = "medium",
    ) -> tuple[AsyncIterator[str], str]:
        available_models = await self._available_models_safe()
        selection = self.model_manager.select_model(
            requested_model=model,
            user_message=user_message,
            effort=effort,
            available_models=available_models,
        )
        messages = self._build_messages(
            user_message=user_message,
            conversation=conversation,
            custom_instructions=custom_instructions,
            memory_items=memory_items,
            memory_note=memory_note,
            tool_context=tool_context,
            effort=effort,
        )
        stream = self.provider.stream_generate(
            messages=messages,
            model=selection.selected,
            options=selection.options,
        )
        return stream, selection.selected

    async def available_models(self) -> list[str]:
        return await self.provider.list_models()


@lru_cache
def get_chat_service() -> ChatService:
    """Reuse one chat service instance across requests."""
    return ChatService(provider=OllamaProvider())
