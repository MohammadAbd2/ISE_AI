from datetime import UTC, datetime
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore

_store = ChromaJSONStore("expansion_metrics")


def record_metric(metric_type: str, payload: dict | None = None):
    metric_id = str(uuid4())
    _store.upsert(metric_id, {"_id": metric_id, "timestamp": datetime.now(UTC).isoformat(), "metric_type": metric_type, "payload": payload or {}})
    return metric_id


def record_expansion(plan_id, original_step: str, substep_count: int, depth: int, source: str = "heuristic"):
    return record_metric("expansion", {"plan_id": plan_id, "original_step": original_step, "substep_count": substep_count, "depth": depth, "source": source})


def list_metrics(limit: int = 100):
    return _store.find(limit=limit, sort_key="timestamp", reverse=True)
