from datetime import UTC, datetime
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore

_store = ChromaJSONStore("approval_log")


def record_approval(plan_id: str, approved_by: str, message: str, accepted_files: list | None):
    document_id = str(uuid4())
    _store.upsert(document_id, {
        "_id": document_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "plan_id": plan_id,
        "approved_by": approved_by,
        "message": message,
        "accepted_files": accepted_files or [],
    })


def list_approvals(limit: int = 100):
    return [
        {
            "timestamp": row.get("timestamp"),
            "plan_id": row.get("plan_id"),
            "approved_by": row.get("approved_by"),
            "message": row.get("message"),
            "accepted_files": row.get("accepted_files", []),
        }
        for row in _store.find(limit=limit, sort_key="timestamp", reverse=True)
    ]
