from abc import ABC, abstractmethod
from typing import AsyncIterator

from backend.app.models.message import Message


class LLMProvider(ABC):
    """Common contract for any local or remote model provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def stream_generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[str]:
        raise NotImplementedError
