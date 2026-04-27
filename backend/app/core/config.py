"""Centralized runtime configuration for ISE AI backend."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_env_file() -> dict[str, str]:
    """Load .env values from the most common project entry points."""
    env_paths = [
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    values: dict[str, str] = {}
    for env_path in env_paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


_env_file_values = _load_env_file()


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, _env_file_values.get(key, default))


def _get_env_bool(key: str, default: bool) -> bool:
    raw = _get_env(key, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    """Centralized runtime configuration shared across the backend."""

    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[3])
    backend_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    app_name: str = _get_env("APP_NAME", "ISE AI")
    environment: str = _get_env("ENVIRONMENT", "development")
    version: str = "2.0.0"

    # Ollama / model settings
    ollama_base_url: str = _get_env("OLLAMA_BASE_URL", "http://localhost:11434")
    default_model: str = _get_env("DEFAULT_MODEL", "auto")  # "auto" = hardware-detected
    coding_model: str = _get_env("CODING_MODEL", "auto")
    reasoning_model: str = _get_env("REASONING_MODEL", "auto")
    ollama_num_ctx: int = int(_get_env("OLLAMA_NUM_CTX", "8192"))
    max_tool_context_chars: int = int(_get_env("MAX_TOOL_CONTEXT_CHARS", "32000"))
    ollama_image_model: str = _get_env("OLLAMA_IMAGE_MODEL", "").strip()
    ollama_vision_model: str = _get_env("OLLAMA_VISION_MODEL", "").strip()

    # Fallback models in priority order
    ollama_fallback_models: list[str] = field(
        default_factory=lambda: [
            m.strip()
            for m in _get_env(
                "OLLAMA_FALLBACK_MODELS",
                "qwen2.5-coder:14b,qwen2.5-coder:7b,qwen2.5:7b,deepseek-coder-v2,llama3.1:8b,llama3.2:3b",
            ).split(",")
            if m.strip()
        ]
    )

    # Self-rewrite / evolution
    self_rewrite_apply_on_success: bool = _get_env_bool("SELF_REWRITE_APPLY_ON_SUCCESS", True)
    self_rewrite_workspace: str = _get_env("SELF_REWRITE_WORKSPACE", ".ise_ai_self_rewrites")

    # ChromaDB storage
    chroma_path: str = _get_env("CHROMA_PATH", str(Path(__file__).resolve().parents[3] / "backend" / ".chroma"))
    chroma_tenant: str = _get_env("CHROMA_TENANT", "default_tenant")
    chroma_database: str = _get_env("CHROMA_DATABASE", "default_database")

    # Sandbox
    sandbox_enabled: bool = _get_env_bool("SANDBOX_ENABLED", True)
    sandbox_timeout: int = int(_get_env("SANDBOX_TIMEOUT", "30"))
    docker_enabled: bool = _get_env_bool("DOCKER_ENABLED", False)

    # CORS
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in _get_env(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,https://localhost:5173,https://127.0.0.1:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]
    )

    # System prompt
    system_prompt: str = _get_env(
        "SYSTEM_PROMPT",
        (
            "You are ISE AI, an advanced autonomous software engineering assistant. "
            "You operate with execution-first principles: inspect, plan, act, verify, report. "
            "You have access to file I/O, shell commands, web search, and a sandboxed desktop environment. "
            "Never pretend operations occurred—execute them and report real results. "
            "When improving yourself, use the isolated self-rewrite workflow. "
            "Be concise, technically strong, and transparent. "
            "Use ✅ for success, ❌ for errors, 🔍 for research, 🛠️ for building, 🧪 for testing."
        ),
    )


settings = Settings()
