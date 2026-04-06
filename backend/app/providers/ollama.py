import httpx
import json
from typing import AsyncIterator

from app.core.config import settings
from app.models.message import Message
from app.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.ollama_base_url

    def _build_payload(
        self,
        messages: list[Message],
        model: str,
        stream: bool,
        options: dict | None = None,
    ) -> dict:
        # Translate the internal message model into Ollama's chat payload shape.
        payload = {
            "model": model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "stream": stream,
        }
        if options:
            payload["options"] = options
        return payload

    async def generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> str:
        payload = self._build_payload(
            messages=messages,
            model=model,
            stream=False,
            options=options,
        )

        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        return data["message"]["content"]

    async def stream_generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> AsyncIterator[str]:
        payload = self._build_payload(
            messages=messages,
            model=model,
            stream=True,
            options=options,
        )

        async with httpx.AsyncClient(base_url=self.base_url, timeout=None) as client:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                # Ollama streams one JSON object per line.
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

        models = [item["name"] for item in data.get("models", []) if item.get("name")]
        # Show preferred local models first when they are installed.
        preferred = ["llama3", "qwen:7b", "llama3.2:3b"]
        ordered = preferred + [model for model in models if model not in preferred]
        return ordered or [settings.default_model]
