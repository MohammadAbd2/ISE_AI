"""Small ChromaDB-backed document store used by backend services.

The project uses ChromaDB for JSON persistence. This
module centralizes that persistence on ChromaDB while keeping a tiny in-memory
fallback so the application can still import and run in environments where the
Python package has not been installed yet. Install ``chromadb`` from
``backend/requirements.txt`` for durable storage.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

try:  # ChromaDB is the only persistent database backend used by this project.
    import chromadb
except Exception:  # pragma: no cover - lets source checks pass before install.
    chromadb = None


def _default_chroma_path() -> Path:
    path = Path(getattr(settings, "chroma_path", Path(settings.backend_root).parent / ".chroma"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _safe_metadata(document: dict[str, Any]) -> dict[str, str | int | float | bool]:
    metadata: dict[str, str | int | float | bool] = {}
    for key, value in document.items():
        if key.startswith("_"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            metadata[key] = "" if value is None else value
        elif isinstance(value, datetime):
            metadata[key] = value.isoformat()
    return metadata


class ChromaJSONStore:
    """Persist and retrieve JSON-like dictionaries in a ChromaDB collection."""

    def __init__(self, collection_name: str, persist_path: Path | None = None) -> None:
        self.collection_name = collection_name
        self._lock = threading.RLock()
        self._memory: dict[str, dict[str, Any]] = {}
        self._client = None
        self._collection = None
        if chromadb is not None:
            self._client = chromadb.PersistentClient(path=str(persist_path or _default_chroma_path()))
            self._collection = self._client.get_or_create_collection(name=collection_name)

    @property
    def is_persistent(self) -> bool:
        return self._collection is not None

    def upsert(self, document_id: str, document: dict[str, Any]) -> str:
        document = dict(document)
        document["_id"] = str(document_id)
        payload = json.dumps(document, default=_json_default, ensure_ascii=False)
        with self._lock:
            if self._collection is None:
                self._memory[str(document_id)] = document
                return str(document_id)
            self._collection.upsert(
                ids=[str(document_id)],
                documents=[payload],
                metadatas=[_safe_metadata(document)],
            )
        return str(document_id)

    def get(self, document_id: str) -> dict[str, Any] | None:
        with self._lock:
            if self._collection is None:
                doc = self._memory.get(str(document_id))
                return dict(doc) if doc is not None else None
            result = self._collection.get(ids=[str(document_id)], include=["documents"])
        docs = result.get("documents") or []
        if not docs:
            return None
        return json.loads(docs[0])

    def all(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if self._collection is None:
                values = list(self._memory.values())
                return [dict(item) for item in (values[:limit] if limit else values)]
            result = self._collection.get(include=["documents"], limit=limit)
        return [json.loads(raw) for raw in (result.get("documents") or [])]

    def find(self, *, filters: dict[str, Any] | None = None, limit: int | None = None,
             sort_key: str | None = None, reverse: bool = True) -> list[dict[str, Any]]:
        records = self.all()
        if filters:
            records = [record for record in records if self._matches(record, filters)]
        if sort_key:
            records.sort(key=lambda item: str(item.get(sort_key, "")), reverse=reverse)
        return records[:limit] if limit else records

    def delete(self, document_id: str) -> bool:
        with self._lock:
            if self._collection is None:
                return self._memory.pop(str(document_id), None) is not None
            existed = self.get(str(document_id)) is not None
            if existed:
                self._collection.delete(ids=[str(document_id)])
            return existed

    def clear(self, filters: dict[str, Any] | None = None) -> int:
        records = self.find(filters=filters) if filters else self.all()
        count = 0
        for record in records:
            if self.delete(str(record.get("_id"))):
                count += 1
        return count

    @staticmethod
    def _matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            value = record.get(key)
            if isinstance(expected, (set, list, tuple)):
                if value not in expected:
                    return False
            elif value != expected:
                return False
        return True
