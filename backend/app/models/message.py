from dataclasses import dataclass


@dataclass(slots=True)
class Message:
    """Provider-facing chat message used after request validation."""
    role: str
    content: str
