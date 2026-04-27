"""Permission and approval system backed by ChromaDB."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    id: str
    action: str
    details: str
    status: ApprovalStatus
    requested_at: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None


class PermissionManager:
    """Manages user approval requests for AI self-modifications."""

    def __init__(self):
        self.store = ChromaJSONStore("approval_requests")

    def _init_db(self) -> None:
        return None

    def request_approval(self, action: str, details: str, request_id: Optional[str] = None) -> dict:
        request_id = request_id or str(uuid4())[:12]
        timestamp = datetime.now(UTC).isoformat()
        self.store.upsert(request_id, {"_id": request_id, "id": request_id, "action": action, "details": details, "status": ApprovalStatus.PENDING.value, "requested_at": timestamp, "approved_at": None, "approved_by": None, "created_at": timestamp})
        return {"status": "success", "request_id": request_id, "action": action, "approval_status": ApprovalStatus.PENDING.value}

    def approve_request(self, request_id: str, approved_by: str = "user") -> dict:
        row = self.store.get(request_id)
        if not row:
            return {"status": "failed", "error": f"Request {request_id} not found"}
        if row.get("status") != ApprovalStatus.PENDING.value:
            return {"status": "failed", "error": f"Request is {row.get('status')}, not pending"}
        timestamp = datetime.now(UTC).isoformat()
        row.update({"status": ApprovalStatus.APPROVED.value, "approved_at": timestamp, "approved_by": approved_by})
        self.store.upsert(request_id, row)
        return {"status": "success", "request_id": request_id, "approved": True, "approved_at": timestamp}

    def reject_request(self, request_id: str, reason: Optional[str] = None, rejected_by: str = "user") -> dict:
        row = self.store.get(request_id)
        if not row:
            return {"status": "failed", "error": f"Request {request_id} not found"}
        if row.get("status") != ApprovalStatus.PENDING.value:
            return {"status": "failed", "error": f"Request is {row.get('status')}, not pending"}
        timestamp = datetime.now(UTC).isoformat()
        details = row.get("details") or ""
        if reason:
            details = f"{details}\n---\nRejection reason: {reason}"
        row.update({"status": ApprovalStatus.REJECTED.value, "details": details, "approved_at": timestamp, "approved_by": rejected_by})
        self.store.upsert(request_id, row)
        return {"status": "success", "request_id": request_id, "rejected": True, "rejected_at": timestamp}

    def get_request(self, request_id: str) -> Optional[dict]:
        return self.store.get(request_id)

    def list_pending_requests(self) -> list[dict]:
        return self.store.find(filters={"status": ApprovalStatus.PENDING.value}, sort_key="requested_at", reverse=True)

    def list_all_requests(self, action: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        rows = self.store.find(sort_key="requested_at", reverse=True)
        if action:
            rows = [row for row in rows if row.get("action") == action]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows[:limit]

    def get_approval_history(self, action: Optional[str] = None) -> list[dict]:
        return self.list_all_requests(action=action, status=ApprovalStatus.APPROVED.value)

    def get_rejection_history(self, action: Optional[str] = None) -> list[dict]:
        return self.list_all_requests(action=action, status=ApprovalStatus.REJECTED.value)

    def count_pending(self) -> int:
        return len(self.list_pending_requests())

    def requires_approval(self, action: str) -> bool:
        return action in {"develop_capability", "deploy_feature", "modify_core_file", "delete_data", "install_package"}

    def can_proceed(self, request_id: str) -> bool:
        request = self.get_request(request_id)
        return request is not None and request.get("status") == ApprovalStatus.APPROVED.value


def get_permission_manager() -> PermissionManager:
    return PermissionManager()
