"""
Evolution session state management.
Tracks pending capability development offers across requests.
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class PendingCapability:
    """Tracks a pending capability development offer."""
    capability_name: str
    offered_at: datetime
    expires_at: datetime


class EvolutionSessionManager:
    """
    Manages per-session evolution state across requests.
    Tracks pending capability offers and development status.
    """

    def __init__(self, expiration_minutes: int = 30):
        self.pending_capabilities: dict[str, PendingCapability] = {}
        self.expiration_delta = timedelta(minutes=expiration_minutes)

    def offer_capability(self, session_id: str, capability_name: str) -> None:
        """Record that a capability has been offered to the user."""
        now = datetime.utcnow()
        self.pending_capabilities[session_id] = PendingCapability(
            capability_name=capability_name,
            offered_at=now,
            expires_at=now + self.expiration_delta,
        )

    def get_pending_capability(self, session_id: str) -> Optional[str]:
        """
        Get the pending capability for a session (if not expired).
        
        Returns:
            Capability name if pending and not expired, None otherwise
        """
        if session_id not in self.pending_capabilities:
            return None

        pending = self.pending_capabilities[session_id]
        if datetime.utcnow() > pending.expires_at:
            # Expired, remove it
            del self.pending_capabilities[session_id]
            return None

        return pending.capability_name

    def clear_pending(self, session_id: str) -> None:
        """Clear the pending capability for a session."""
        if session_id in self.pending_capabilities:
            del self.pending_capabilities[session_id]

    def cleanup_expired(self) -> int:
        """Remove all expired pending capabilities. Returns count removed."""
        expired = [
            sid for sid, pending in self.pending_capabilities.items()
            if datetime.utcnow() > pending.expires_at
        ]
        for sid in expired:
            del self.pending_capabilities[sid]
        return len(expired)


# Global session manager instance
_session_manager = EvolutionSessionManager()


def get_evolution_session_manager() -> EvolutionSessionManager:
    """Get the global evolution session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = EvolutionSessionManager()
    return _session_manager
