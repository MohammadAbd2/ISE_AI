from functools import lru_cache
import re

import httpx

from app.core.config import settings


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
            hint = settings.ollama_vision_model.strip()
            extra = ""
            if hint:
                extra = (
                    f" You set OLLAMA_VISION_MODEL={hint!r}, but that name was not found in `ollama list`. "
                    "Run `ollama pull " + hint.split(":", 1)[0] + "` or fix the name."
                )
            else:
                extra = (
                    " Install one (for example `ollama pull llava` or `ollama pull moondream`), "
                    "or set OLLAMA_VISION_MODEL to the exact tag you use (e.g. llava:7b)."
                )
            raise ValueError(
                "No vision-capable Ollama model is installed or selected." + extra
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
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

        installed = [item.get("name", "") for item in data.get("models", []) if item.get("name")]

        configured = settings.ollama_vision_model.strip()
        if configured:
            if configured in installed:
                return configured
            prefix = configured.rstrip(":") + ":"
            for name in installed:
                if name == configured or name.startswith(prefix):
                    return name

        if preferred_model and self._looks_like_vision_model(preferred_model):
            if preferred_model in installed:
                return preferred_model

        for model in installed:
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
            "qwen3-vl",
            "qwen3vl",
            "qwen3.5-vl",
            "gemma3",
            "granite-vision",
            "smolvlm",
            "internvl",
            "glm4v",
            "glm-4v",
            "phi3.5-vision",
        )
        if any(keyword in lower for keyword in keywords):
            return True
        if "llama3.2" in lower and "vision" in lower:
            return True
        if "qwen" in lower and "vl" in lower:
            return True
        return re.search(r"(^|[:/._-])vl($|[:/._-]|\d)", lower) is not None


@lru_cache
def get_vision_service() -> VisionService:
    return VisionService(base_url=settings.ollama_base_url)
