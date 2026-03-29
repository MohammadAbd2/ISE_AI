import asyncio
from datetime import datetime, UTC
from functools import lru_cache
import threading
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.core.config import settings
from backend.app.schemas.chat import ChatMessage


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _session_title(message: str) -> str:
    compact = " ".join(message.split())
    return compact[:48] + ("..." if len(compact) > 48 else "") or "New chat"


class HistoryService:
    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self._memory_sessions: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._mongo_available = True
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            self.collection = client[db_name]["chat_sessions"]
        except PyMongoError:
            # Fall back to in-memory storage when MongoDB is unavailable.
            self.collection = None
            self._mongo_available = False

    async def list_sessions(self) -> list[dict]:
        return await asyncio.to_thread(self._list_sessions_sync)

    def _list_sessions_sync(self) -> list[dict]:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                sessions = sorted(
                    self._memory_sessions.values(),
                    key=lambda item: item["updated_at"],
                    reverse=True,
                )
                return [self._summary(document) for document in sessions]
        try:
            sessions = self.collection.find().sort("updated_at", -1)
            return [self._summary(document) for document in sessions]
        except PyMongoError:
            self._mongo_available = False
            # Retry against memory mode after the first database failure.
            return self._list_sessions_sync()

    async def get_session(self, session_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_session_sync, session_id)

    def _get_session_sync(self, session_id: str) -> dict | None:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                document = self._memory_sessions.get(session_id)
                return self._detail(document) if document else None
        object_id = self._object_id(session_id)
        if object_id is None:
            return None
        try:
            document = self.collection.find_one({"_id": object_id})
            return self._detail(document) if document else None
        except PyMongoError:
            self._mongo_available = False
            return self._get_session_sync(session_id)

    async def create_session(self, message: str, model: str) -> dict:
        return await asyncio.to_thread(self._create_session_sync, message, model)

    def _create_session_sync(self, message: str, model: str) -> dict:
        now = _utc_now()
        document_id = ObjectId() if self._mongo_available and self.collection is not None else str(uuid4())
        document = {
            "_id": document_id,
            "title": _session_title(message),
            "model": model,
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        if not self._mongo_available or self.collection is None:
            with self._lock:
                self._memory_sessions[str(document_id)] = document
            return self._detail(document)
        try:
            result = self.collection.insert_one({k: v for k, v in document.items() if k != "_id"})
            document["_id"] = result.inserted_id
        except PyMongoError:
            self._mongo_available = False
            # Preserve the session even if persistence fails after startup.
            memory_id = str(uuid4())
            document["_id"] = memory_id
            with self._lock:
                self._memory_sessions[memory_id] = document
        return self._detail(document)

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model: str,
    ) -> None:
        await asyncio.to_thread(
            self._append_message_sync,
            session_id,
            role,
            content,
            model,
        )

    def _append_message_sync(
        self,
        session_id: str,
        role: str,
        content: str,
        model: str,
    ) -> None:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                document = self._memory_sessions.get(session_id)
                if document is None:
                    return
                document["messages"].append({"role": role, "content": content})
                document["updated_at"] = _utc_now()
                document["model"] = model
            return
        object_id = self._object_id(session_id)
        if object_id is None:
            return
        now = _utc_now()
        try:
            self.collection.update_one(
                {"_id": object_id},
                {
                    "$push": {"messages": {"role": role, "content": content}},
                    "$set": {"updated_at": now, "model": model},
                },
            )
        except PyMongoError:
            self._mongo_available = False

    async def delete_session(self, session_id: str) -> None:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                self._memory_sessions.pop(session_id, None)
            return
        object_id = self._object_id(session_id)
        if object_id is None:
            return
        try:
            await asyncio.to_thread(
                self.collection.delete_one,
                {"_id": object_id},
            )
        except PyMongoError:
            self._mongo_available = False

    async def clear_sessions(self) -> None:
        if not self._mongo_available or self.collection is None:
            with self._lock:
                self._memory_sessions.clear()
            return
        try:
            await asyncio.to_thread(self.collection.delete_many, {})
        except PyMongoError:
            self._mongo_available = False

    def storage_mode(self) -> str:
        return "mongodb" if self._mongo_available and self.collection is not None else "memory"

    def _summary(self, document: dict) -> dict:
        # Summaries power the chat history sidebar.
        messages = document.get("messages", [])
        preview = messages[-1]["content"] if messages else ""
        return {
            "id": str(document["_id"]),
            "title": document.get("title", "New chat"),
            "model": document.get("model", settings.default_model),
            "updated_at": document.get("updated_at", _utc_now()).isoformat(),
            "preview": preview[:72],
        }

    def _detail(self, document: dict) -> dict:
        return {
            "id": str(document["_id"]),
            "title": document.get("title", "New chat"),
            "model": document.get("model", settings.default_model),
            "updated_at": document.get("updated_at", _utc_now()).isoformat(),
            "messages": [
                ChatMessage(role=item["role"], content=item["content"])
                for item in document.get("messages", [])
            ],
        }

    def _object_id(self, session_id: str) -> ObjectId | None:
        try:
            return ObjectId(session_id)
        except InvalidId:
            return None


@lru_cache
def get_history_service() -> HistoryService:
    """Reuse one storage service instance across requests."""
    return HistoryService(
        mongo_uri=settings.mongo_uri,
        db_name=settings.mongo_db_name,
    )
