"""
Permission and approval system for user control over AI self-evolution.
Tracks user approvals and ensures major changes are authorized.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import settings


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """Represents a request for user approval."""

    id: str
    action: str  # e.g., "develop_capability", "deploy_feature"
    details: str
    status: ApprovalStatus
    requested_at: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None


class PermissionManager:
    """
    Manages user approval requests for AI self-modifications.
    Provides audit trail of all approvals and rejections.
    """

    def __init__(self):
        self.db_path = Path(settings.backend_root).parent / ".evolution-approvals.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    details TEXT,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON approval_requests(status)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_requested_at
                ON approval_requests(requested_at)
                """
            )
            conn.commit()

    def request_approval(
        self,
        action: str,
        details: str,
        request_id: Optional[str] = None,
    ) -> dict:
        """
        Create a new approval request.
        
        Args:
            action: Type of action requiring approval
            details: Detailed description of the request
            request_id: Optional custom ID (auto-generated if not provided)
        
        Returns:
            Request details
        """
        import uuid

        request_id = request_id or str(uuid.uuid4())[:12]
        timestamp = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO approval_requests
                (id, action, details, status, requested_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, action, details, ApprovalStatus.PENDING.value, timestamp),
            )
            conn.commit()

        return {
            "status": "success",
            "request_id": request_id,
            "action": action,
            "approval_status": ApprovalStatus.PENDING.value,
        }

    def approve_request(
        self,
        request_id: str,
        approved_by: str = "user",
    ) -> dict:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of request to approve
            approved_by: Who approved it (default: "user")
        
        Returns:
            Approval details
        """
        timestamp = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM approval_requests WHERE id = ?", (request_id,)
            )
            row = cursor.fetchone()

            if not row:
                return {
                    "status": "failed",
                    "error": f"Request {request_id} not found",
                }

            if row[3] != ApprovalStatus.PENDING.value:
                return {
                    "status": "failed",
                    "error": f"Request is {row[3]}, not pending",
                }

            conn.execute(
                """
                UPDATE approval_requests
                SET status = ?, approved_at = ?, approved_by = ?
                WHERE id = ?
                """,
                (ApprovalStatus.APPROVED.value, timestamp, approved_by, request_id),
            )
            conn.commit()

        return {
            "status": "success",
            "request_id": request_id,
            "approved": True,
            "approved_at": timestamp,
        }

    def reject_request(
        self,
        request_id: str,
        reason: Optional[str] = None,
        rejected_by: str = "user",
    ) -> dict:
        """
        Reject a pending request.
        
        Args:
            request_id: ID of request to reject
            reason: Optional reason for rejection
            rejected_by: Who rejected it
        
        Returns:
            Rejection details
        """
        timestamp = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM approval_requests WHERE id = ?", (request_id,)
            )
            row = cursor.fetchone()

            if not row:
                return {
                    "status": "failed",
                    "error": f"Request {request_id} not found",
                }

            if row[3] != ApprovalStatus.PENDING.value:
                return {
                    "status": "failed",
                    "error": f"Request is {row[3]}, not pending",
                }

            details = row[2] or ""
            if reason:
                details = f"{details}\n---\nRejection reason: {reason}"

            conn.execute(
                """
                UPDATE approval_requests
                SET status = ?, details = ?
                WHERE id = ?
                """,
                (ApprovalStatus.REJECTED.value, details, request_id),
            )
            conn.commit()

        return {
            "status": "success",
            "request_id": request_id,
            "rejected": True,
            "rejected_at": timestamp,
        }

    def get_request(self, request_id: str) -> Optional[dict]:
        """Get a specific approval request."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM approval_requests WHERE id = ?", (request_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_pending_requests(self) -> list[dict]:
        """List all pending approval requests."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM approval_requests
                WHERE status = ?
                ORDER BY requested_at DESC
                """,
                (ApprovalStatus.PENDING.value,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def list_all_requests(
        self,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List approval requests with optional filtering.
        
        Args:
            action: Filter by action type
            status: Filter by status
            limit: Maximum results
        
        Returns:
            List of requests
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM approval_requests WHERE 1=1"
            params = []

            if action:
                query += " AND action = ?"
                params.append(action)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY requested_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_approval_history(self, action: Optional[str] = None) -> list[dict]:
        """Get history of approved requests."""
        return self.list_all_requests(
            action=action, status=ApprovalStatus.APPROVED.value
        )

    def get_rejection_history(self, action: Optional[str] = None) -> list[dict]:
        """Get history of rejected requests."""
        return self.list_all_requests(
            action=action, status=ApprovalStatus.REJECTED.value
        )

    def count_pending(self) -> int:
        """Count pending approval requests."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM approval_requests WHERE status = ?",
                (ApprovalStatus.PENDING.value,),
            )
            return cursor.fetchone()[0]

    def requires_approval(self, action: str) -> bool:
        """Check if an action type requires approval."""
        # Actions that always require approval
        requires_approval_actions = {
            "develop_capability",
            "deploy_feature",
            "modify_core_file",
            "delete_data",
            "install_package",
        }
        return action in requires_approval_actions

    def can_proceed(self, request_id: str) -> bool:
        """Check if a request has been approved and can proceed."""
        request = self.get_request(request_id)
        return request is not None and request["status"] == ApprovalStatus.APPROVED.value


def get_permission_manager() -> PermissionManager:
    """Dependency for FastAPI endpoints."""
    return PermissionManager()
