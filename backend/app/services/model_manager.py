from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from app.core.config import settings
from app.core.hardware import detect_hardware


@dataclass(slots=True)
class ModelSelection:
    requested: str | None
    selected: str
    reasoning: str
    tier: str
    options: dict


class ModelManager:
    """Centralized model policy for chat, coding, and self-rewrite turns."""

    def __init__(self) -> None:
        self.default_model = settings.default_model
        self.coding_model = settings.coding_model
        self.reasoning_model = settings.reasoning_model
        self.fallback_models = settings.ollama_fallback_models
        self.large_context_chars = settings.max_tool_context_chars
        self.hw = detect_hardware()


    def get_hardware_info(self) -> dict:
        """Return a stable hardware profile payload for UI and API routes."""
        hw = self.hw
        return {
            "total_ram_gb": hw.total_ram_gb,
            "available_ram_gb": hw.available_ram_gb,
            "cpu_count": hw.cpu_count,
            "platform": hw.platform,
            "gpu_vram_gb": hw.gpu_vram_gb,
            "tier": hw.tier,
            "recommended_model": hw.recommended_model,
            "coding_model": hw.coding_model,
            "chat_model": hw.chat_model,
            "context_tokens": hw.context_tokens,
            "safe_limit_gb": hw.safe_ram_limit_gb,
            "safe_ram_limit_gb": hw.safe_ram_limit_gb,
            "default_model": self.default_model,
            "configured_coding_model": self.coding_model,
            "configured_reasoning_model": self.reasoning_model,
            "fallback_models": list(self.fallback_models),
        }

    def build_generation_options(self, *, effort: str, task_type: str) -> dict:
        base_ctx = max(settings.ollama_num_ctx, 8192 if task_type in {"coding", "self_rewrite"} else 4096)
        low = {
            "temperature": 0.15,
            "num_predict": 384,
            "num_ctx": base_ctx,
            "repeat_penalty": 1.05,
        }
        medium = {
            "temperature": 0.1,
            "num_predict": 768,
            "num_ctx": base_ctx,
            "repeat_penalty": 1.08,
        }
        high = {
            "temperature": 0.05,
            "num_predict": 1536,
            "num_ctx": max(base_ctx, 12288),
            "repeat_penalty": 1.1,
        }
        profiles = {"low": low, "medium": medium, "high": high}
        chosen = dict(profiles.get(effort, medium))
        if task_type == "self_rewrite":
            chosen["num_predict"] = max(chosen["num_predict"], 1024)
            chosen["num_ctx"] = max(chosen["num_ctx"], 12288)
        elif task_type == "coding":
            chosen["num_ctx"] = max(chosen["num_ctx"], 8192)
        return chosen

    def select_model(
        self,
        *,
        requested_model: str | None,
        user_message: str,
        effort: str,
        available_models: Iterable[str] | None = None,
    ) -> ModelSelection:
        available = [model for model in (available_models or []) if model]
        available_lower = {model.lower(): model for model in available}

        if requested_model:
            return ModelSelection(
                requested=requested_model,
                selected=requested_model,
                reasoning="User-selected model was honored.",
                tier="manual",
                options=self.build_generation_options(effort=effort, task_type=self.detect_task_type(user_message)),
            )

        task_type = self.detect_task_type(user_message)
        preferred = self._preferred_order_for_task(task_type)
        selected = self._resolve_preferred_model(preferred, available_lower) if available else preferred[0]
        reasoning = {
            "chat": "Balanced default selected for normal conversation.",
            "coding": "Coding-oriented model selected for implementation-heavy turn.",
            "self_rewrite": "Reasoning-focused model selected for self-development and guarded code rewriting.",
        }[task_type]
        return ModelSelection(
            requested=requested_model,
            selected=selected,
            reasoning=reasoning,
            tier=task_type,
            options=self.build_generation_options(effort=effort, task_type=task_type),
        )

    def detect_task_type(self, user_message: str) -> str:
        text = (user_message or "").lower()
        self_rewrite_markers = (
            "develop yourself",
            "improve yourself",
            "rewrite yourself",
            "rewrite your code",
            "fix your code",
            "upgrade yourself",
            "self improve",
            "self-improve",
            "self improve",
        )
        coding_markers = (
            "create ",
            "build ",
            "implement",
            "refactor",
            "debug",
            "fix bug",
            "write code",
            "edit file",
            "update file",
            "test ",
            "frontend",
            "backend",
            "api",
        )
        if any(marker in text for marker in self_rewrite_markers):
            return "self_rewrite"
        if any(marker in text for marker in coding_markers):
            return "coding"
        return "chat"

    def _preferred_order_for_task(self, task_type: str) -> list[str]:
        if task_type == "self_rewrite":
            order = [self.reasoning_model, self.coding_model, self.default_model]
        elif task_type == "coding":
            order = [self.coding_model, self.reasoning_model, self.default_model]
        else:
            order = [self.default_model, self.coding_model, self.reasoning_model]
        for model in self.fallback_models:
            if model not in order:
                order.append(model)
        return order

    def _resolve_preferred_model(self, preferred: list[str], available_lower: dict[str, str]) -> str:
        for candidate in preferred:
            exact = available_lower.get(candidate.lower())
            if exact:
                return exact
            for lower_name, original_name in available_lower.items():
                if candidate.lower() in lower_name or lower_name in candidate.lower():
                    return original_name
        return preferred[0]


@lru_cache
def get_model_manager() -> ModelManager:
    return ModelManager()
