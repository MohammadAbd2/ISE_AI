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

    def _is_chat_compatible_model(self, model_data: dict) -> bool:
        name = (model_data.get("name") or "").lower()
        if not name:
            return False
        if any(blocked in name for blocked in ("llava", "bakllava", "moondream")):
            return False
        return True

    def _candidate_models(self, requested_model: str, catalog: list[dict]) -> list[str]:
        configured = settings.ollama_fallback_models
        installed = [item for item in catalog if self._is_chat_compatible_model(item)]
        installed_by_size = sorted(
            installed,
            key=lambda item: item.get("size") or 10**18,
        )

        ordered: list[str] = []

        def add(model_name: str) -> None:
            if model_name and model_name not in ordered:
                ordered.append(model_name)

        add(requested_model)
        for model_name in configured:
            add(model_name)
        for item in installed_by_size:
            add(item.get("name", ""))
        return ordered

    def _is_retryable_model_error(self, exc: Exception) -> bool:
        if not isinstance(exc, httpx.HTTPStatusError):
            return False
        try:
            # For streamed responses, we cannot access .json() or .text until read() is called.
            # httpx.HTTPStatusError from a stream context will have an un-read response.
            if exc.response.is_stream_consumed:
                payload = exc.response.json()
                error_text = str(payload.get("error", "")).lower()
            else:
                # We don't want to trigger a read() here as it might interfere with the stream logic,
                # but for error classification we may have to if we want to be precise.
                # However, Ollama usually sends the error in the initial response body for non-streaming
                # or as a JSON object if the stream fails immediately.
                error_text = exc.response.reason_phrase.lower()
        except Exception:
            error_text = ""
        
        return any(
            marker in error_text
            for marker in (
                "requires more system memory",
                "model not found",
                "not enough memory",
                "not enough available memory",
                "insufficient memory",
            )
        )

    async def _fetch_catalog(self, client: httpx.AsyncClient) -> list[dict]:
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception:
            return []

    async def generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> str:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            catalog = await self._fetch_catalog(client)
            last_error: Exception | None = None
            for candidate in self._candidate_models(model, catalog):
                payload = self._build_payload(
                    messages=messages,
                    model=candidate,
                    stream=False,
                    options=options,
                )
                try:
                    response = await client.post("/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data["message"]["content"]
                except Exception as exc:
                    last_error = exc
                    if not self._is_retryable_model_error(exc):
                        raise
            if last_error is not None:
                raise last_error
        raise RuntimeError("Ollama chat request failed without a recoverable model candidate.")

    async def stream_generate(
        self,
        messages: list[Message],
        model: str,
        options: dict | None = None,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=None) as client:
            catalog = await self._fetch_catalog(client)
            last_error: Exception | None = None
            for candidate in self._candidate_models(model, catalog):
                payload = self._build_payload(
                    messages=messages,
                    model=candidate,
                    stream=True,
                    options=options,
                )
                try:
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
                                return
                except Exception as exc:
                    last_error = exc
                    if not self._is_retryable_model_error(exc):
                        raise
            if last_error is not None:
                raise last_error
        raise RuntimeError("Ollama streaming request failed without a recoverable model candidate.")

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

        models = [item["name"] for item in data.get("models", []) if item.get("name") and self._is_chat_compatible_model(item)]
        preferred = [settings.default_model, *settings.ollama_fallback_models]
        ordered = []
        for model_name in preferred + models:
            if model_name not in ordered:
                ordered.append(model_name)
        return ordered or [settings.default_model]
