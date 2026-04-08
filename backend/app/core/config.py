from dataclasses import dataclass, field
import os
from pathlib import Path


def _load_env_file() -> dict[str, str]:
    """Load .env values from the most common project entrypoints."""
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


@dataclass(slots=True)
class Settings:
    """Centralized runtime configuration shared across the backend."""
    backend_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    app_name: str = _get_env("APP_NAME", "ISE AI Chatbot")
    environment: str = _get_env("ENVIRONMENT", "development")
    ollama_base_url: str = _get_env("OLLAMA_BASE_URL", "http://localhost:11434")
    mongo_uri: str = _get_env("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = _get_env("MONGO_DB_NAME", "ise_ai")
    default_model: str = _get_env("DEFAULT_MODEL", "llama3")
    ollama_image_model: str = _get_env(
        "OLLAMA_IMAGE_MODEL",
        "",
    ).strip()
    ollama_vision_model: str = _get_env(
        "OLLAMA_VISION_MODEL",
        "",
    ).strip()
    system_prompt: str = _get_env(
        "SYSTEM_PROMPT",
        "You are ISE AI, a professional coding assistant that ACTUALLY performs operations. "
        "When asked to create, edit, or manipulate files, EXECUTE the operation - don't just describe it. "
        "Always show real results: actual file paths, actual content, actual command output. "
        "Be proactive: if you notice issues while working, fix them automatically. "
        "Self-correct: if something fails, analyze the error, fix it, and retry. "
        "Use icons and formatting: ✅ for success, ❌ for errors, 📝 for creating, ✏️ for editing, 📖 for reading, 🗑️ for deleting. "
        "Be concise but thorough. Prioritize execution and results over explanation.",
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in _get_env(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]
    )


settings = Settings()
