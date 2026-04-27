"""
Evolution logger for tracking AI self-modifications.
Records all changes, attempts, and rollbacks for audit trail using ChromaDB.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore


class EvolutionEventType(str, Enum):
    CAPABILITY_REQUESTED = "capability_requested"
    RESEARCH_STARTED = "research_started"
    IMPLEMENTATION_STARTED = "implementation_started"
    CODE_MODIFIED = "code_modified"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    CAPABILITY_DEPLOYED = "capability_deployed"
    ROLLBACK_EXECUTED = "rollback_executed"
    ERROR_OCCURRED = "error_occurred"


class EventStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


@dataclass
class EvolutionEvent:
    timestamp: str
    event_type: EvolutionEventType
    capability: str
    status: EventStatus
    description: str
    details: Optional[dict] = None
    rollback_backup_id: Optional[str] = None


class EvolutionLogger:
    """ChromaDB-based logger for AI evolution events."""

    def __init__(self):
        self.store = ChromaJSONStore("evolution_events")

    def _init_db(self) -> None:
        return None

    def log_event(self, event_type: EvolutionEventType, capability: str, status: EventStatus, description: str, details: Optional[dict] = None, rollback_backup_id: Optional[str] = None) -> dict:
        timestamp = datetime.now(UTC).isoformat()
        event_id = str(uuid4())
        document = {"_id": event_id, "id": event_id, "timestamp": timestamp, "event_type": event_type.value, "capability": capability, "status": status.value, "description": description, "details": details or {}, "rollback_backup_id": rollback_backup_id, "created_at": timestamp}
        self.store.upsert(event_id, document)
        return {"id": event_id, "timestamp": timestamp, "event_type": event_type.value, "capability": capability, "status": status.value, "description": description}

    def get_event_history(self, capability: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[dict]:
        filters = {"capability": capability} if capability else None
        rows = self.store.find(filters=filters, sort_key="timestamp", reverse=True)
        return rows[offset:offset + limit]

    def get_capability_timeline(self, capability: str) -> list[dict]:
        return self.store.find(filters={"capability": capability}, sort_key="timestamp", reverse=False)

    def count_events(self, capability: Optional[str] = None) -> int:
        return len(self.store.find(filters={"capability": capability} if capability else None))

    def get_latest_event(self, capability: str) -> Optional[dict]:
        rows = self.store.find(filters={"capability": capability}, sort_key="timestamp", reverse=True, limit=1)
        return rows[0] if rows else None

    def get_failed_attempts(self, capability: str) -> list[dict]:
        rows = self.store.find(filters={"capability": capability}, sort_key="timestamp", reverse=True)
        return [row for row in rows if row.get("status") == EventStatus.FAILED.value]

    def get_deployment_history(self) -> list[dict]:
        return self.store.find(filters={"event_type": EvolutionEventType.CAPABILITY_DEPLOYED.value}, sort_key="timestamp", reverse=True)

    def clear_logs(self, capability: Optional[str] = None) -> dict:
        deleted = self.store.clear(filters={"capability": capability} if capability else None)
        return {"status": "success", "rows_deleted": deleted}


def get_evolution_logger() -> EvolutionLogger:
    return EvolutionLogger()
