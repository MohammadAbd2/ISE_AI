"""
Capability registry for the AI system.
Tracks what the AI can do and status of each capability.
"""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from backend.app.core.config import settings


class CapabilityStatus(str, Enum):
    """Status of a capability."""

    AVAILABLE = "available"
    PENDING = "pending"
    IN_DEVELOPMENT = "in_development"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class Capability:
    """Represents a single AI capability."""

    def __init__(
        self,
        name: str,
        description: str,
        status: CapabilityStatus = CapabilityStatus.AVAILABLE,
        version: str = "1.0.0",
        added_at: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.name = name
        self.description = description
        self.status = status
        self.version = version
        self.added_at = added_at or datetime.now(UTC).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "version": self.version,
            "added_at": self.added_at,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "Capability":
        """Create from dictionary."""
        return Capability(
            name=data["name"],
            description=data["description"],
            status=CapabilityStatus(data.get("status", "available")),
            version=data.get("version", "1.0.0"),
            added_at=data.get("added_at"),
            metadata=data.get("metadata", {}),
        )


class CapabilityRegistry:
    """
    Central registry of AI capabilities.
    Persisted as JSON for easy inspection and modification.
    """

    def __init__(self):
        self.registry_file = (
            Path(settings.backend_root).parent / ".evolution-registry.json"
        )
        self.capabilities: dict[str, Capability] = {}
        self._load_registry()
        self._initialize_defaults()

    def _load_registry(self) -> None:
        """Load registry from file."""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text())
                for name, cap_data in data.items():
                    self.capabilities[name] = Capability.from_dict(cap_data)
            except Exception:
                self.capabilities = {}
        else:
            self.capabilities = {}

    def _save_registry(self) -> None:
        """Save registry to file."""
        data = {name: cap.to_dict() for name, cap in self.capabilities.items()}
        self.registry_file.write_text(json.dumps(data, indent=2))

    def _initialize_defaults(self) -> None:
        """Initialize default capabilities if empty."""
        if not self.capabilities:
            self.register(
                Capability(
                    name="text_generation",
                    description="Generate text responses using language models",
                    status=CapabilityStatus.AVAILABLE,
                    version="1.0.0",
                    metadata={"default": True, "models": ["llama3", "mistral"]},
                )
            )
            self.register(
                Capability(
                    name="memory_management",
                    description="Store and retrieve user information and preferences",
                    status=CapabilityStatus.AVAILABLE,
                    version="1.0.0",
                    metadata={"default": True},
                )
            )
            self.register(
                Capability(
                    name="web_search",
                    description="Search the web for information",
                    status=CapabilityStatus.AVAILABLE,
                    version="1.0.0",
                    metadata={"provider": "pending"},
                )
            )

    def register(self, capability: Capability) -> dict:
        """
        Register a new capability or update existing one.
        
        Args:
            capability: Capability object to register
        
        Returns:
            Registration result
        """
        self.capabilities[capability.name] = capability
        self._save_registry()
        return {
            "status": "success",
            "capability": capability.name,
            "current_status": capability.status.value,
        }

    def get_capability(self, name: str) -> Optional[Capability]:
        """Get a capability by name."""
        return self.capabilities.get(name)

    def list_capabilities(self) -> list[dict]:
        """List all capabilities."""
        return [cap.to_dict() for cap in self.capabilities.values()]

    def list_by_status(self, status: CapabilityStatus) -> list[dict]:
        """List capabilities by status."""
        return [
            cap.to_dict()
            for cap in self.capabilities.values()
            if cap.status == status
        ]

    def update_status(self, name: str, status: CapabilityStatus) -> dict:
        """Update capability status."""
        if name not in self.capabilities:
            return {
                "status": "failed",
                "error": f"Capability {name} not found",
            }

        cap = self.capabilities[name]
        cap.status = status
        self._save_registry()
        return {
            "status": "success",
            "capability": name,
            "new_status": status.value,
        }

    def update_metadata(self, name: str, metadata: dict) -> dict:
        """Update capability metadata."""
        if name not in self.capabilities:
            return {
                "status": "failed",
                "error": f"Capability {name} not found",
            }

        cap = self.capabilities[name]
        cap.metadata.update(metadata)
        self._save_registry()
        return {
            "status": "success",
            "capability": name,
            "metadata": cap.metadata,
        }

    def has_capability(self, name: str) -> bool:
        """Check if a capability exists and is available."""
        cap = self.capabilities.get(name)
        return cap is not None and cap.status == CapabilityStatus.AVAILABLE

    def can_develop_capability(self, name: str) -> bool:
        """Check if a capability can be developed (doesn't exist yet)."""
        return name not in self.capabilities or self.capabilities[
            name
        ].status in [
            CapabilityStatus.FAILED,
            CapabilityStatus.DEPRECATED,
        ]

    def remove_capability(self, name: str) -> dict:
        """Remove a capability (set to deprecated)."""
        if name not in self.capabilities:
            return {
                "status": "failed",
                "error": f"Capability {name} not found",
            }

        cap = self.capabilities[name]
        cap.status = CapabilityStatus.DEPRECATED
        self._save_registry()
        return {
            "status": "success",
            "capability": name,
            "marked_as": "deprecated",
        }


def get_capability_registry() -> CapabilityRegistry:
    """Dependency for FastAPI endpoints."""
    return CapabilityRegistry()
