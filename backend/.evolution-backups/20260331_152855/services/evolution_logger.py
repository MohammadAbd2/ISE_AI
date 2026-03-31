"""
Evolution logger for tracking AI self-modifications.
Records all changes, attempts, and rollbacks for audit trail.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from backend.app.core.config import settings


class EvolutionEventType(str, Enum):
    """Type of evolution event."""

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
    """Status of an event."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


@dataclass
class EvolutionEvent:
    """Represents a single evolution event."""

    timestamp: str
    event_type: EvolutionEventType
    capability: str
    status: EventStatus
    description: str
    details: Optional[dict] = None
    rollback_backup_id: Optional[str] = None


class EvolutionLogger:
    """
    SQLite-based logger for AI evolution events.
    Provides audit trail of all modifications and rollbacks.
    """

    def __init__(self):
        self.db_path = (
            Path(settings.backend_root).parent / ".evolution-logs.db"
        )
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT,
                    details TEXT,
                    rollback_backup_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_capability
                ON evolution_events(capability)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON evolution_events(timestamp)
                """
            )
            conn.commit()

    def log_event(
        self,
        event_type: EvolutionEventType,
        capability: str,
        status: EventStatus,
        description: str,
        details: Optional[dict] = None,
        rollback_backup_id: Optional[str] = None,
    ) -> dict:
        """
        Log a single evolution event.
        
        Args:
            event_type: Type of evolution event
            capability: Name of capability involved
            status: Status of the event
            description: Human-readable description
            details: Optional structured details (dict)
            rollback_backup_id: Backup ID if this is a rollback
        
        Returns:
            Event details with ID
        """
        timestamp = datetime.now(UTC).isoformat()
        details_json = None
        if details:
            import json

            details_json = json.dumps(details)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO evolution_events
                (timestamp, event_type, capability, status, description, details, rollback_backup_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    event_type.value,
                    capability,
                    status.value,
                    description,
                    details_json,
                    rollback_backup_id,
                ),
            )
            event_id = cursor.lastrowid
            conn.commit()

        return {
            "id": event_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "capability": capability,
            "status": status.value,
            "description": description,
        }

    def get_event_history(
        self,
        capability: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get evolution event history.
        
        Args:
            capability: Filter by capability (None = all)
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of events
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if capability:
                cursor = conn.execute(
                    """
                    SELECT * FROM evolution_events
                    WHERE capability = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (capability, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM evolution_events
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_capability_timeline(self, capability: str) -> list[dict]:
        """Get full timeline for a specific capability."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evolution_events
                WHERE capability = ?
                ORDER BY timestamp ASC
                """,
                (capability,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def count_events(self, capability: Optional[str] = None) -> int:
        """Count total events."""
        with sqlite3.connect(self.db_path) as conn:
            if capability:
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM evolution_events WHERE capability = ?",
                    (capability,),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM evolution_events"
                )
            return cursor.fetchone()[0]

    def get_latest_event(self, capability: str) -> Optional[dict]:
        """Get the most recent event for a capability."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evolution_events
                WHERE capability = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (capability,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_failed_attempts(self, capability: str) -> list[dict]:
        """Get all failed attempts for a capability."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evolution_events
                WHERE capability = ? AND status = ?
                ORDER BY timestamp DESC
                """,
                (capability, EventStatus.FAILED.value),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_deployment_history(self) -> list[dict]:
        """Get history of all capability deployments."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evolution_events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                """,
                (EvolutionEventType.CAPABILITY_DEPLOYED.value,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_logs(self, capability: Optional[str] = None) -> dict:
        """Clear logs (use with caution)."""
        with sqlite3.connect(self.db_path) as conn:
            if capability:
                cursor = conn.execute(
                    "DELETE FROM evolution_events WHERE capability = ?",
                    (capability,),
                )
            else:
                cursor = conn.execute("DELETE FROM evolution_events")
            conn.commit()
            return {
                "status": "success",
                "rows_deleted": cursor.rowcount,
            }


def get_evolution_logger() -> EvolutionLogger:
    """Dependency for FastAPI endpoints."""
    return EvolutionLogger()
