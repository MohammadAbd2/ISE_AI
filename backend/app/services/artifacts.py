import asyncio
from datetime import UTC, datetime
from functools import lru_cache
import threading
from uuid import uuid4

from app.services.chroma_store import ChromaJSONStore


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactService:
    """Persist uploaded documents, search results, and sandbox outputs per session in ChromaDB."""

    def __init__(self, chroma_path: str | None = None, collection_name: str | None = None) -> None:
        self._lock = threading.Lock()
        self.store = ChromaJSONStore("artifacts")

    async def create_artifact(self, session_id: str, kind: str, title: str, content: str, metadata: dict | None = None) -> dict:
        return await asyncio.to_thread(self._create_artifact_sync, session_id, kind, title, content, metadata or {})

    def _create_artifact_sync(self, session_id: str, kind: str, title: str, content: str, metadata: dict) -> dict:
        now = _utc_now().isoformat()
        artifact_id = str(uuid4())
        document = {"_id": artifact_id, "session_id": session_id, "kind": kind, "title": title, "content": content, "metadata": metadata, "created_at": now, "updated_at": now}
        self.store.upsert(artifact_id, document)
        return self._serialize(document)

    async def get_artifact(self, artifact_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_artifact_sync, artifact_id)

    def _get_artifact_sync(self, artifact_id: str) -> dict | None:
        return self._serialize(self.store.get(artifact_id))

    async def list_artifacts(self, session_id: str, kinds: list[str] | None = None, limit: int = 8) -> list[dict]:
        return await asyncio.to_thread(self._list_artifacts_sync, session_id, kinds or [], limit)

    def _list_artifacts_sync(self, session_id: str, kinds: list[str], limit: int) -> list[dict]:
        docs = self.store.find(filters={"session_id": session_id}, sort_key="updated_at", reverse=True)
        if kinds:
            docs = [doc for doc in docs if doc.get("kind") in kinds]
        return [self._serialize(item) for item in docs[:limit]]

    async def delete_artifact(self, artifact_id: str) -> bool:
        return await asyncio.to_thread(self.store.delete, artifact_id)

    async def reassign_session(self, old_session_id: str, new_session_id: str) -> None:
        await asyncio.to_thread(self._reassign_session_sync, old_session_id, new_session_id)

    def _reassign_session_sync(self, old_session_id: str, new_session_id: str) -> None:
        if old_session_id == new_session_id:
            return
        with self._lock:
            for artifact in self.store.find(filters={"session_id": old_session_id}):
                artifact["session_id"] = new_session_id
                artifact["updated_at"] = _utc_now().isoformat()
                self.store.upsert(str(artifact["_id"]), artifact)

    def storage_mode(self) -> str:
        return "chromadb" if self.store.is_persistent else "memory"

    def close(self) -> None:
        return None

    def __del__(self) -> None:
        self.close()

    def _serialize(self, document: dict | None) -> dict | None:
        if document is None:
            return None
        return {"id": str(document.get("_id", "")), "session_id": document.get("session_id", ""), "kind": document.get("kind", "file"), "title": document.get("title", "Artifact"), "content": document.get("content", ""), "metadata": dict(document.get("metadata", {})), "created_at": str(document.get("created_at", _utc_now().isoformat())), "updated_at": str(document.get("updated_at", _utc_now().isoformat()))}


@lru_cache
def get_artifact_service() -> ArtifactService:
    return ArtifactService()
