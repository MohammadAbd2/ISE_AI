import asyncio
from datetime import UTC, datetime
from functools import lru_cache
import threading
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.core.config import settings


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactService:
    """Persist uploaded documents, search results, and sandbox outputs per session."""

    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._memory_artifacts: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._mongo_available = True
        self._client: MongoClient | None = None
        try:
            self._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
            self._client.admin.command("ping")
            self.collection = self._client[db_name]["artifacts"]
        except PyMongoError:
            if self._client is not None:
                self._client.close()
                self._client = None
            self.collection = None
            self._mongo_available = False

    async def create_artifact(
        self,
        session_id: str,
        kind: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> dict:
        return await asyncio.to_thread(
            self._create_artifact_sync,
            session_id,
            kind,
            title,
            content,
            metadata or {},
        )

    def _create_artifact_sync(
        self,
        session_id: str,
        kind: str,
        title: str,
        content: str,
        metadata: dict,
    ) -> dict:
        now = _utc_now()
        artifact_id = str(uuid4())
        document = {
            "_id": artifact_id,
            "session_id": session_id,
            "kind": kind,
            "title": title,
            "content": content,
            "metadata": metadata,
            "created_at": now,
            "updated_at": now,
        }
        if not self._mongo_available or self.collection is None:
            with self._lock:
                self._memory_artifacts[artifact_id] = document
            return self._serialize(document)
        try:
            self.collection.insert_one(document)
            return self._serialize(document)
        except PyMongoError:
            self._mongo_available = False
            with self._lock:
                self._memory_artifacts[artifact_id] = document
            return self._serialize(document)

    async def get_artifact(self, artifact_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_artifact_sync, artifact_id)

    def _get_artifact_sync(self, artifact_id: str) -> dict | None:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                document = self._memory_artifacts.get(artifact_id)
                return self._serialize(document) if document else None
        try:
            document = self.collection.find_one({"_id": artifact_id})
            return self._serialize(document) if document else None
        except PyMongoError:
            self._mongo_available = False
            return self._get_artifact_sync(artifact_id)

    async def list_artifacts(
        self,
        session_id: str,
        kinds: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict]:
        return await asyncio.to_thread(
            self._list_artifacts_sync,
            session_id,
            kinds or [],
            limit,
        )

    def _list_artifacts_sync(
        self,
        session_id: str,
        kinds: list[str],
        limit: int,
    ) -> list[dict]:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                artifacts = [
                    artifact
                    for artifact in self._memory_artifacts.values()
                    if artifact["session_id"] == session_id
                    and (not kinds or artifact["kind"] in kinds)
                ]
                artifacts.sort(key=lambda item: item["updated_at"], reverse=True)
                return [self._serialize(item) for item in artifacts[:limit]]
        try:
            query = {"session_id": session_id}
            if kinds:
                query["kind"] = {"$in": kinds}
            cursor = self.collection.find(query).sort("updated_at", -1).limit(limit)
            return [self._serialize(item) for item in cursor]
        except PyMongoError:
            self._mongo_available = False
            return self._list_artifacts_sync(session_id, kinds, limit)

    async def reassign_session(self, old_session_id: str, new_session_id: str) -> None:
        await asyncio.to_thread(self._reassign_session_sync, old_session_id, new_session_id)

    def _reassign_session_sync(self, old_session_id: str, new_session_id: str) -> None:
        if old_session_id == new_session_id:
            return
        if not self._mongo_available or self.collection is None:
            with self._lock:
                for artifact in self._memory_artifacts.values():
                    if artifact["session_id"] == old_session_id:
                        artifact["session_id"] = new_session_id
                        artifact["updated_at"] = _utc_now()
            return
        try:
            self.collection.update_many(
                {"session_id": old_session_id},
                {"$set": {"session_id": new_session_id, "updated_at": _utc_now()}},
            )
        except PyMongoError:
            self._mongo_available = False

    def storage_mode(self) -> str:
        return "mongodb" if self._mongo_available and self.collection is not None else "memory"

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __del__(self) -> None:
        self.close()

    def _serialize(self, document: dict | None) -> dict | None:
        if document is None:
            return None
        metadata = dict(document.get("metadata", {}))
        return {
            "id": str(document["_id"]),
            "session_id": document.get("session_id", ""),
            "kind": document.get("kind", "file"),
            "title": document.get("title", "Artifact"),
            "content": document.get("content", ""),
            "metadata": metadata,
            "created_at": document.get("created_at", _utc_now()).isoformat(),
            "updated_at": document.get("updated_at", _utc_now()).isoformat(),
        }


@lru_cache
def get_artifact_service() -> ArtifactService:
    return ArtifactService(
        mongo_uri=settings.mongo_uri,
        db_name=settings.mongo_db_name,
    )
