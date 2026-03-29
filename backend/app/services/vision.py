from functools import lru_cache
import re

import httpx

from backend.app.core.config import settings


class VisionService:
    """Run image understanding through a vision-capable Ollama model when available."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def analyze_images(
        self,
        images_base64: list[str],
        prompt: str,
        preferred_model: str | None = None,
    ) -> tuple[str, str]:
        if not images_base64:
            raise ValueError("At least one image is required for vision analysis.")
        model = await self._select_model(preferred_model)
        if model is None:
            raise ValueError(
                "No vision-capable Ollama model is installed. Install a model such as "
                "`llava`, `moondream`, `qwen2.5vl`, or another vision model first."
            )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": images_base64,
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 384,
            },
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=180.0) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("The vision model returned an empty response.")
        return content, model

    async def _select_model(self, preferred_model: str | None) -> str | None:
        if preferred_model and self._looks_like_vision_model(preferred_model):
            return preferred_model

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

        models = [item.get("name", "") for item in data.get("models", [])]
        for model in models:
            if self._looks_like_vision_model(model):
                return model
        return None

    def _looks_like_vision_model(self, model: str) -> bool:
        lower = model.lower()
        keywords = (
            "llava",
            "bakllava",
            "vision",
            "moondream",
            "minicpm",
            "pixtral",
            "qwen2-vl",
            "qwen2vl",
            "qwen2.5-vl",
            "qwen2.5vl",
            "gemma3",
            "granite-vision",
        )
        if any(keyword in lower for keyword in keywords):
            return True
        return re.search(r"(^|[:/._-])vl($|[:/._-]|\d)", lower) is not None


@lru_cache
def get_vision_service() -> VisionService:
    return VisionService(base_url=settings.ollama_base_url)
